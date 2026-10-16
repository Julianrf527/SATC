"""Cálculo de las alertas de vencimiento de los expedientes sancionatorios.

Las reglas (qué genera una alerta, plazos, semáforo) son las mismas de
siempre; lo que cambia es cómo se cargan los datos: ``calcular_alertas_expedientes``
trae etapas, notificaciones y anexos de TODOS los expedientes pedidos con
pocas consultas ``IN (...)`` (10 en total, sin importar cuántos expedientes),
resuelve los nombres de involucrados en UNA llamada bulk a app-involved y
calcula en memoria. Antes eran >13 consultas y una llamada HTTP por expediente.
"""
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from typing import Dict, Iterable
from dateutil.relativedelta import relativedelta
from enum import Enum
from dotenv import load_dotenv
import logging

from db.models.notificacion import Notificacion
from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.documento_anexo import DocumentoAnexo
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso
from services.etapas import ETAPA_LABELS

load_dotenv()
logger = logging.getLogger(__name__)


class EstadoSemaforo(str, Enum):
    VERDE = "verde"
    AMARILLO = "amarillo"
    ROJO = "rojo"
    VENCIDO = "vencido"


from utils.functions import calcular_dias_laborales
from utils.functions import obtener_fecha_despues_dias_laborales
from services.involucrado import get_involucrados_by_ids


def calcular_estado_semaforo(dias_transcurridos: int, dias_totales: int) -> Dict:
    if dias_transcurridos < 0:
        dias_transcurridos = 0
    porcentaje = (dias_transcurridos / dias_totales * 100) if dias_totales > 0 else 100
    if porcentaje > 100:
        estado, urgencia = EstadoSemaforo.VENCIDO, "critico"
    elif porcentaje >= 66:
        estado, urgencia = EstadoSemaforo.ROJO, "alta"
    elif porcentaje >= 33:
        estado, urgencia = EstadoSemaforo.AMARILLO, "media"
    else:
        estado, urgencia = EstadoSemaforo.VERDE, "baja"
    return {
        "estado": estado.value,
        "color_hex": {"verde": "#10B981", "amarillo": "#F59E0B", "rojo": "#EF4444", "vencido": "#7F1D1D"}[estado.value],
        "porcentaje_avance": round(min(porcentaje, 100), 2),
        "urgencia": urgencia,
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": max(dias_totales - dias_transcurridos, 0),
        "dias_totales": dias_totales,
        "esta_vencido": porcentaje > 100,
    }


async def _get_acto_notifs(db: AsyncSession, acto_id: int | None):
    """Returns (acto_row, notificaciones_list) or (None, [])."""
    if not acto_id:
        return None, []
    acto = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if not acto:
        return None, []
    notifs = (await db.execute(
        select(Notificacion.notificacion_exitosa, Notificacion.fecha_notificacion)
        .where(Notificacion.acto_administrativo_id == acto_id)
    )).all()
    return acto, notifs


# ── Carga en bloque ───────────────────────────────────────────────────────────

# Tamaño de lote de los IN (...): asyncpg admite como máximo 32767 parámetros.
_LOTE = 5000

# Etapas que el cálculo lee (una consulta por modelo para todos los expedientes).
_ETAPAS_LEIDAS = (
    EtapaIndagacion, EtapaMedidaPreventiva, EtapaInicioSancionatorio,
    EtapaFormulacionCargos, EtapaAperturaProbatoria, EtapaCierreProbatoria,
    EtapaDecisionFondo, EtapaProbatoriaRecurso,
)

# Alerta 7 (50 días desde la constancia de citación). Subconjunto deliberado:
# excluye EtapaCesacion y EtapaEjecucionSancion, etapas terminales donde esta
# alerta no aplica. El orden importa: si dos etapas comparten acto, gana la
# etiqueta de la última (como antes).
_STAGE_MODELS_CON_ACTO = [
    (Model, ETAPA_LABELS[Model])
    for Model in (
        EtapaIndagacion, EtapaMedidaPreventiva, EtapaInicioSancionatorio,
        EtapaFormulacionCargos, EtapaAperturaProbatoria, EtapaCierreProbatoria,
        EtapaDecisionFondo, EtapaProbatoriaRecurso,
    )
]

