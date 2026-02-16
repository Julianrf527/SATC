from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
import logging
import os


# -------- MODELS ------------
from db.models.tipo_etapa import TipoEtapa
from db.models.etapa import Etapa
from db.models.acto_admin import ActoAdmin
from db.models.comunicacion import Comunicacion
from db.models.documento import Documento
from db.models.medida_preventiva import MedidaPreventiva
from db.models.notificacion import Notificacion
from db.models.tipo_medida import TipoMedida
from db.models.involucrado_notificacion import InvolucradoNotificacion
from db.models.formulacion_cargos import FormulacionCargos
from db.models.decision_fondo import DecisionFondo
from db.models.tipo_sancion import TipoSancion
from db.models.cesacion import Cesacion
from db.models.tipo_cesacion import TipoCesacion
from db.models.log_auditoria import LogAuditoria


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

#Crud Auxiliar
async def insert_log_auditoria(
    db: AsyncSession,
    usuario_id: int,
    tabla_afectada: str,
    tipo_operacion: str,
    descripcion: str,
    expediente_radicado: str | None = None,
    id_registro: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
):
    try:
        stmt = insert(LogAuditoria).values(
            usuario_id=usuario_id,
            tabla_afectada=tabla_afectada,
            tipo_operacion=tipo_operacion,
            descripcion=descripcion,
            expediente_radicado=expediente_radicado,
            id_registro=id_registro,
            fecha=datetime.utcnow(),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        ).returning(LogAuditoria.id)
        
        result = await db.execute(stmt)
        inserted_id = result.scalar()
        return {"ok": True, "id": inserted_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def get_creable(etapa_consulta: str, etapa_name_db: str, radicado: str, db: AsyncSession):
    stmt = (
        select(Etapa.id)
        .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
        .where(
            Etapa.expediente_radicado == radicado,
            TipoEtapa.nombre == etapa_name_db
        )
    )
    etapa_id = await db.scalar(stmt)

    if not etapa_id:
        creable = {
            "status": False,
            "msg": f'No se ha creado la etapa "{etapa_consulta}" aún.'
        }
    else:

        # Buscar acto administrativo asociado
        stmt = select(ActoAdmin.id,ActoAdmin.fecha_numerado).where(ActoAdmin.etapa_id == etapa_id)
        result = await db.execute(stmt)
        ad = result.first()

        if not ad:
            creable = {
                "status": False,
                "msg": f'No se ha creado acto administrativo para "{etapa_consulta}" aún.'
            }
        else:
            # Verificar notificación exitosa
            stmt = (
                select(InvolucradoNotificacion.notificacion_exitosa)
                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                .where(Notificacion.acto_admin_id == ad.id)
            )
            result = await db.execute(stmt)
            notificaciones = result.scalars().all()

            if not notificaciones or not any(notificaciones):
                creable = {
                    "status": False,
                    "msg":
                    f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de la etapa: "{etapa_consulta}".'
                }
            else:
                creable = {"status": True}
    return creable

async def get_acto_admin(etapa_id: int,notificacion: bool, db:AsyncSession, nivel: bool = None):
    #Si noti = False, se evalua comunicacion
    if nivel:
        stmt = select(ActoAdmin).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == nivel)
    else:
        stmt = select(ActoAdmin).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == False)

    acto_admin = await db.scalar(stmt)
    acto_admin_data = {}

    if acto_admin:

        acto_admin_data = {
            "id": acto_admin.id,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado),
            "url_acto": acto_admin.url_acto,
            "tipo_acto": acto_admin.tipo_acto,
            "fecha_creacion": str(acto_admin.fecha_creacion),
            "etapa_id": acto_admin.etapa_id,
            "nivel_auxiliar": acto_admin.nivel_auxiliar
        }

        # Buscar notificacion asociada
        if notificacion:
            stmt = select(Notificacion).where(Notificacion.acto_admin_id == acto_admin.id)
            noti = await db.scalar(stmt)

            notificacion_data = {}
            if noti:
                stmt = select(InvolucradoNotificacion).where(InvolucradoNotificacion.notificacion_id == noti.id)
                involucrados_noti = (await db.execute(stmt)).scalars().all()
                involucrados_noti_data = [
                    {
                        "id": inv_noti.id,
                        "involucrado_id": inv_noti.involucrado_id,
                        "numerado": inv_noti.numerado,
                        "fecha_numerado": str(inv_noti.fecha_numerado),
                        "fecha_envio_citacion": str(inv_noti.fecha_envio_citacion),
                        "fecha_constancia_citacion": str(inv_noti.fecha_constancia_citacion),
                        "notificacion_exitosa": inv_noti.notificacion_exitosa,
                        "url_documento" : inv_noti.url_documento,
                        "url_doc_citacion": inv_noti.url_doc_citacion,
                        "tipo_notificacion_id": inv_noti.tipo_notificacion_id,
                    }
                    for inv_noti in involucrados_noti
                ]

                notificacion_data = {
                    "id": noti.id,
                    "fecha_creacion": str(noti.fecha_creacion),
                    "involucrados": involucrados_noti_data
                }
            acto_admin_data["notificacion"]= notificacion_data
        else:
            # Buscar comunicación asociada
            stmt = select(Comunicacion).where(Comunicacion.acto_admin_id == acto_admin.id)
            comunicacion = await db.scalar(stmt)
            
            comunicacion_data = {}
            if comunicacion:
                comunicacion_data = {
                    "id": comunicacion.id,
                    "numerado": comunicacion.numerado,
                    "fecha_numerado": str(comunicacion.fecha_numerado),
                    "fecha_envio": str(comunicacion.fecha_envio),
                    "fecha_creacion": str(comunicacion.fecha_creacion),
                    "url_documento": str(comunicacion.url_documento)
                }
            acto_admin_data["comunicacion"]= comunicacion_data

        
    return acto_admin_data

