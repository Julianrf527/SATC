"""Cálculo de las alertas de vencimiento de los expedientes de infracción.

``calcular_alertas_expedientes`` trae los datos de TODOS los expedientes
pedidos con un número fijo de consultas ``IN (...)`` (sin importar cuántos
expedientes) y calcula en memoria con ``_calcular``.

Todos los plazos son en días HÁBILES (Colombia), el día de inicio no cuenta,
y el semáforo también cuenta días hábiles. "Hoy" es el día en Bogotá. Los
expedientes archivados no tienen alertas.

Alertas (clave → plazo, inicio → fin):

- ``respuesta_plazo``: 15, creación del expediente → se registra la respuesta.
- Visita técnica / seguimiento (``visita_*`` / ``seguimiento_*``):
  ``_asignar`` 30 (registro de la respuesta / vencimiento del término del
  auto de requerimiento → técnico Y fecha de programación),
  ``_primera_version`` 30 (``informe_tecnico.fecha_asignacion`` → primera
  versión en el proceso de revisión), ``_aprobacion`` 20 (primera versión →
  versión firmada, que acepta el informe).
- Acoger concepto / concepto · seguimiento (prefijo ``concepto`` /
  ``concepto_seguimiento``): ``_solicitud`` 10 (radicado de la solicitud de
  información → su respuesta); ``_acto_proyectar`` 17 (versión firmada del
  informe habilitante, o la respuesta a la solicitud → primera versión del
  auto de requerimiento) y ``_acto_aprobacion`` 25 (primera versión → acto
  creado con la versión firmada o por cargue directo). Sin tipo de acogida
  aún sale ``_acto_proyectar`` como recordatorio; con OFICIO o
  RESOLUCION_ARCHIVO el concepto no tiene acto (el de RESOLUCION_ARCHIVO es
  el de cierre). Además ``_constancia_{notif}`` y ``_termino`` (sin cambios).
- ``medida_acto_proyectar`` / ``_aprobacion``: igual sobre el acto de la
  medida preventiva cuando la respuesta la requiere (inicio: registro de la
  respuesta).
- ``cierre_acto_proyectar`` / ``_aprobacion``: igual sobre el acto de cierre;
  inicia cuando el cierre queda habilitado (RESOLUCION_ARCHIVO: como el acto
  del concepto; OFICIO: remisión del oficio; auto de requerimiento de
  seguimiento: primera notificación exitosa de su acto).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

import holidays
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.documento_proceso import (
    ETAPA_CIERRE,
    ETAPA_CONCEPTO,
    ETAPA_INFORME,
    ETAPA_MEDIDA,
    DocumentoProceso,
    DocumentoProcesoVersion,
)
from db.models.etapa_acoger_concepto import INSTANCIA_SEGUIMIENTO, EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.expediente import Expediente
from db.models.informe_tecnico import InformeTecnico
from db.models.medida_preventiva import MedidaPreventiva
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion

BOGOTA = ZoneInfo("America/Bogota")

# Tamaño de lote de los IN (...): asyncpg admite como máximo 32767 parámetros.
_LOTE = 5000

AUTO_REQUERIMIENTO = "AUTO_REQUERIMIENTO"
OFICIO = "OFICIO"
RESOLUCION_ARCHIVO = "RESOLUCION_ARCHIVO"

PLAZO_RESPUESTA = 15
PLAZO_ASIGNAR_VISITA = 30
PLAZO_PRIMERA_VERSION_INFORME = 30
PLAZO_APROBACION_INFORME = 20
PLAZO_SOLICITUD = 10
PLAZO_PROYECTAR_ACTO = 17
PLAZO_APROBACION_ACTO = 25
# Aviso (no bloquea) de la fecha de programación de la visita.
PLAZO_PROGRAMACION_VISITA = 30


# ───────────────────────────────────────────────────────────── días hábiles

@lru_cache(maxsize=None)
def _festivos_anio(anio: int) -> frozenset:
    """Festivos de Colombia de un año, calculados una sola vez por proceso."""
    return frozenset(holidays.Colombia(years=anio).keys())


def _es_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in _festivos_anio(d.year)


def fecha_limite_habiles(fecha_inicio: date, dias_habiles: int) -> date:
    """Día en que se cumplen ``dias_habiles`` contados desde el día siguiente."""
    count = 0
    current = fecha_inicio
    while count < dias_habiles:
        current += timedelta(days=1)
        if _es_habil(current):
            count += 1
    return current


def _restar_habiles(fecha_fin: date, dias_habiles: int) -> date:
    """Inverso de ``fecha_limite_habiles``: inicio tal que sumarle
    ``dias_habiles`` da ``fecha_fin`` (o el día hábil anterior más cercano)."""
    current, count = fecha_fin, 0
    while count < dias_habiles:
        if _es_habil(current):
            count += 1
        current -= timedelta(days=1)
    return current


def _habiles_entre(desde: date, hasta: date) -> int:
    """Días hábiles en (desde, hasta]; 0 si ``hasta <= desde``."""
    if hasta <= desde:
        return 0
    return sum(1 for i in range(1, (hasta - desde).days + 1) if _es_habil(desde + timedelta(days=i)))


def hoy_bogota() -> date:
    return datetime.now(BOGOTA).date()


def _fecha_local(valor) -> Optional[date]:
    """TIMESTAMPTZ → día en Bogotá; ``date`` tal cual; None → None."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return (valor.astimezone(BOGOTA) if valor.tzinfo else valor).date()
    return valor