# Anexos cuya existencia apaga una alerta: (etapa_tipo, nombre).
_ANEXO_INFORME = ("etapa_apertura_probatoria", "Informe Tecnico")
_ANEXO_ALEGATO = ("etapa_cierre_probatoria", "Alegato de conclusion")
_ANEXO_RECURSO = ("etapa_decision_fondo", "Recurso")
_ANEXOS = (_ANEXO_INFORME, _ANEXO_ALEGATO, _ANEXO_RECURSO)


def _lotes(ids: list) -> Iterable[list]:
    for i in range(0, len(ids), _LOTE):
        yield ids[i:i + _LOTE]


def _a_fecha(valor):
    return valor.date() if hasattr(valor, 'date') else valor


def _fecha_primera_exitosa(notifs: list):
    """Fecha mínima de las notificaciones exitosas que tienen fecha; None si
    no hay exitosas o ninguna tiene fecha (en ambos casos no hay alerta)."""
    exitosas = [n for n in notifs if n.notificacion_exitosa]
    if not exitosas:
        return None
    fecha_noti = min((n.fecha_notificacion for n in exitosas if n.fecha_notificacion), default=None)
    return _a_fecha(fecha_noti) if fecha_noti else None


class _DatosAlertas:
    """Todo lo que el cálculo necesita, cargado en bloque."""

    def __init__(self):
        self.etapas: dict[type, dict[int, object]] = {M: {} for M in _ETAPAS_LEIDAS}
        self.notifs_por_acto: dict[int, list] = defaultdict(list)
        self.anexos: set[tuple[str, int, str]] = set()
        self.involucrados: dict[int, str] = {}

    def etapa(self, Model, expediente_id):
        return self.etapas[Model].get(expediente_id)

    def notifs(self, acto_id):
        return self.notifs_por_acto.get(acto_id, []) if acto_id else []

    def hay_anexo(self, anexo: tuple[str, str], etapa_ref_id: int) -> bool:
        return (anexo[0], etapa_ref_id, anexo[1]) in self.anexos

    def constancias_pendientes(self, expediente_id: int):
        """(notificaciones con constancia de citación y sin éxito —False o
        NULL— de los actos de las etapas, ordenadas por id; acto → etiqueta)."""
        acto_ids_etapa: list[tuple[int, str]] = []
        for Model, etapa_nombre in _STAGE_MODELS_CON_ACTO:
            fila = self.etapa(Model, expediente_id)
            if fila and fila.acto_administrativo_id:
                acto_ids_etapa.append((fila.acto_administrativo_id, etapa_nombre))
        acto_label = {a[0]: a[1] for a in acto_ids_etapa}
        notifs = sorted(
            (
                n for acto_id in acto_label for n in self.notifs(acto_id)
                if n.fecha_constancia_citacion is not None and not n.notificacion_exitosa
            ),
            key=lambda n: n.id,
        )
        return notifs, acto_label