#Crud Get Etapas
async def get_indagacion_preliminar(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'INDAGACION PRELIMINAR')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "indagacion": {"tipo_etapa_id": tipo_etapa_id }
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id, False, db)

        indagacion = {
            "etapa_id": etapa_id,
            "acto_admin": acto_admin_data,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "indagacion": indagacion,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_indagacion_preliminar: {e}")
        return {
            "ok": False
        }

async def get_medida_preventiva(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'DETALLE MEDIDA PREVENTIVA')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "medida": {"tipo_etapa_id": tipo_etapa_id}
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]
        #Si existe la etapa, buscar la info
        stmt = select(MedidaPreventiva).where(MedidaPreventiva.etapa_id == etapa_id)
        info = await db.scalar(stmt)
        info_data = {}
        if info:
            info_data = {
                "id": info.id,
                "tipo_medida_id": info.tipo_medida_id,
                "cantidad": info.cantidad,
                "especie": info.especie,
                "estado_medida": info.estado_medida,
            }
        
        stmt = select(TipoMedida)
        tipo_medidas = (await db.execute(stmt)).scalars().all()
        tipo_medidas_data = [
                {
                    "id": tm.id,
                    "nombre": tm.nombre,
                }
                for tm in tipo_medidas
            ]
        
        info_data["tipo_medidas"] = tipo_medidas_data


        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id, False, db)

        medida = {
            "etapa_id": etapa_id,
            "informacion": info_data,
            "acto_admin": acto_admin_data,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "medida": medida,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_medida_preventiva: {e}")
        return {
            "ok": False
        }

async def get_inicio_proceso_sancionatorio(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'INICIO PROCESO SANCIONATORIO')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "inicio_proceso": {"tipo_etapa_id": tipo_etapa_id}
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id, True, db)

        proceso = {
            "etapa_id": etapa_id,
            "acto_admin": acto_admin_data,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "inicio_proceso": proceso,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_medida_preventiva: {e}")
        return {
            "ok": False
        }

async def get_cesacion(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'CESACION')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }

        #Permisos
        creable = await get_creable("Inicio Proceso Sancionatorio","INICIO PROCESO SANCIONATORIO", radicado, db)

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "cesacion": {"tipo_etapa_id": tipo_etapa_id,"creable": creable},
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]
        
        #Si existe la etapa, buscar la info
        stmt = select(Cesacion).where(Cesacion.etapa_id == etapa_id)
        info = await db.scalar(stmt)
        info_data = {}
        if info:
            info_data = {
                "id": info.id,
                "tipo_cesacion_id": info.tipo_cesacion_id
            }
        
        stmt = select(TipoCesacion)
        tipo_cesacion = (await db.execute(stmt)).scalars().all()
        tipo_cesacion_data = [
                {
                    "id": tm.id,
                    "nombre": tm.nombre,
                }
                for tm in tipo_cesacion
            ]
        
        info_data["tipo_cesacion"] = tipo_cesacion_data

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id, True, db)

        cesacion = {
            "etapa_id": etapa_id,
            "informacion": info_data,
            "acto_admin": acto_admin_data,
            "documento": documentos_data,
            "creable": creable,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "cesacion": cesacion,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_medida_preventiva: {e}")
        return {
            "ok": False
        }

async def get_formulacion_cargos(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'FORMULACION DE CARGOS')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }
        #Permisos
        creable = await get_creable("Inicio Proceso Sancionatorio","INICIO PROCESO SANCIONATORIO", radicado, db)

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "formulacion_cargos": {"tipo_etapa_id": tipo_etapa_id,"creable": creable}
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]
        
        #Si existe la etapa, buscar la info
        stmt = select(FormulacionCargos).where(FormulacionCargos.etapa_id == etapa_id)
        info = await db.scalar(stmt)
        info_data = {}
        if info:
            info_data = {
                "id": info.id,
                "descargos": info.descargos,
                "url_documento": info.url_documento
            }

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id,True, db)

        formulacion = {
            "etapa_id": etapa_id,
            "informacion": info_data,
            "acto_admin": acto_admin_data,
            "creable": creable,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "formulacion_cargos": formulacion,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_formulacion_cargos: {e}")
        return {
            "ok": False
        }

async def get_apertura_etapa_probatoria(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'APERTURA ETAPA PROBATORIA')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }
        #Permisos
        creable = await get_creable("Formulacion de Cargos", "FORMULACION DE CARGOS", radicado, db)

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "apertura_etapa_probatoria": {"tipo_etapa_id": tipo_etapa_id,"creable": creable}
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id,True,db)

        apertura = {
            "etapa_id": etapa_id,
            "acto_admin": acto_admin_data,
            "creable": creable,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "apertura_etapa_probatoria": apertura,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_apertura_etapa_probatoria: {e}")
        return {
            "ok": False
        }

async def get_cierre_etapa_probatoria(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'CIERRE ETAPA PROBATORIA')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }
        #Permisos
        creable = await get_creable("Apertura Etapa Probatoria","APERTURA ETAPA PROBATORIA", radicado, db)

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "cierre_etapa_probatoria": {"tipo_etapa_id": tipo_etapa_id,"creable": creable}
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id,True,db)

        cierre = {
            "etapa_id": etapa_id,
            "acto_admin": acto_admin_data,
            "creable": creable,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "cierre_etapa_probatoria": cierre,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_ciere_etapa_probatoria: {e}")
        return {
            "ok": False
        }

async def get_decision_fondo(radicado: str, db: AsyncSession):
    try:
        print(f"[GET_DECISION_FONDO] Iniciando para radicado: {radicado}")
        
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'DECISION DE FONDO')
        tipo_etapa_id = await db.scalar(stmt)
        print(f"[GET_DECISION_FONDO] tipo_etapa_id encontrado: {tipo_etapa_id}")

        if not tipo_etapa_id:
            print(f"[GET_DECISION_FONDO] No se encontró tipo de etapa 'DECISION DE FONDO'")
            # Si no existe el tipo de etapa, devolver estructura vacía pero válida
            return {
                "ok": True,
                "decision_fondo": {
                    "creable": False
                }
            }
        
        print(f"[GET_DECISION_FONDO] Obteniendo permisos creable...")
        # Permisos
        creable = await get_creable("Cierre Etapa Probatoria", "CIERRE ETAPA PROBATORIA", radicado, db)

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "decision_fondo": {
                    "tipo_etapa_id": tipo_etapa_id,
                    "creable": creable
                }
            }

        # Consultar documentos
        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
            {
                "id": doc.id,
                "nombre": doc.nombre,
                "url_documento": doc.url_documento,
                "fecha_subida": str(doc.fecha_subida)
            }
            for doc in documentos
        ]

        # Consultar tipos de sanción
        stmt = select(TipoSancion)
        ts = await db.execute(stmt)
        ts = ts.scalars().all()
        tipo_sancion = [{"id": tipo.id, "nombre": tipo.nombre} for tipo in ts] if ts else []

        # Consultar información de la decisión
        stmt = select(DecisionFondo).where(DecisionFondo.etapa_id == etapa_id)
        info = await db.scalar(stmt)
        info_data = {"tipo_sancion": tipo_sancion}
        if info:
            info_data = {
                "id": info.id,
                "detalle": info.detalle,
                "tipo_sancion_id": info.tipo_sancion_id,
                "tipo_sancion": tipo_sancion
            }

        # Buscar PRIMER acto administrativo (tipo null)
        stmt = select(ActoAdmin).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == False)
        acto_admin = await db.scalar(stmt)
        acto_admin_data = {}

        if acto_admin:
            # Buscar notificación asociada
            stmt = select(Notificacion).where(Notificacion.acto_admin_id == acto_admin.id)
            noti = await db.scalar(stmt)

            notificacion_data = {}
            if noti:
                stmt = select(InvolucradoNotificacion).where(
                    InvolucradoNotificacion.notificacion_id == noti.id
                )
                involucrados_noti = (await db.execute(stmt)).scalars().all()
                involucrados_noti_data = [
                    {
                        "id": inv_noti.id,
                        "involucrado_id": inv_noti.involucrado_id,
                        "numerado": inv_noti.numerado,
                        "fecha_numerado": str(inv_noti.fecha_numerado),
                        "fecha_envio_citacion": str(inv_noti.fecha_envio_citacion),
                        "fecha_constancia_citacion": str(inv_noti.fecha_constancia_citacion),
                        "notificacion_exitosa": inv_noti.notificacion_exitosa,
                        "url_documento": inv_noti.url_documento,
                        "tipo_notificacion_id": inv_noti.tipo_notificacion_id,
                    }
                    for inv_noti in involucrados_noti
                ]

                notificacion_data = {
                    "id": noti.id,
                    "fecha_creacion": str(noti.fecha_creacion),
                    "involucrados": involucrados_noti_data
                }

            acto_admin_data = {
                "id": acto_admin.id,
                "numerado": acto_admin.numerado,
                "fecha_numerado": str(acto_admin.fecha_numerado),
                "url_acto": acto_admin.url_acto,
                "tipo_acto": acto_admin.tipo_acto,
                "fecha_creacion": str(acto_admin.fecha_creacion),
                "etapa_id": acto_admin.etapa_id,
                "notificacion": notificacion_data,
            }

        # Buscar SEGUNDO acto administrativo (el más reciente - recurso)
        acto_admin_recurso_data = {}
        creable_recurso = {"status": False, "msg": "Debe subir un documento de tipo 'Recurso' para crear este acto."}
        creable_acto_recurso = {"status": False, "msg": "Debe subir un documento de tipo 'Recurso' para crear este acto."}
        documentos_restringidos = []
        
        # Obtener la fecha de referencia: fecha de constancia de citación de notificación exitosa
        fecha_referencia_notificacion = None
        if acto_admin_data and acto_admin_data.get("notificacion") and acto_admin_data["notificacion"].get("involucrados"):
            # Buscar la fecha más reciente de constancia de citación exitosa
            for inv_noti in acto_admin_data["notificacion"]["involucrados"]:
                if inv_noti.get("notificacion_exitosa") and inv_noti.get("fecha_constancia_citacion"):
                    fecha_const = inv_noti["fecha_constancia_citacion"]
                    if isinstance(fecha_const, str):
                        fecha_const = fecha_const.split(' ')[0] if ' ' in fecha_const else fecha_const
                        fecha_const = datetime.strptime(fecha_const, "%Y-%m-%d").date()
                    
                    if fecha_referencia_notificacion is None or fecha_const > fecha_referencia_notificacion:
                        fecha_referencia_notificacion = fecha_const
        
        # Verificar si existe documento de recurso
        doc_recurso = next((doc for doc in documentos_data if doc["nombre"] == "Recurso"),None)

        if doc_recurso:
            fecha_subida = doc_recurso["fecha_subida"]

            # Convertir a datetime.date si es string
            if isinstance(fecha_subida, str):
                # Extraer solo la parte de la fecha si viene con timestamp completo
                fecha_subida = fecha_subida.split(' ')[0] if ' ' in fecha_subida else fecha_subida
                fecha_subida = datetime.strptime(fecha_subida, "%Y-%m-%d").date()

            # Validación para subir documento de recurso (10 días desde notificación exitosa)
            if not fecha_referencia_notificacion:
                creable_recurso = {"status": False, "msg": "Debe existir una notificación exitosa del acto administrativo de esta etapa."}
            else:
                # Validar 10 días desde fecha de constancia de citación exitosa
                if calcular_dias_laborales(fecha_referencia_notificacion, fecha_subida) <= 10:
                    creable_recurso = {"status": True}
                else:
                    creable_recurso = {"status": False, "msg": "Pasaron más de 10 días hábiles desde la notificación exitosa del acto de etapa"}
            
            # Validación para crear acto administrativo de recurso (15 días desde subida del documento)
            from datetime import date
            fecha_actual = date.today()
            dias_desde_subida = calcular_dias_laborales(fecha_subida, fecha_actual)
            
            if dias_desde_subida <= 15:
                creable_acto_recurso = {"status": True}
            else:
                creable_acto_recurso = {"status": False, "msg": "Pasaron más de 15 días hábiles desde la fecha de subida del documento Recurso"}
        else:
            # Si no existe documento de recurso y hay notificación exitosa, verificar si pasaron los 10 días
            if fecha_referencia_notificacion:
                from datetime import date
                fecha_actual = date.today()
                dias_transcurridos = calcular_dias_laborales(fecha_referencia_notificacion, fecha_actual)
                
                if dias_transcurridos > 10:
                    # Si pasaron más de 10 días, restringir el documento Recurso
                    documentos_restringidos.append("Recurso")
                    creable_recurso = {"status": False, "msg": "Pasaron más de 10 días hábiles desde la notificación exitosa del acto de etapa"}
                
        # Buscar si ya existe el acto de recurso (nivel = recurso)
        stmt = select(ActoAdmin).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == True)
        acto_recurso = await db.scalar(stmt)

        # Solo considerar como acto de recurso si hay más de un acto
        if acto_recurso and acto_recurso.id != acto_admin_data.get("id"):
            # Buscar notificación asociada
            stmt = select(Notificacion).where(Notificacion.acto_admin_id == acto_recurso.id)
            noti = await db.scalar(stmt)

            notificacion_data = {}
            if noti:
                stmt = select(InvolucradoNotificacion).where(
                    InvolucradoNotificacion.notificacion_id == noti.id
                )
                involucrados_noti = (await db.execute(stmt)).scalars().all()
                involucrados_noti_data = [
                    {
                        "id": inv_noti.id,
                        "involucrado_id": inv_noti.involucrado_id,
                        "numerado": inv_noti.numerado,
                        "fecha_numerado": str(inv_noti.fecha_numerado),
                        "fecha_envio_citacion": str(inv_noti.fecha_envio_citacion),
                        "fecha_constancia_citacion": str(inv_noti.fecha_constancia_citacion),
                        "notificacion_exitosa": inv_noti.notificacion_exitosa,
                        "url_documento": inv_noti.url_documento,
                        "tipo_notificacion_id": inv_noti.tipo_notificacion_id,
                    }
                    for inv_noti in involucrados_noti
                ]

                notificacion_data = {
                    "id": noti.id,
                    "fecha_creacion": str(noti.fecha_creacion),
                    "involucrados": involucrados_noti_data
                }

            acto_admin_recurso_data = {
                "id": acto_recurso.id,
                "numerado": acto_recurso.numerado,
                "fecha_numerado": str(acto_recurso.fecha_numerado),
                "url_acto": acto_recurso.url_acto,
                "tipo_acto": acto_recurso.tipo_acto,
                "fecha_creacion": str(acto_recurso.fecha_creacion),
                "etapa_id": acto_recurso.etapa_id,
                "notificacion": notificacion_data,
                "nivel_auxiliar": acto_recurso.nivel_auxiliar
            }
        

        decision = {
            "etapa_id": etapa_id,
            "informacion": info_data,
            "acto_admin": acto_admin_data,
            "acto_admin_recurso": acto_admin_recurso_data,
            "creable": creable,
            "creable_recurso": creable_recurso,
            "creable_acto_recurso": creable_acto_recurso,
            "documento": documentos_data,
            "documentos_restringidos": documentos_restringidos,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "decision_fondo": decision,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_decision_fondo: {e}")
        # Devolver estructura consistente incluso en error
        return {
            "ok": False,
            "decision_fondo": {},
            "error": str(e)
        }
    
async def get_recurso(radicado: str, db: AsyncSession):
    try:
        # Buscar id del tipo de etapa
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == 'PROBATORIA DE RECURSO')
        tipo_etapa_id = await db.scalar(stmt)

        if not tipo_etapa_id:
            return {
                "ok": False
            }
        
        #Permisos
        stmt = (
            select(Etapa.id)
            .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(
                Etapa.expediente_radicado == radicado,
                TipoEtapa.nombre == "EJECUCION DE LA SANCION"
            )
        )
        ejecucion_id = await db.scalar(stmt)
        if ejecucion_id:
            creable = {
                "status": False,
                "msg": f'Se ha creado la etapa "Ejecución de la Sanción", no es posible crear etapa de recurso.'
            }
        else:

            stmt = (
                select(Etapa.id)
                .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
                .where(
                    Etapa.expediente_radicado == radicado,
                    TipoEtapa.nombre == "DECISION DE FONDO"
                )
            )
            decision_id = await db.scalar(stmt)

            if not decision_id:
                creable = {
                    "status": False,
                    "msg": f'No se ha creado la etapa "Decision de Fondo" aún.'
                }
            else:
                
                stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == decision_id, ActoAdmin.nivel_auxiliar == True)
                ad_recurso_id = await db.scalar(stmt)

                if not ad_recurso_id:
                    creable = {
                        "status": False,
                        "msg": f'No se ha creado acto administrativo de recurso en "Decision de Fondo" aún.'
                    }
                else:
                    stmt = (
                        select(InvolucradoNotificacion.notificacion_exitosa)
                        .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                        .where(Notificacion.acto_admin_id == ad_recurso_id)
                    )
                    result = await db.execute(stmt)
                    notificaciones = result.scalars().all()
                    if not notificaciones or not any(notificaciones):
                        creable = {
                            "status": False,
                            "msg": f'No se ha notificado exitosamente el acto administrativo de recurso en "Decision de Fondo".'
                        }
                    else:
                        stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == decision_id, ActoAdmin.nivel_auxiliar == True)
                        ad_id = await db.scalar(stmt)
                        if not ad_id:
                            creable = {
                                "status": False,
                                "msg": f'No se ha creado acto administrativo en "Decision de Fondo" aún.'
                            }
                        else:
                            stmt = (
                            select(InvolucradoNotificacion.notificacion_exitosa)
                            .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                            .where(Notificacion.acto_admin_id == ad_id)
                            )
                            result = await db.execute(stmt)
                            notificaciones = result.scalars().all()

                            if not notificaciones or not any(notificaciones):
                                creable = {
                                    "status": False,
                                    "msg": f'No se ha notificado exitosamente el acto administrativo en "Decision de Fondo".'
                                }
                            else:
                                creable = {"status": True}

        # Buscar id de la etapa asociada
        stmt = select(Etapa.id).where(
            Etapa.expediente_radicado == radicado,
            Etapa.tipo_etapa_id == tipo_etapa_id
        )
        etapa_id = await db.scalar(stmt)

        # No existe la etapa
        if not etapa_id:
            return {
                "ok": True,
                "recurso": {"tipo_etapa_id": tipo_etapa_id,"creable": creable}
                
            }

        stmt = select(Documento).where(Documento.etapa_id == etapa_id)
        documentos = (await db.execute(stmt)).scalars().all()

        documentos_data = [
                {
                    "id": doc.id,
                    "nombre": doc.nombre,
                    "url_documento": doc.url_documento,
                    "fecha_subida": str(doc.fecha_subida)
                }
                for doc in documentos
            ]

        # Si existe la etapa, buscar el acto administrativo
        acto_admin_data = await get_acto_admin(etapa_id,True,db)

        acto_admin_decision = await get_acto_admin(etapa_id,True,db,True)

        recurso = {
            "etapa_id": etapa_id,
            "acto_admin": acto_admin_data,
            "acto_admin_decision": acto_admin_decision,
            "creable": creable,
            "documento": documentos_data,
            "tipo_etapa_id": tipo_etapa_id
        }

        return {
            "ok": True,
            "recurso": recurso,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en obtener_recurso: {e}")
        return {
            "ok": False
        }