def _fecha_texto(valor: Optional[str]) -> Optional[date]:
    """Columnas VARCHAR(10) "aaaa-mm-dd" (solicitud, oficio)."""
    if not valor:
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None


# ─────────────────────────────────────── aviso de la fecha de programación

def limite_programacion(desde: date) -> date:
    return fecha_limite_habiles(desde, PLAZO_PROGRAMACION_VISITA)


def advertencia_programacion(fecha_programacion: Optional[date], desde: date) -> Optional[str]:
    """Aviso (no bloquea) si la visita queda a más de 30 días hábiles de
    ``desde`` (el día de la asignación). None si está bien o no hay fecha."""
    if fecha_programacion is None:
        return None
    limite = limite_programacion(desde)
    if fecha_programacion <= limite:
        return None
    return (f"Fecha fuera del plazo: la visita ({fecha_programacion.strftime('%d/%m/%Y')}) supera los "
            f"{PLAZO_PROGRAMACION_VISITA} días hábiles desde la asignación (límite {limite.strftime('%d/%m/%Y')}). "
            "Se guardó igual.")


# ───────────────────────────────────────────────────────────────── semáforo

def _build_semaforo(fecha_inicio: date, fecha_limite: date, fecha_hoy: date) -> dict:
    """Semáforo en días hábiles: <50 % verde, ≥50 % amarillo, ≥80 % rojo y,
    pasado el último día del plazo, vencido."""
    esta_vencido = fecha_hoy > fecha_limite
    dias_totales = max(_habiles_entre(fecha_inicio, fecha_limite), 1)
    dias_transcurridos = _habiles_entre(fecha_inicio, fecha_hoy)
    porcentaje = min((dias_transcurridos / dias_totales) * 100, 100)

    if esta_vencido:
        estado, urgencia, color = "vencido", "critico", "#1f2937"
    elif porcentaje >= 80:
        estado, urgencia, color = "rojo", "alta", "#ef4444"
    elif porcentaje >= 50:
        estado, urgencia, color = "amarillo", "media", "#f59e0b"
    else:
        estado, urgencia, color = "verde", "baja", "#22c55e"

    return {
        "estado": estado,
        "color_hex": color,
        "porcentaje_avance": round(porcentaje, 1),
        "urgencia": urgencia,
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": _habiles_entre(fecha_hoy, fecha_limite),
        "dias_totales": dias_totales,
        "esta_vencido": esta_vencido,
    }


def _alerta(tipo: str, etapa: str, accion: str, plazo: str,
            fecha_inicio: date, fecha_limite: date, fecha_hoy: date, msg: str = None) -> dict:
    return {
        "tipo": tipo,
        "etapa": etapa,
        "accion_requerida": accion,
        "plazo_legal": plazo,
        "msg": msg or accion,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_limite": fecha_limite.isoformat(),
        "semaforo": _build_semaforo(fecha_inicio, fecha_limite, fecha_hoy),
    }