async def _cargar_datos(db: AsyncSession, ids: list[int]) -> _DatosAlertas:
    datos = _DatosAlertas()

    # 1-8. Etapas (expediente_id es único en cada tabla de etapa).
    for Model in _ETAPAS_LEIDAS:
        tabla = Model.__table__
        for lote in _lotes(ids):
            for fila in (await db.execute(select(tabla).where(tabla.c.expediente_id.in_(lote)))).all():
                datos.etapas[Model][fila.expediente_id] = fila

    # 9. Notificaciones de todos los actos de esas etapas.
    actos: set[int] = set()
    for filas in datos.etapas.values():
        for fila in filas.values():
            for col in ("acto_administrativo_id", "acto_recurso_id", "acto_decision_id"):
                acto_id = getattr(fila, col, None)
                if acto_id:
                    actos.add(acto_id)
    for lote in _lotes(sorted(actos)):
        for n in (await db.execute(
            select(
                Notificacion.id,
                Notificacion.acto_administrativo_id,
                Notificacion.notificacion_exitosa,
                Notificacion.fecha_notificacion,
                Notificacion.fecha_constancia_citacion,
                Notificacion.involucrado_id,
            ).where(Notificacion.acto_administrativo_id.in_(lote)).order_by(Notificacion.id)
        )).all():
            datos.notifs_por_acto[n.acto_administrativo_id].append(n)

    # 10. Anexos que apagan alertas (informe técnico, alegato, recurso).
    refs = sorted(
        {f.id for f in datos.etapas[EtapaAperturaProbatoria].values()}
        | {f.id for f in datos.etapas[EtapaCierreProbatoria].values()}
        | {f.id for f in datos.etapas[EtapaDecisionFondo].values()}
    )
    for lote in _lotes(refs):
        datos.anexos.update(
            (fila.etapa_tipo, fila.etapa_ref_id, fila.nombre)
            for fila in (await db.execute(
                select(DocumentoAnexo.etapa_tipo, DocumentoAnexo.etapa_ref_id, DocumentoAnexo.nombre)
                .where(
                    DocumentoAnexo.etapa_ref_id.in_(lote),
                    DocumentoAnexo.etapa_tipo.in_([a[0] for a in _ANEXOS]),
                    DocumentoAnexo.nombre.in_([a[1] for a in _ANEXOS]),
                ).distinct()
            )).all()
        )

    # Nombres de los involucrados de todas las constancias: UNA llamada bulk.
    inv_ids = sorted({
        n.involucrado_id
        for exp_id in ids
        for n in datos.constancias_pendientes(exp_id)[0]
        if n.involucrado_id
    })
    for lote in _lotes(inv_ids):
        try:
            for inv in await get_involucrados_by_ids(None, lote):
                iid = inv.get("id")
                nombre = f"{inv.get('nombre', '')} {inv.get('apellido', '')}".strip()
                if iid:
                    datos.involucrados[iid] = nombre or f"ID {iid}"
        except Exception:
            pass  # nombres opcionales — no rompe la alerta

    return datos


# ── Reglas (en memoria) ───────────────────────────────────────────────────────

