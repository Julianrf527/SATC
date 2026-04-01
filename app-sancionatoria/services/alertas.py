from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dateutil.relativedelta import relativedelta
from enum import Enum
from dotenv import load_dotenv
import logging
import os



# -------- MODELS ------------
from db.models.tipo_etapa import TipoEtapa
from db.models.etapa import Etapa
from db.models.acto_admin import ActoAdministrativo
from db.models.notificacion import Notificacion
# from db.models.involucrado_notificacion import InvolucradoNotificacion  # Módulo no existe
# from db.models.formulacion_cargos import FormulacionCargos  # Módulo no existe


load_dotenv()
GATEWAY_URL = os.getenv("API_GATEWAY_URL")
SERVICE_SECRET_KEY =os.getenv("SERVICE_SECRET_KEY")

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


from utils.funtions import calcular_dias_laborales
from utils.funtions import obtener_fecha_despues_dias_laborales


# --------- MODELS------
class EstadoSemaforo(str, Enum):
    """Estados del semáforo de alertas"""
    VERDE = "verde"
    AMARILLO = "amarillo"
    ROJO = "rojo"
    VENCIDO = "vencido"




def calcular_estado_semaforo(dias_transcurridos: int, dias_totales: int) -> Dict:
    """
    Calcula el estado del semáforo basado en los días transcurridos.
    
    División en tercios:
    - Verde: 0% - 33% del tiempo
    - Amarillo: 33% - 66% del tiempo
    - Rojo: 66% - 100% del tiempo
    - Vencido: > 100% del tiempo
    
    Args:
        dias_transcurridos: Días que han pasado desde el inicio
        dias_totales: Total de días disponibles para la tarea
        
    Returns:
        Dict con estado del semáforo, porcentaje y información adicional
    """
    if dias_transcurridos < 0:
        dias_transcurridos = 0
    
    # Calcular porcentaje de avance
    porcentaje = (dias_transcurridos / dias_totales * 100) if dias_totales > 0 else 100
    
    # Determinar estado del semáforo
    if porcentaje > 100:
        estado = EstadoSemaforo.VENCIDO
        urgencia = "critico"
    elif porcentaje >= 66:
        estado = EstadoSemaforo.ROJO
        urgencia = "alta"
    elif porcentaje >= 33:
        estado = EstadoSemaforo.AMARILLO
        urgencia = "media"
    else:
        estado = EstadoSemaforo.VERDE
        urgencia = "baja"
    
    dias_restantes = dias_totales - dias_transcurridos
    
    return {
        "estado": estado.value,
        "color_hex": {
            "verde": "#10B981",      # green-500
            "amarillo": "#F59E0B",   # amber-500
            "rojo": "#EF4444",       # red-500
            "vencido": "#7F1D1D"     # red-900
        }[estado.value],
        "porcentaje_avance": round(min(porcentaje, 100), 2),
        "urgencia": urgencia,
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": max(dias_restantes, 0),
        "dias_totales": dias_totales,
        "esta_vencido": porcentaje > 100
    }