def _alerta_plazo(alertas: dict, clave: str, etapa: str, accion: str, dias: int, desde: str,
                  inicio: date, hoy: date) -> None:
    alertas[clave] = _alerta(clave, etapa, accion, f"{dias} días hábiles desde {desde}",
                             inicio, fecha_limite_habiles(inicio, dias), hoy)


# ───────────────────────────────────────────────────── datos de un expediente

@dataclass
class _Datos:
    """Lo que necesitan las reglas de UN expediente (ya cargado)."""
    fecha_creacion: date
    tiene_respuesta: bool = False
    respuesta: object = None                 # primera fila de etapa_respuesta
    medida: object = None                    # su medida preventiva
    informes: dict = field(default_factory=dict)   # "VISITA" / "SEGUIMIENTO" -> fila
    concepto: object = None
    concepto_seguimiento: object = None
    notifs_constancia: list = field(default_factory=list)
    notifs_seguimiento: list = field(default_factory=list)
    solicitudes: dict = field(default_factory=dict)  # concepto_id -> fila
    oficios: dict = field(default_factory=dict)      # concepto_id -> fila
    cierre: object = None
    primeras_versiones: dict = field(default_factory=dict)  # (etapa_tipo, ref_id) -> date
    primera_exitosa: dict = field(default_factory=dict)     # acto_id -> date

    def primera_version(self, etapa_tipo: str, fila) -> Optional[date]:
        return self.primeras_versiones.get((etapa_tipo, fila.id)) if fila is not None else None


# ────────────────────────────────────────────────────────────────── reglas

def _alertas_acto(alertas: dict, prefijo: str, etapa: str, documento: str, inicio: Optional[date],
                  desde: str, primera: Optional[date], listo: bool, hoy: date) -> None:
    """Proyectar (17) → aprobar hasta la versión firmada (25) de un acto."""
    if listo:
        return
    if primera is None:
        if inicio is not None:
            _alerta_plazo(alertas, f"{prefijo}_proyectar", etapa,
                          f"Proyectar el {documento}: cargar la primera versión",
                          PLAZO_PROYECTAR_ACTO, desde, inicio, hoy)
        return
    _alerta_plazo(alertas, f"{prefijo}_aprobacion", etapa,
                  f"Aprobar el {documento} y cargar la versión firmada",
                  PLAZO_APROBACION_ACTO, "la primera versión", primera, hoy)


def _alertas_informe(alertas: dict, d: _Datos, prefijo: str, etapa: str, documento: str, informe,
                     inicio_asignar: Optional[date], desde_asignar: str, hoy: date) -> None:
    """Asignar visita (30) → primera versión (30) → versión firmada (20)."""
    if informe is not None and informe.fecha_aceptacion_informe is not None:
        return
    asignado = (informe is not None and informe.profesional_asignado_id
                and informe.fecha_programacion_visita is not None)
    if not asignado:
        if inicio_asignar is not None:
            _alerta_plazo(alertas, f"{prefijo}_asignar", etapa,
                          "Asignar profesional y fecha de programación de la visita",
                          PLAZO_ASIGNAR_VISITA, desde_asignar, inicio_asignar, hoy)
        return
    primera = d.primera_version(ETAPA_INFORME, informe)
    if primera is None:
        inicio = informe.fecha_asignacion or _fecha_local(informe.fecha_creacion)
        _alerta_plazo(alertas, f"{prefijo}_primera_version", etapa,
                      f"Cargar la primera versión del {documento}",
                      PLAZO_PRIMERA_VERSION_INFORME, "la asignación de la visita", inicio, hoy)
        return
    _alerta_plazo(alertas, f"{prefijo}_aprobacion", etapa,
                  f"Aprobar el {documento} y cargar la versión firmada",
                  PLAZO_APROBACION_INFORME, "la primera versión", primera, hoy)