def _calcular(expediente_id: int, datos: _DatosAlertas, fecha_hoy: date) -> Dict:
    alertas = {}

    # ── ALERTA 1: 6 meses para iniciar sancionatorio desde indagación ──────────
    indagacion = datos.etapa(EtapaIndagacion, expediente_id)
    if indagacion and not datos.etapa(EtapaInicioSancionatorio, expediente_id):
        fecha_ind = _a_fecha(indagacion.fecha_creacion)
        dias_t = (fecha_hoy - fecha_ind).days
        fecha_lim = fecha_ind + relativedelta(months=6)
        alertas["alerta1"] = {
            "tipo": "inicio_sancionatorio",
            "etapa": "INDAGACION PRELIMINAR",
            "accion_requerida": "Iniciar proceso sancionatorio",
            "plazo_legal": "6 meses",
            "msg": f"Debe iniciar proceso sancionatorio. Han transcurrido {dias_t} días desde la indagación.",
            "fecha_inicio": fecha_ind.isoformat(),
            "fecha_limite": fecha_lim.isoformat(),
            "semaforo": calcular_estado_semaforo(dias_t, (fecha_lim - fecha_ind).days),
        }

    # ── ALERTA 2 & 3: Formulación de cargos ─────────────────────────────────────
    formulacion = datos.etapa(EtapaFormulacionCargos, expediente_id)
    decision = datos.etapa(EtapaDecisionFondo, expediente_id)
    if formulacion:
        fecha_noti = _fecha_primera_exitosa(datos.notifs(formulacion.acto_administrativo_id))
        if fecha_noti:
            # Alerta 2: 80 días para decisión de fondo
            if not decision or not decision.acto_administrativo_id:
                dias_t = calcular_dias_laborales(fecha_noti, fecha_hoy)
                alertas["alerta2"] = {
                    "tipo": "decision_fondo",
                    "etapa": "FORMULACION DE CARGOS",
                    "accion_requerida": "Crear etapa decisión de fondo con acto administrativo",
                    "plazo_legal": "80 días laborales",
                    "msg": f"Debe emitir decisión de fondo. Han transcurrido {dias_t} días laborales.",
                    "fecha_notificacion": fecha_noti.isoformat(),
                    "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 80).isoformat(),
                    "semaforo": calcular_estado_semaforo(dias_t, 80),
                }

            # Alerta 3: 10 días para descargos (si hay documento en formulación)
            if formulacion.documento_id:
                dias_t = calcular_dias_laborales(fecha_noti, fecha_hoy)
                alertas["alerta3"] = {
                    "tipo": "presentacion_descargos",
                    "etapa": "FORMULACION DE CARGOS",
                    "accion_requerida": "Presentar descargos",
                    "plazo_legal": "10 días laborales",
                    "msg": f"Debe presentar descargos. Han transcurrido {dias_t} días laborales.",
                    "fecha_notificacion": fecha_noti.isoformat(),
                    "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                    "semaforo": calcular_estado_semaforo(dias_t, 10),
                }

    # ── ALERTA 4: 30 días para informe técnico en apertura probatoria ────────────
    apertura = datos.etapa(EtapaAperturaProbatoria, expediente_id)
    if apertura and not datos.hay_anexo(_ANEXO_INFORME, apertura.id):
        fecha_noti = _fecha_primera_exitosa(datos.notifs(apertura.acto_administrativo_id))
        if fecha_noti:
            dias_t = calcular_dias_laborales(fecha_noti, fecha_hoy)
            alertas["alerta4"] = {
                "tipo": "informe_tecnico",
                "etapa": "APERTURA ETAPA PROBATORIA",
                "accion_requerida": "Presentar informe técnico",
                "plazo_legal": "30 días laborales",
                "msg": f"Debe presentar informe técnico. Han transcurrido {dias_t} días laborales.",
                "fecha_notificacion": fecha_noti.isoformat(),
                "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 30).isoformat(),
                "semaforo": calcular_estado_semaforo(dias_t, 30),
            }

    # ── ALERTA 5: 10 días para alegatos en cierre probatoria ─────────────────────
    cierre = datos.etapa(EtapaCierreProbatoria, expediente_id)
    if cierre and not datos.hay_anexo(_ANEXO_ALEGATO, cierre.id):
        fecha_noti = _fecha_primera_exitosa(datos.notifs(cierre.acto_administrativo_id))
        if fecha_noti:
            dias_t = calcular_dias_laborales(fecha_noti, fecha_hoy)
            alertas["alerta5"] = {
                "tipo": "alegato_conclusion",
                "etapa": "CIERRE ETAPA PROBATORIA",
                "accion_requerida": "Presentar alegato de conclusión",
                "plazo_legal": "10 días laborales",
                "msg": f"Debe presentar alegato de conclusión. Han transcurrido {dias_t} días laborales.",
                "fecha_notificacion": fecha_noti.isoformat(),
                "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                "semaforo": calcular_estado_semaforo(dias_t, 10),
            }

    # ── ALERTA 6: recurso / resolución recurso ────────────────────────────────────
    if decision and decision.acto_administrativo_id:
        fecha_noti = _fecha_primera_exitosa(datos.notifs(decision.acto_administrativo_id))
        if fecha_noti:
            if not datos.hay_anexo(_ANEXO_RECURSO, decision.id):
                dias_t = calcular_dias_laborales(fecha_noti, fecha_hoy)
                alertas["alerta6"] = {
                    "tipo": "presentacion_recurso",
                    "etapa": "DECISION DE FONDO",
                    "accion_requerida": "Presentar recurso",
                    "plazo_legal": "10 días laborales",
                    "msg": f"Puede presentar recurso. Han transcurrido {dias_t} días laborales.",
                    "fecha_notificacion": fecha_noti.isoformat(),
                    "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                    "semaforo": calcular_estado_semaforo(dias_t, 10),
                }
            else:
                recurso = datos.etapa(EtapaProbatoriaRecurso, expediente_id)
                if recurso:
                    # La decisión del recurso es el acto auxiliar de la
                    # probatoria (acto_decision_id), no su acto principal.
                    # Sin ese acto, o sin notificación exitosa, sigue pendiente.
                    noti_rec = [n.notificacion_exitosa for n in datos.notifs(recurso.acto_decision_id)]
                    if not any(noti_rec):
                        dias_t = (fecha_hoy - fecha_noti).days
                        alertas["alerta6"] = {
                            "tipo": "resolucion_recurso",
                            "etapa": "PROBATORIA DE RECURSO",
                            "accion_requerida": "Notificar decisión del recurso",
                            "plazo_legal": "1 año",
                            "msg": f"Debe notificar decisión del recurso. Han transcurrido {dias_t} días.",
                            "fecha_presentacion": fecha_noti.isoformat(),
                            "fecha_limite": (fecha_noti + relativedelta(years=1)).isoformat(),
                            "semaforo": calcular_estado_semaforo(dias_t, 365),
                        }
                elif decision.acto_recurso_id:
                    noti_rec = [n.notificacion_exitosa for n in datos.notifs(decision.acto_recurso_id)]
                    if not any(noti_rec):
                        dias_t = (fecha_hoy - fecha_noti).days
                        alertas["alerta6"] = {
                            "tipo": "notificacion_recurso",
                            "etapa": "DECISION DE FONDO",
                            "accion_requerida": "Notificar acto administrativo de recurso",
                            "plazo_legal": "1 año",
                            "msg": f"Debe notificar el acto de recurso. Han transcurrido {dias_t} días.",
                            "fecha_presentacion": fecha_noti.isoformat(),
                            "fecha_limite": (fecha_noti + relativedelta(years=1)).isoformat(),
                            "semaforo": calcular_estado_semaforo(dias_t, 365),
                        }

    # ── ALERTA 7: 50 días calendario desde fecha_constancia_citacion ─────────────
    # Para CUALQUIER notificación con constancia de citación que aún no sea
    # exitosa, en las etapas de _STAGE_MODELS_CON_ACTO.
    notifs_constancia, acto_label = datos.constancias_pendientes(expediente_id)
    for i, noti in enumerate(notifs_constancia, start=1):
        fc = _a_fecha(noti.fecha_constancia_citacion)
        dias_t = (fecha_hoy - fc).days
        fecha_lim = fc + timedelta(days=50)
        etapa_label = acto_label.get(noti.acto_administrativo_id, "ETAPA")
        inv_nombre = datos.involucrados.get(noti.involucrado_id, "") if noti.involucrado_id else ""
        alertas[f"alerta_constancia_{i}"] = {
            "tipo": "constancia_citacion_pendiente",
            "etapa": etapa_label,
            "involucrado_nombre": inv_nombre,
            "accion_requerida": "Completar notificación como exitosa",
            "plazo_legal": "50 días calendario",
            "msg": f"Hay {max(50 - dias_t, 0)} días restantes para completar la notificación desde la constancia de citación ({fc.isoformat()}).",
            "fecha_constancia": fc.isoformat(),
            "fecha_limite": fecha_lim.isoformat(),
            "semaforo": calcular_estado_semaforo(dias_t, 50),
        }

    return alertas


# ── API ───────────────────────────────────────────────────────────────────────

async def calcular_alertas_expedientes(
    expediente_ids: Iterable[int], db: AsyncSession, fecha_hoy: date
) -> dict[int, Dict]:
    """Alertas de varios expedientes: ``{expediente_id: {clave: alerta}}``.

    10 consultas + 1 llamada a app-involved en total, sin importar cuántos
    expedientes (en lotes de 5000 ids si fueran más).
    """
    ids = list(dict.fromkeys(expediente_ids))
    if not ids:
        return {}
    datos = await _cargar_datos(db, ids)
    return {exp_id: _calcular(exp_id, datos, fecha_hoy) for exp_id in ids}


async def calcular_alertas_expediente(radicado: str, db: AsyncSession, fecha_hoy: date) -> Dict:
    """Alertas de un expediente por radicado (``{}`` si no existe)."""
    expediente_id = await db.scalar(select(Expediente.id).where(Expediente.radicado == radicado))
    if not expediente_id:
        return {}
    return (await calcular_alertas_expedientes([expediente_id], db, fecha_hoy)).get(expediente_id, {})