# Función auxiliar para calcular alertas de un expediente
async def calcular_alertas_expediente(
    radicado: str,
    db: AsyncSession,
    fecha_hoy: date
) -> Dict:
    """
    Calcula todas las alertas para un expediente específico.
    
    Args:
        radicado: Número de radicado del expediente
        db: Sesión de base de datos
        fecha_hoy: Fecha actual para cálculos
        
    Returns:
        Diccionario con las alertas encontradas
    """
    alertas = {}
    
    # ALERTA 1: 6 meses para iniciar sancionatorio desde indagación preliminar
    stmt = (
        select(Etapa.fecha_inicio)
        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
        .where(TipoEtapa.nombre == "INDAGACION PRELIMINAR")
        .where(Etapa.expediente_radicado == radicado)
    )
    result = await db.execute(stmt)
    fecha_indagacion = result.scalar()

    if fecha_indagacion:
        # Verificar si ya existe proceso sancionatorio
        stmt = (
            select(Etapa.fecha_inicio)
            .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
            .where(TipoEtapa.nombre == "INICIO PROCESO SANCIONATORIO")
            .where(Etapa.expediente_radicado == radicado)
        )
        result = await db.execute(stmt)
        fecha_sancionatorio = result.scalar()

        if fecha_sancionatorio is None:
            fecha_indagacion = fecha_indagacion.date() if hasattr(fecha_indagacion, 'date') else fecha_indagacion
            dias_transcurridos = (fecha_hoy - fecha_indagacion).days
            fecha_limite = fecha_indagacion + relativedelta(months=6)
            dias_restantes = (fecha_limite - fecha_hoy).days
            
            # Calcular días totales (aproximadamente 180 días = 6 meses)
            dias_totales = (fecha_limite - fecha_indagacion).days
            semaforo = calcular_estado_semaforo(dias_transcurridos, dias_totales)
            
            alertas["alerta1"] = {
                "tipo": "inicio_sancionatorio",
                "etapa": "INDAGACION PRELIMINAR",
                "accion_requerida": "Iniciar proceso sancionatorio",
                "plazo_legal": "6 meses",
                "msg": f"Debe iniciar proceso sancionatorio. Han transcurrido {dias_transcurridos} días desde la indagación preliminar.",
                "fecha_inicio": fecha_indagacion.isoformat(),
                "fecha_limite": fecha_limite.isoformat(),
                "semaforo": semaforo
            }

    # ALERTA 2 y 3: Formulación de cargos - 80 días para decisión de fondo y 10 días para descargos
    stmt = (
        select(Etapa.id)
        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
        .where(TipoEtapa.nombre == "FORMULACION DE CARGOS")
        .where(Etapa.expediente_radicado == radicado)
    )
    result = await db.execute(stmt)
    formulacion_id = result.scalar()
    
    logger.info(f"[ALERTA2-DEBUG] Radicado: {radicado}, Formulacion_id: {formulacion_id}")

    if formulacion_id:
        # Obtener acto administrativo de formulación
        stmt = select(ActoAdmin.id, ActoAdmin.fecha_numerado).where(
            ActoAdmin.etapa_id == formulacion_id
        )
        result = await db.execute(stmt)
        acto_admin = result.first()
        
        logger.info(f"[ALERTA2-DEBUG] Acto admin encontrado: {acto_admin}")

        if acto_admin:
            # Obtener notificaciones exitosas
            stmt = (
                select(InvolucradoNotificacion.notificacion_exitosa, 
                       InvolucradoNotificacion.fecha_notificacion)
                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                .where(Notificacion.acto_admin_id == acto_admin.id)
            )
            result = await db.execute(stmt)
            notificaciones = result.all()
            
            logger.info(f"[ALERTA2-DEBUG] Total notificaciones: {len(notificaciones)}")

            # Verificar si hay al menos una notificación exitosa
            notificaciones_exitosas = [n for n in notificaciones if n.notificacion_exitosa]
            
            logger.info(f"[ALERTA2-DEBUG] Notificaciones exitosas: {len(notificaciones_exitosas)}")
            
            if notificaciones_exitosas:
                # Obtener la fecha de notificación más temprana
                fecha_noti = min(
                    (n.fecha_notificacion for n in notificaciones_exitosas if n.fecha_notificacion),
                    default=None
                )
                
                logger.info(f"[ALERTA2-DEBUG] Fecha notificación: {fecha_noti}")
                
                if fecha_noti:
                    fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
                    
                    # ALERTA 2: 80 días para decisión de fondo
                    stmt = (
                        select(Etapa.id)
                        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
                        .where(TipoEtapa.nombre == "DECISION DE FONDO")
                        .where(Etapa.expediente_radicado == radicado)
                    )
                    result = await db.execute(stmt)
                    decision_id = result.scalar()
                    
                    logger.info(f"[ALERTA2-DEBUG] Decision_id: {decision_id}")
                    
                    # Si no existe decisión de fondo, validar alerta
                    if not decision_id:
                        dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                        semaforo = calcular_estado_semaforo(dias_transcurridos, 80)
                        
                        logger.info(f"[ALERTA2-DEBUG] Generando alerta2: días={dias_transcurridos}")
                        
                        alertas["alerta2"] = {
                            "tipo": "decision_fondo",
                            "etapa": "FORMULACION DE CARGOS",
                            "accion_requerida": "Crear etapa decisión de fondo",
                            "plazo_legal": "80 días laborales",
                            "msg": f"Debe crear la etapa decisión de fondo. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                            "fecha_notificacion": fecha_noti.isoformat(),
                            "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 80).isoformat(),
                            "semaforo": semaforo
                        }
                    elif decision_id:
                        # Verificar si hay acto administrativo en decisión de fondo
                        stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == decision_id)
                        result = await db.execute(stmt)
                        acto_decision = result.scalar()
                        
                        logger.info(f"[ALERTA2-DEBUG] Acto decisión: {acto_decision}")
                        
                        if not acto_decision:
                            dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                            semaforo = calcular_estado_semaforo(dias_transcurridos, 80)
                            
                            logger.info(f"[ALERTA2-DEBUG] Generando alerta2 (sin acto): días={dias_transcurridos}")
                            
                            alertas["alerta2"] = {
                                "tipo": "decision_fondo",
                                "etapa": "FORMULACION DE CARGOS",
                                "accion_requerida": "Emitir acto administrativo en decisión de fondo",
                                "plazo_legal": "80 días laborales",
                                "msg": f"Debe emitir acto administrativo en decisión de fondo. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                                "fecha_notificacion": fecha_noti.isoformat(),
                                "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 80).isoformat(),
                                "semaforo": semaforo
                            }
                    
                    # ALERTA 3: 10 días para presentar descargos
                    stmt = select(FormulacionCargos.url_documento).where(
                        FormulacionCargos.etapa_id == formulacion_id
                    )
                    result = await db.execute(stmt)
                    url_doc = result.scalar()

                    if url_doc:
                        dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                        semaforo = calcular_estado_semaforo(dias_transcurridos, 10)
                        
                        alertas["alerta3"] = {
                            "tipo": "presentacion_descargos",
                            "etapa": "FORMULACION DE CARGOS",
                            "accion_requerida": "Presentar descargos",
                            "plazo_legal": "10 días laborales",
                            "msg": f"Debe presentar descargos. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                            "fecha_notificacion": fecha_noti.isoformat(),
                            "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                            "semaforo": semaforo
                        }

    # ALERTA 4: 30 días para presentar informe técnico en apertura etapa probatoria
    stmt = (
        select(Etapa.id)
        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
        .where(TipoEtapa.nombre == "APERTURA ETAPA PROBATORIA")
        .where(Etapa.expediente_radicado == radicado)
    )
    result = await db.execute(stmt)
    apertura_id = result.scalar()

    if apertura_id:
        stmt = select(ActoAdmin.id, ActoAdmin.fecha_numerado).where(
            ActoAdmin.etapa_id == apertura_id
        )
        result = await db.execute(stmt)
        acto_admin = result.first()

        if acto_admin:
            stmt = (
                select(InvolucradoNotificacion.notificacion_exitosa, 
                       InvolucradoNotificacion.fecha_notificacion)
                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                .where(Notificacion.acto_admin_id == acto_admin.id)
            )
            result = await db.execute(stmt)
            notificaciones = result.all()

            notificaciones_exitosas = [n for n in notificaciones if n.notificacion_exitosa]
            
            if notificaciones_exitosas:
                # Verificar si ya existe informe técnico
                stmt = select(1).where(
                    Documento.etapa_id == apertura_id,
                    Documento.nombre == "Informe Tecnico"
                ).limit(1)
                result = await db.execute(stmt)
                existe_informe = result.scalar()

                if not existe_informe:
                    fecha_noti = min(
                        (n.fecha_notificacion for n in notificaciones_exitosas if n.fecha_notificacion),
                        default=None
                    )
                    
                    if fecha_noti:
                        fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
                        dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                        semaforo = calcular_estado_semaforo(dias_transcurridos, 30)
                        
                        alertas["alerta4"] = {
                            "tipo": "informe_tecnico",
                            "etapa": "APERTURA ETAPA PROBATORIA",
                            "accion_requerida": "Presentar informe técnico",
                            "plazo_legal": "30 días laborales",
                            "msg": f"Debe presentar informe técnico. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                            "fecha_notificacion": fecha_noti.isoformat(),
                            "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 30).isoformat(),
                            "semaforo": semaforo
                        }

    # ALERTA 5: 10 días para presentar alegatos de conclusión
    stmt = (
        select(Etapa.id)
        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
        .where(TipoEtapa.nombre == "CIERRE ETAPA PROBATORIA")
        .where(Etapa.expediente_radicado == radicado)
    )
    result = await db.execute(stmt)
    cierre_id = result.scalar()

    if cierre_id:
        stmt = select(ActoAdmin.id, ActoAdmin.fecha_numerado).where(
            ActoAdmin.etapa_id == cierre_id
        )
        result = await db.execute(stmt)
        acto_admin = result.first()

        if acto_admin:
            stmt = (
                select(InvolucradoNotificacion.notificacion_exitosa, 
                       InvolucradoNotificacion.fecha_notificacion)
                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                .where(Notificacion.acto_admin_id == acto_admin.id)
            )
            result = await db.execute(stmt)
            notificaciones = result.all()

            notificaciones_exitosas = [n for n in notificaciones if n.notificacion_exitosa]
            
            if notificaciones_exitosas:
                # Verificar si ya existe alegato de conclusión
                stmt = select(1).where(
                    Documento.etapa_id == cierre_id,
                    Documento.nombre == "Alegato de conclusion"
                ).limit(1)
                result = await db.execute(stmt)
                existe_alegato = result.scalar()

                if not existe_alegato:
                    fecha_noti = min(
                        (n.fecha_notificacion for n in notificaciones_exitosas if n.fecha_notificacion),
                        default=None
                    )
                    
                    if fecha_noti:
                        fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
                        dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                        semaforo = calcular_estado_semaforo(dias_transcurridos, 10)
                        
                        alertas["alerta5"] = {
                            "tipo": "alegato_conclusion",
                            "etapa": "CIERRE ETAPA PROBATORIA",
                            "accion_requerida": "Presentar alegato de conclusión",
                            "plazo_legal": "10 días laborales",
                            "msg": f"Debe presentar alegato de conclusión. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                            "fecha_notificacion": fecha_noti.isoformat(),
                            "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                            "semaforo": semaforo
                        }

    # ALERTA 6: 10 días para presentar recurso o 1 año para resolver recurso
    stmt = (
        select(Etapa.id)
        .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
        .where(TipoEtapa.nombre == "DECISION DE FONDO")
        .where(Etapa.expediente_radicado == radicado)
    )
    result = await db.execute(stmt)
    decision_id = result.scalar()

    if decision_id:
        stmt = select(ActoAdmin.id, ActoAdmin.fecha_numerado).where(
            ActoAdmin.etapa_id == decision_id
        )
        result = await db.execute(stmt)
        acto_admin = result.first()

        if acto_admin:
            stmt = (
                select(InvolucradoNotificacion.notificacion_exitosa, 
                       InvolucradoNotificacion.fecha_notificacion)
                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                .where(Notificacion.acto_admin_id == acto_admin.id)
            )
            result = await db.execute(stmt)
            notificaciones = result.all()

            notificaciones_exitosas = [n for n in notificaciones if n.notificacion_exitosa]
            
            if notificaciones_exitosas:
                fecha_noti = min(
                    (n.fecha_notificacion for n in notificaciones_exitosas if n.fecha_notificacion),
                    default=None
                )
                
                if fecha_noti:
                    fecha_noti = fecha_noti.date() if hasattr(fecha_noti, 'date') else fecha_noti
                    
                    # Verificar si existe recurso
                    stmt = select(1).where(
                        Documento.etapa_id == decision_id,
                        Documento.nombre == "Recurso"
                    ).limit(1)
                    result = await db.execute(stmt)
                    existe_recurso = result.scalar()

                    if not existe_recurso:
                        # Alerta para presentar recurso (10 días)
                        dias_transcurridos = calcular_dias_laborales(fecha_noti, fecha_hoy)
                        semaforo = calcular_estado_semaforo(dias_transcurridos, 10)
                        
                        alertas["alerta6"] = {
                            "tipo": "presentacion_recurso",
                            "etapa": "DECISION DE FONDO",
                            "accion_requerida": "Presentar recurso",
                            "plazo_legal": "10 días laborales",
                            "msg": f"Puede presentar recurso. Han transcurrido {dias_transcurridos} días laborales desde la notificación.",
                            "fecha_notificacion": fecha_noti.isoformat(),
                            "fecha_limite": obtener_fecha_despues_dias_laborales(fecha_noti, 10).isoformat(),
                            "semaforo": semaforo
                        }
                    elif existe_recurso:
                        # Si existe recurso, verificar resolución (1 año)
                        stmt = (
                            select(Etapa.id)
                            .join(TipoEtapa, TipoEtapa.id == Etapa.tipo_etapa_id)
                            .where(TipoEtapa.nombre == "PROBATORIA DE RECURSO")
                            .where(Etapa.expediente_radicado == radicado)
                        )
                        result = await db.execute(stmt)
                        recurso_id = result.scalar()

                        if recurso_id:
                            # Buscar acto_admin "recurso"
                            stmt = select(ActoAdmin.id).where(
                                ActoAdmin.etapa_id == recurso_id,
                                ActoAdmin.nivel_auxiliar == True
                            )
                            result = await db.execute(stmt)
                            acto_recurso = result.scalar()

                            if acto_recurso:
                                # Verificar notificaciones del recurso
                                stmt = (
                                    select(InvolucradoNotificacion.notificacion_exitosa)
                                    .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                                    .where(Notificacion.acto_admin_id == acto_recurso)
                                )
                                result = await db.execute(stmt)
                                noti_recurso = result.scalars().all()

                                if not any(noti_recurso):
                                    dias_transcurridos = (fecha_hoy - fecha_noti).days
                                    semaforo = calcular_estado_semaforo(dias_transcurridos, 365)
                                    
                                    alertas["alerta6"] = {
                                        "tipo": "resolucion_recurso",
                                        "etapa": "PROBATORIA DE RECURSO",
                                        "accion_requerida": "Notificar acto administrativo de decisión en recurso",
                                        "plazo_legal": "1 año",
                                        "msg": f"Debe notificar decisión del recurso. Han transcurrido {dias_transcurridos} días desde que se presentó el recurso.",
                                        "fecha_presentacion": fecha_noti.isoformat(),
                                        "fecha_limite": (fecha_noti + relativedelta(years=1)).isoformat(),
                                        "semaforo": semaforo
                                    }
                        elif not recurso_id:
                            # Buscar acto "decision"
                            stmt = select(ActoAdmin.id).where(
                                ActoAdmin.etapa_id == decision_id,
                                ActoAdmin.nivel_auxiliar == True
                            
                            )
                            result = await db.execute(stmt)
                            acto_decision = result.scalar()

                            if acto_decision:
                                stmt = (
                                    select(InvolucradoNotificacion.notificacion_exitosa)
                                    .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                                    .where(Notificacion.acto_admin_id == acto_decision)
                                )
                                result = await db.execute(stmt)
                                noti_decision = result.scalars().all()

                                if not any(noti_decision):
                                    dias_transcurridos = (fecha_hoy - fecha_noti).days
                                    semaforo = calcular_estado_semaforo(dias_transcurridos, 365)
                                    
                                    alertas["alerta6"] = {
                                        "tipo": "notificacion_recurso",
                                        "etapa": "DECISION DE FONDO",
                                        "accion_requerida": "Notificar acto administrativo de recurso",
                                        "plazo_legal": "1 año",
                                        "msg": f"Debe notificar el acto administrativo. Han transcurrido {dias_transcurridos} días desde que se presentó el recurso.",
                                        "fecha_presentacion": fecha_noti.isoformat(),
                                        "fecha_limite": (fecha_noti + relativedelta(years=1)).isoformat(),
                                        "semaforo": semaforo
                                    }

    return alertas