def _alertas_concepto_acto(alertas: dict, d: _Datos, concepto, aceptacion: Optional[date], *,
                           prefijo: str, etapa: str, informe_txt: str, hoy: date):
    """Solicitud de información (10) y auto de requerimiento (17 / 25) de un
    acoger concepto. Devuelve ``(inicio, desde)`` del acto de la instancia
    (lo usa el cierre con RESOLUCION_ARCHIVO); ``(None, "")`` si no corre."""
    if aceptacion is None:
        return None, ""
    solicitud = d.solicitudes.get(concepto.id) if concepto is not None else None
    if solicitud is not None:
        if not solicitud.fecha_radicado_respuesta:
            inicio_sol = _fecha_texto(solicitud.fecha_radicado)
            if inicio_sol is not None:
                _alerta_plazo(alertas, f"{prefijo}_solicitud", etapa,
                              "Registrar la respuesta a la solicitud de información",
                              PLAZO_SOLICITUD, "el radicado de la solicitud", inicio_sol, hoy)
            return None, ""
        inicio, desde = _fecha_texto(solicitud.fecha_radicado_respuesta), "la respuesta a la solicitud de información"
    else:
        inicio, desde = aceptacion, f"la versión firmada del {informe_txt}"

    tipo = concepto.tipo_acogida_concepto if concepto is not None else None
    if tipo is None:
        if inicio is not None:
            _alerta_plazo(alertas, f"{prefijo}_acto_proyectar", etapa,
                          "Elegir el tipo de acogida y proyectar el acto administrativo",
                          PLAZO_PROYECTAR_ACTO, desde, inicio, hoy)
    elif tipo == AUTO_REQUERIMIENTO:
        _alertas_acto(alertas, f"{prefijo}_acto", etapa, "auto de requerimiento", inicio, desde,
                      d.primera_version(ETAPA_CONCEPTO, concepto), bool(concepto.acto_administrativo_id), hoy)
    return inicio, desde


def _alertas_constancia_termino(alertas: dict, concepto, notifs_constancia: list, fecha_hoy: date, *,
                                prefijo: str, etapa: str) -> None:
    """Constancia de citación y días de término de un acoger concepto."""
    if concepto is None:
        return
    # 15 días hábiles desde fecha_constancia_citacion para notificar (el acto
    # de acoger concepto solo se notifica: ya no se cambia a comunicación).
    if concepto.tipo_acogida_concepto == AUTO_REQUERIMIENTO and concepto.acto_administrativo_id:
        for notif in notifs_constancia:
            fecha_const = notif.fecha_constancia_citacion
            fecha_lim = fecha_limite_habiles(fecha_const, 15)
            alertas[f"{prefijo}_constancia_{notif.id}"] = _alerta(
                tipo=f"{prefijo}_constancia",
                etapa=etapa,
                accion="Constancia de citación registrada. Notificar el acto antes de que venza el plazo",
                plazo="15 días hábiles desde fecha de constancia de citación",
                fecha_inicio=fecha_const,
                fecha_limite=fecha_lim,
                fecha_hoy=fecha_hoy,
                msg=f"15 días hábiles desde constancia del {fecha_const.isoformat()} para notificar",
            )

    # Fecha término de los días hábiles definidos.
    if concepto.fecha_termino_calculada and concepto.dias_termino:
        fecha_termino = concepto.fecha_termino_calculada
        dias = concepto.dias_termino
        alertas[f"{prefijo}_termino"] = _alerta(
            tipo=f"{prefijo}_termino",
            etapa=etapa,
            accion=f"El término de {dias} días hábiles del concepto técnico está en curso",
            plazo=f"{dias} días hábiles desde notificación del concepto",
            fecha_inicio=_restar_habiles(fecha_termino, dias),
            fecha_limite=fecha_termino,
            fecha_hoy=fecha_hoy,
            msg=f"Término de {dias} días hábiles vence el {fecha_termino.isoformat()}",
        )


