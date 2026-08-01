from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import date, timedelta
from typing import Dict
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


async def calcular_alertas_expediente(radicado: str, db: AsyncSession, fecha_hoy: date) -> Dict:
    alertas = {}

    expediente_id = await db.scalar(select(Expediente.id).where(Expediente.radicado == radicado))
    if not expediente_id:
        return alertas

    # ── ALERTA 1: 6 meses para iniciar sancionatorio desde indagación ──────────
    indagacion = await db.scalar(
        select(EtapaIndagacion).where(EtapaIndagacion.expediente_id == expediente_id)
    )
    if indagacion:
        inicio_sanc = await db.scalar(
            select(EtapaInicioSancionatorio.id).where(EtapaInicioSancionatorio.expediente_id == expediente_id)
        )
        if not inicio_sanc:
            fecha_ind = indagacion.fecha_creacion.date() if hasattr(indagacion.fecha_creacion, 'date') else indagacion.fecha_creacion
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
    formulacion = await db.scalar(
        select(EtapaFormulacionCargos).where(EtapaFormulacionCargos.expediente_id == expediente_id)
    )
    if formulacion:
        acto_form, notifs_form = await _get_acto_notifs(db, formulacion.acto_administrativo_id)
        if acto_form:
            exitosas = [n for n in notifs_form if n.notificacion_exitosa]
            if exitosas:
                fecha_noti = min((n.fecha_notificacion for n in exitosas if n.fecha_notificacion), default=None)
                if fecha_noti:
                    fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti

                    # Alerta 2: 80 días para decisión de fondo
                    decision = await db.scalar(
                        select(EtapaDecisionFondo).where(EtapaDecisionFondo.expediente_id == expediente_id)
                    )
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
    apertura = await db.scalar(
        select(EtapaAperturaProbatoria).where(EtapaAperturaProbatoria.expediente_id == expediente_id)
    )
    if apertura:
        _, notifs_ap = await _get_acto_notifs(db, apertura.acto_administrativo_id)
        exitosas = [n for n in notifs_ap if n.notificacion_exitosa]
        if exitosas:
            existe_informe = await db.scalar(
                select(DocumentoAnexo.id).where(
                    DocumentoAnexo.etapa_tipo == "etapa_apertura_probatoria",
                    DocumentoAnexo.etapa_ref_id == apertura.id,
                    DocumentoAnexo.nombre == "Informe Tecnico",
                ).limit(1)
            )
            if not existe_informe:
                fecha_noti = min((n.fecha_notificacion for n in exitosas if n.fecha_notificacion), default=None)
                if fecha_noti:
                    fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
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
    cierre = await db.scalar(
        select(EtapaCierreProbatoria).where(EtapaCierreProbatoria.expediente_id == expediente_id)
    )
    if cierre:
        _, notifs_ci = await _get_acto_notifs(db, cierre.acto_administrativo_id)
        exitosas = [n for n in notifs_ci if n.notificacion_exitosa]
        if exitosas:
            existe_alegato = await db.scalar(
                select(DocumentoAnexo.id).where(
                    DocumentoAnexo.etapa_tipo == "etapa_cierre_probatoria",
                    DocumentoAnexo.etapa_ref_id == cierre.id,
                    DocumentoAnexo.nombre == "Alegato de conclusion",
                ).limit(1)
            )
            if not existe_alegato:
                fecha_noti = min((n.fecha_notificacion for n in exitosas if n.fecha_notificacion), default=None)
                if fecha_noti:
                    fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
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
    decision = await db.scalar(
        select(EtapaDecisionFondo).where(EtapaDecisionFondo.expediente_id == expediente_id)
    )
    if decision and decision.acto_administrativo_id:
        _, notifs_dec = await _get_acto_notifs(db, decision.acto_administrativo_id)
        exitosas = [n for n in notifs_dec if n.notificacion_exitosa]
        if exitosas:
            fecha_noti = min((n.fecha_notificacion for n in exitosas if n.fecha_notificacion), default=None)
            if fecha_noti:
                fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti

                existe_recurso = await db.scalar(
                    select(DocumentoAnexo.id).where(
                        DocumentoAnexo.etapa_tipo == "etapa_decision_fondo",
                        DocumentoAnexo.etapa_ref_id == decision.id,
                        DocumentoAnexo.nombre == "Recurso",
                    ).limit(1)
                )

                if not existe_recurso:
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
                    recurso = await db.scalar(
                        select(EtapaProbatoriaRecurso).where(EtapaProbatoriaRecurso.expediente_id == expediente_id)
                    )
                    if recurso and recurso.acto_administrativo_id:
                        noti_rec = (await db.execute(
                            select(Notificacion.notificacion_exitosa)
                            .where(Notificacion.acto_administrativo_id == recurso.acto_administrativo_id)
                        )).scalars().all()
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
                        noti_rec = (await db.execute(
                            select(Notificacion.notificacion_exitosa)
                            .where(Notificacion.acto_administrativo_id == decision.acto_recurso_id)
                        )).scalars().all()
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
    # Para CUALQUIER notificación con constancia de citación que aún no sea exitosa,
    # aplica en todas las etapas del expediente.
    # Subconjunto deliberado: excluye EtapaCesacion y EtapaEjecucionSancion,
    # etapas terminales donde esta alerta de 50 días no aplica.
    STAGE_MODELS_CON_ACTO = [
        (Model, ETAPA_LABELS[Model])
        for Model in (
            EtapaIndagacion, EtapaMedidaPreventiva, EtapaInicioSancionatorio,
            EtapaFormulacionCargos, EtapaAperturaProbatoria, EtapaCierreProbatoria,
            EtapaDecisionFondo, EtapaProbatoriaRecurso,
        )
    ]
    acto_ids_etapa: list[tuple[int, str]] = []
    for Model, etapa_nombre in STAGE_MODELS_CON_ACTO:
        acto_id = await db.scalar(
            select(Model.acto_administrativo_id).where(Model.expediente_id == expediente_id)
        )
        if acto_id:
            acto_ids_etapa.append((acto_id, etapa_nombre))

    if acto_ids_etapa:
        ids_only = [a[0] for a in acto_ids_etapa]
        acto_label = {a[0]: a[1] for a in acto_ids_etapa}
        notifs_constancia = (await db.execute(
            select(Notificacion).where(
                Notificacion.acto_administrativo_id.in_(ids_only),
                Notificacion.fecha_constancia_citacion.is_not(None),
                or_(
                    Notificacion.notificacion_exitosa == False,
                    Notificacion.notificacion_exitosa.is_(None),
                ),
            )
        )).scalars().all()

        inv_ids = [n.involucrado_id for n in notifs_constancia if n.involucrado_id]
        involucrados_map: dict[int, str] = {}
        if inv_ids:
            try:
                inv_data = await get_involucrados_by_ids(None, list(set(inv_ids)))
                for inv in inv_data:
                    iid = inv.get("id")
                    nombre = f"{inv.get('nombre', '')} {inv.get('apellido', '')}".strip()
                    if iid:
                        involucrados_map[iid] = nombre or f"ID {iid}"
            except Exception:
                pass  # nombres opcionales — no rompe la alerta

        for i, noti in enumerate(notifs_constancia, start=1):
            fc = noti.fecha_constancia_citacion
            fc = fc.date() if hasattr(fc, 'date') else fc
            dias_t = (fecha_hoy - fc).days
            fecha_lim = fc + timedelta(days=50)
            etapa_label = acto_label.get(noti.acto_administrativo_id, "ETAPA")
            inv_nombre = involucrados_map.get(noti.involucrado_id, "") if noti.involucrado_id else ""
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
