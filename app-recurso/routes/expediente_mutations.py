"""Creación y edición de la información base del expediente (plan §3, fase 4).

Prefijo en main.py: ``/expedientes``. Escritura: ``requiere_gestion`` (V1).

- ``POST /expedientes``: nace el expediente (llega el comprobante de pago).
- ``PUT /expedientes/{id}``: edita la información base, incluidas fuentes y
  usos, bajo el mismo bloqueo optimista (``version`` del cliente; 409 si otra
  persona lo modificó antes).

El comprobante de pago lo sube el front a app-docs y aquí llega su
``file_id``; se registra el uso en app-docs igual que infraction (``+1`` al
nuevo, ``-1`` al reemplazado).
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import Expediente, ExpedienteFuente, ExpedienteUso, UsoAgua
from services.concurrencia import actualizar_versionado, integridad_a_409
from services.docs import decrement_file_usage, increment_file_usage
from services.expediente import (
    CAMPOS_BASE,
    MSG_UNICO,
    cargar_expediente,
    datos_auditables,
    validar_catalogos,
    validar_comprobante_pago,
    verificar_unicos,
)
from services.expediente_involucrados import datos_cliente
from utils.log import insert_log

router = APIRouter()
logger = logging.getLogger(__name__)


class ExpedienteDatos(BaseModel):
    """Información base (§3). Todos los campos son obligatorios."""

    model_config = ConfigDict(str_strip_whitespace=True)

    radicado: str = Field(..., min_length=1, max_length=15)
    fecha_radicado: date
    # TODO(negocio): el plan solo da el ejemplo "CA 001-26"; no se valida formato.
    expediente: str = Field(..., min_length=1, max_length=9)
    numero_vital: str = Field(..., min_length=1, max_length=20)
    nombre_predio: str = Field(..., min_length=1, max_length=50)
    matricula_inmobiliaria: str = Field(..., min_length=1, max_length=20)
    codigo_catastral: str = Field(..., min_length=1, max_length=30)
    radicado_oficio_entrada: str = Field(..., min_length=1, max_length=20)
    fecha_oficio_entrada: date
    doc_comprobante_pago_id: int = Field(..., gt=0)
    vereda_id: int = Field(..., gt=0)
    tipo_fuente_id: int = Field(..., gt=0)
    nombre_fuente: str = Field(..., min_length=1, max_length=50)
    # TODO(negocio): el plan lista fuentes y usos entre los datos de nacimiento
    # pero no dice si puede nacer sin ninguno; se exige al menos uno.
    fuente_ids: list[int] = Field(..., min_length=1)
    usos: list[UsoAgua] = Field(..., min_length=1)

    @field_validator("fuente_ids", "usos")
    @classmethod
    def _sin_repetidos(cls, valores):
        return list(dict.fromkeys(valores))


class ExpedienteEditar(ExpedienteDatos):
    version: int = Field(..., ge=1, description="version leída en GET /expedientes/{id}")


def _campos(body: ExpedienteDatos) -> dict:
    return {campo: getattr(body, campo) for campo in CAMPOS_BASE}


def _relaciones(expediente_id: int, body: ExpedienteDatos) -> list:
    return [
        *(ExpedienteFuente(expediente_id=expediente_id, fuente_id=f) for f in body.fuente_ids),
        *(ExpedienteUso(expediente_id=expediente_id, uso=u) for u in body.usos),
    ]


async def _auditar(db: AsyncSession, **kwargs) -> None:
    resultado = await insert_log(db=db, resultado="OK", **kwargs)
    if not resultado["ok"]:
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")


@router.post("")
async def crear_expediente(
    request: Request,
    body: ExpedienteDatos,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)

    await validar_catalogos(db, body.vereda_id, body.tipo_fuente_id, body.fuente_ids)
    await verificar_unicos(db, body.radicado, body.expediente)
    await validar_comprobante_pago(body.doc_comprobante_pago_id)

    expediente = Expediente(**_campos(body))
    async with integridad_a_409(db, MSG_UNICO):
        db.add(expediente)
        await db.flush()
        db.add_all(_relaciones(expediente.id, body))
        await db.flush()

    expediente = await cargar_expediente(db, expediente.id)
    await _auditar(
        db,
        tipo_evento="INSERT_EXPEDIENTE",
        usuario_id=usuario.user_id,
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        detalle=f"Creación del expediente {expediente.expediente} (radicado {expediente.radicado})",
        datos_nuevos=datos_auditables(expediente),
        **datos_cliente(request),
    )

    # Uso del archivo antes del commit (como infraction): si no se puede
    # registrar, no se crea el expediente.
    inc = await increment_file_usage([body.doc_comprobante_pago_id])
    if not inc.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=502, detail="No se pudo registrar el uso del comprobante de pago")

    await db.commit()
    return JSONResponse(
        status_code=201,
        content={
            "ok": True,
            "message": "Expediente creado",
            "data": {"id": expediente.id, "expediente": expediente.expediente, "version": expediente.version},
        },
    )


@router.put("/{expediente_id}")
async def editar_expediente(
    request: Request,
    expediente_id: int,
    body: ExpedienteEditar,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)

    actual = await cargar_expediente(db, expediente_id)
    datos_anteriores = datos_auditables(actual)
    comprobante_anterior = actual.doc_comprobante_pago_id

    await validar_catalogos(db, body.vereda_id, body.tipo_fuente_id, body.fuente_ids)
    await verificar_unicos(db, body.radicado, body.expediente, excluir_id=expediente_id)
    cambia_comprobante = body.doc_comprobante_pago_id != comprobante_anterior
    if cambia_comprobante:
        await validar_comprobante_pago(body.doc_comprobante_pago_id)

    # Bloqueo optimista: el UPDATE ... WHERE version = :version bloquea la fila
    # hasta el commit; una edición concurrente con la misma version recibe 409.
    async with integridad_a_409(db, MSG_UNICO):
        nueva_version = await actualizar_versionado(
            db, Expediente, expediente_id, body.version, _campos(body)
        )

    # Fuentes y usos se reemplazan completos (misma transacción y misma version).
    await db.execute(delete(ExpedienteFuente).where(ExpedienteFuente.expediente_id == expediente_id))
    await db.execute(delete(ExpedienteUso).where(ExpedienteUso.expediente_id == expediente_id))
    db.add_all(_relaciones(expediente_id, body))
    await db.flush()

    nuevo = await cargar_expediente(db, expediente_id)
    await _auditar(
        db,
        tipo_evento="UPDATE_EXPEDIENTE_BASICO",
        usuario_id=usuario.user_id,
        expediente_id=expediente_id,
        expediente_radicado=nuevo.radicado,
        detalle=f"Edición de la información base del expediente {nuevo.expediente}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_auditables(nuevo),
        **datos_cliente(request),
    )

    if cambia_comprobante:
        inc = await increment_file_usage([body.doc_comprobante_pago_id])
        if not inc.get("ok"):
            await db.rollback()
            raise HTTPException(status_code=502, detail="No se pudo registrar el uso del comprobante de pago")
        # Si el commit falla tras este +1, get_db_managed lo compensa
        # (services/usos_archivos.py).

    await db.commit()

    # −1 del comprobante reemplazado DESPUÉS del commit (best-effort, como el
    # resto de la app): si la transacción fallara, el anterior sigue en uso.
    if cambia_comprobante and comprobante_anterior:
        try:
            dec = await decrement_file_usage([comprobante_anterior])
            if not dec.get("ok"):
                logger.warning(
                    f"No se pudo decrementar el uso del archivo {comprobante_anterior}: {dec.get('message')}"
                )
        except Exception as e:  # best-effort: el commit ya se hizo
            logger.warning(f"No se pudo decrementar el uso del archivo {comprobante_anterior}: {e}")
    return {
        "ok": True,
        "message": "Expediente actualizado",
        "data": {"id": expediente_id, "version": nueva_version},
    }