def _inicio_cierre(d: _Datos, visita: tuple, seguimiento: tuple):
    """``(inicio, desde)`` del acto de cierre: cuando el cierre queda
    habilitado. ``(None, "")`` si todavía no."""
    cv, cs = d.concepto, d.concepto_seguimiento
    if cv is None:
        return None, ""
    terminal, inicio_concepto = (cv, visita) if cv.tipo_acogida_concepto != AUTO_REQUERIMIENTO else (cs, seguimiento)
    if terminal is None:
        return None, ""
    tipo = terminal.tipo_acogida_concepto
    if tipo == RESOLUCION_ARCHIVO:
        return inicio_concepto
    if tipo == OFICIO:
        oficio = d.oficios.get(terminal.id)
        if oficio is None or not oficio.archivo_remite_id:
            return None, ""
        return _fecha_texto(oficio.fecha_remitido), "la remisión del oficio"
    if tipo == AUTO_REQUERIMIENTO and terminal.acto_administrativo_id:
        # Solo llega aquí el concepto · seguimiento.
        return (d.primera_exitosa.get(terminal.acto_administrativo_id),
                "la primera notificación exitosa del auto de requerimiento de seguimiento")
    return None, ""


def _calcular(d: _Datos, hoy: date) -> dict:
    """Reglas de un expediente con sus datos ya cargados (sin BD)."""
    alertas = {}
    respuesta = d.respuesta
    inicio_respuesta = (respuesta.fecha_creacion or respuesta.fecha_radicado) if respuesta is not None else None

    # 1. Respuesta: 15 días hábiles desde creación del expediente.
    if not d.tiene_respuesta:
        alertas["respuesta_plazo"] = _alerta(
            tipo="respuesta_plazo",
            etapa="Respuesta",
            accion="Registrar la etapa de respuesta con radicado y fecha de radicado",
            plazo="15 días hábiles desde la creación del expediente",
            fecha_inicio=d.fecha_creacion,
            fecha_limite=fecha_limite_habiles(d.fecha_creacion, PLAZO_RESPUESTA),
            fecha_hoy=hoy,
        )

    # Acto de la medida preventiva (si la respuesta la requiere).
    if respuesta is not None and respuesta.requiere_medida_preventiva:
        _alertas_acto(alertas, "medida_acto", "Respuesta", "acto de la medida preventiva",
                      inicio_respuesta, "el registro de la respuesta",
                      d.primera_version(ETAPA_MEDIDA, d.medida),
                      bool(d.medida is not None and d.medida.acto_administrativo_id), hoy)

    # 2-4. Visita técnica.
    visita = d.informes.get("VISITA")
    if d.tiene_respuesta:
        _alertas_informe(alertas, d, "visita", "Visita técnica", "concepto técnico", visita,
                         inicio_respuesta, "el registro de la respuesta", hoy)

    # 5-7. Acoger concepto (de la visita).
    cv = d.concepto
    inicio_visita = _alertas_concepto_acto(
        alertas, d, cv, visita.fecha_aceptacion_informe if visita is not None else None,
        prefijo="concepto", etapa="Concepto", informe_txt="informe técnico de visita", hoy=hoy)
    _alertas_constancia_termino(alertas, cv, d.notifs_constancia, hoy, prefijo="concepto", etapa="Concepto")

    # 9-11 y concepto · seguimiento: solo tras un auto de requerimiento.
    inicio_seg = (None, "")
    if cv is not None and cv.tipo_acogida_concepto == AUTO_REQUERIMIENTO:
        seguimiento = d.informes.get("SEGUIMIENTO")
        termino = cv.fecha_termino_calculada
        vencido = termino is not None and hoy > termino
        if vencido or seguimiento is not None:
            _alertas_informe(alertas, d, "seguimiento", "Seguimiento", "concepto técnico de seguimiento",
                             seguimiento, termino if vencido else None,
                             "el vencimiento del término del auto de requerimiento", hoy)
        inicio_seg = _alertas_concepto_acto(
            alertas, d, d.concepto_seguimiento,
            seguimiento.fecha_aceptacion_informe if seguimiento is not None else None,
            prefijo="concepto_seguimiento", etapa="Concepto seguimiento",
            informe_txt="informe técnico de seguimiento", hoy=hoy)
    _alertas_constancia_termino(alertas, d.concepto_seguimiento, d.notifs_seguimiento, hoy,
                                prefijo="concepto_seguimiento", etapa="Concepto seguimiento")

    # Acto de cierre.
    inicio, desde = _inicio_cierre(d, inicio_visita, inicio_seg)
    _alertas_acto(alertas, "cierre_acto", "Cierre", "acto de cierre", inicio, desde,
                  d.primera_version(ETAPA_CIERRE, d.cierre),
                  bool(d.cierre is not None and d.cierre.acto_administrativo_id), hoy)
    return alertas


# ─────────────────────────────────────────────────────────── carga en bloque

def _lotes(ids: list) -> Iterable[list]:
    for i in range(0, len(ids), _LOTE):
        yield ids[i:i + _LOTE]


async def _todas(db: AsyncSession, ids: list, consulta) -> list:
    """Ejecuta ``consulta(lote)`` por lotes y junta las filas."""
    filas = []
    for lote in _lotes(ids):
        filas.extend((await db.execute(consulta(lote))).all())
    return filas


async def calcular_alertas_expedientes(
    expediente_ids: Iterable[int], db: AsyncSession, fecha_hoy: date
) -> dict[int, dict]:
    """Alertas de varios expedientes: ``{expediente_id: {clave: alerta}}``.

    Solo incluye los expedientes que existen y no están archivados.
    """
    ids = list(dict.fromkeys(expediente_ids))
    if not ids:
        return {}

    datos: dict[int, _Datos] = {}
    for exp_id, fc, archivado in await _todas(db, ids, lambda lote: select(
        Expediente.id, Expediente.fecha_creacion, Expediente.archivado
    ).where(Expediente.id.in_(lote))):
        if not archivado:
            datos[exp_id] = _Datos(fecha_creacion=fc.date() if hasattr(fc, "date") else fc)
    ids = [i for i in ids if i in datos]
    if not ids:
        return {}

    # Respuesta (la primera) y su medida preventiva.
    respuestas = {}
    for r in await _todas(db, ids, lambda lote: select(
        EtapaRespuesta.id, EtapaRespuesta.expediente_id, EtapaRespuesta.fecha_creacion,
        EtapaRespuesta.fecha_radicado, EtapaRespuesta.requiere_medida_preventiva,
    ).where(EtapaRespuesta.expediente_id.in_(lote)).order_by(EtapaRespuesta.id)):
        d = datos[r.expediente_id]
        d.tiene_respuesta = True
        if d.respuesta is None:
            d.respuesta = r
            respuestas[r.id] = d
    for m in await _todas(db, list(respuestas), lambda lote: select(
        MedidaPreventiva.id, MedidaPreventiva.etapa_respuesta_id, MedidaPreventiva.acto_administrativo_id,
    ).where(MedidaPreventiva.etapa_respuesta_id.in_(lote))):
        respuestas[m.etapa_respuesta_id].medida = m

    # Informes técnicos (el primero de cada tipo).
    for inf in await _todas(db, ids, lambda lote: select(
        InformeTecnico.id, InformeTecnico.expediente_id, InformeTecnico.tipo_informe,
        InformeTecnico.profesional_asignado_id, InformeTecnico.fecha_programacion_visita,
        InformeTecnico.fecha_asignacion, InformeTecnico.fecha_aceptacion_informe, InformeTecnico.fecha_creacion,
    ).where(InformeTecnico.expediente_id.in_(lote)).order_by(InformeTecnico.id)):
        datos[inf.expediente_id].informes.setdefault((inf.tipo_informe or "").upper(), inf)

    # Conceptos (uno por instancia, el primero por id).
    conceptos = {}
    for c in await _todas(db, ids, lambda lote: select(
        EtapaAcogerConcepto.id, EtapaAcogerConcepto.expediente_id, EtapaAcogerConcepto.instancia,
        EtapaAcogerConcepto.tipo_acogida_concepto, EtapaAcogerConcepto.acto_administrativo_id,
        EtapaAcogerConcepto.fecha_termino_calculada, EtapaAcogerConcepto.dias_termino,
    ).where(EtapaAcogerConcepto.expediente_id.in_(lote)).order_by(EtapaAcogerConcepto.id)):
        d = datos[c.expediente_id]
        atributo = "concepto_seguimiento" if c.instancia == INSTANCIA_SEGUIMIENTO else "concepto"
        if getattr(d, atributo) is None:
            setattr(d, atributo, c)
            conceptos[c.id] = d
    for s in await _todas(db, list(conceptos), lambda lote: select(
        SolicitudInformacion.etapa_acoger_concepto_id, SolicitudInformacion.fecha_radicado,
        SolicitudInformacion.fecha_radicado_respuesta,
    ).where(SolicitudInformacion.etapa_acoger_concepto_id.in_(lote))):
        conceptos[s.etapa_acoger_concepto_id].solicitudes[s.etapa_acoger_concepto_id] = s
    for o in await _todas(db, list(conceptos), lambda lote: select(
        OficioRemite.etapa_acoger_concepto_id, OficioRemite.fecha_remitido, OficioRemite.archivo_remite_id,
    ).where(OficioRemite.etapa_acoger_concepto_id.in_(lote))):
        conceptos[o.etapa_acoger_concepto_id].oficios[o.etapa_acoger_concepto_id] = o

    # Cierre (el primero).
    for ci in await _todas(db, ids, lambda lote: select(
        EtapaCierre.id, EtapaCierre.expediente_id, EtapaCierre.acto_administrativo_id,
    ).where(EtapaCierre.expediente_id.in_(lote)).order_by(EtapaCierre.id)):
        if datos[ci.expediente_id].cierre is None:
            datos[ci.expediente_id].cierre = ci

    # Primera versión de cada documento (informe o acto), en cualquiera de sus
    # procesos (también los cerrados por reasignación).
    for exp_id, etapa_tipo, ref_id, primera in await _todas(db, ids, lambda lote: select(
        DocumentoProceso.expediente_id, DocumentoProceso.etapa_tipo, DocumentoProceso.etapa_ref_id,
        func.min(DocumentoProcesoVersion.fecha_subida),
    ).join(DocumentoProcesoVersion, DocumentoProcesoVersion.proceso_id == DocumentoProceso.id)
      .where(DocumentoProceso.expediente_id.in_(lote))
      .group_by(DocumentoProceso.expediente_id, DocumentoProceso.etapa_tipo, DocumentoProceso.etapa_ref_id)):
        datos[exp_id].primeras_versiones[(etapa_tipo, ref_id)] = _fecha_local(primera)

    # Notificaciones de los actos de auto de requerimiento.
    actos = {}
    for d in datos.values():
        for c in (d.concepto, d.concepto_seguimiento):
            if c is not None and c.tipo_acogida_concepto == AUTO_REQUERIMIENTO and c.acto_administrativo_id:
                actos[c.acto_administrativo_id] = d
    notifs_por_acto: dict[int, list] = defaultdict(list)
    for n in await _todas(db, list(actos), lambda lote: select(
        Notificacion.id, Notificacion.acto_administrativo_id, Notificacion.fecha_constancia_citacion,
    ).where(
        Notificacion.acto_administrativo_id.in_(lote),
        Notificacion.fecha_constancia_citacion.isnot(None),
        Notificacion.notificacion_exitosa == False,  # noqa: E712 (NULL no cuenta, como antes)
    ).order_by(Notificacion.id)):
        notifs_por_acto[n.acto_administrativo_id].append(n)
    for acto_id, fecha in await _todas(db, list(actos), lambda lote: select(
        Notificacion.acto_administrativo_id, func.min(Notificacion.fecha_notificacion),
    ).where(
        Notificacion.acto_administrativo_id.in_(lote),
        Notificacion.notificacion_exitosa.is_(True),
    ).group_by(Notificacion.acto_administrativo_id)):
        actos[acto_id].primera_exitosa[acto_id] = _fecha_local(fecha)

    resultado = {}
    for exp_id in ids:
        d = datos[exp_id]
        if d.concepto is not None:
            d.notifs_constancia = notifs_por_acto.get(d.concepto.acto_administrativo_id, [])
        if d.concepto_seguimiento is not None:
            d.notifs_seguimiento = notifs_por_acto.get(d.concepto_seguimiento.acto_administrativo_id, [])
        resultado[exp_id] = _calcular(d, fecha_hoy)
    return resultado


async def calcular_alertas_expediente(expediente_id: int, db: AsyncSession, fecha_hoy: date) -> dict:
    """Alertas de un expediente (``{}`` si no existe o está archivado)."""
    return (await calcular_alertas_expedientes([expediente_id], db, fecha_hoy)).get(expediente_id, {})
