"""Documentos anexos (opcionales) de cualquier fila de etapa (tabla ``documentos_anexos``).

La referencia es polimórfica ``(etapa_tipo, etapa_ref_id)`` con ``etapa_tipo`` =
nombre de la tabla de la fila, los MISMOS valores que usa la descarga del
expediente (``services/expediente_documentos.py``): ``acto_admite``,
``concepto_tecnico``, ``requerimiento``,
``decision``, ``recurso_reposicion``, ``memorias_calculo``, ``subsanacion``,
``recibo_satisfaccion_obras``, ``informe_usuario``. El tercero interviniente
(``expediente_involucrado``) no lleva anexos.

Plan §4-Etapa 2: los opcionales del concepto los carga el **abogado** (por eso
escritura = ``recurso_gestionar``, V1). Deben ser PDF (entran a la descarga).
La tabla no tiene columna ``version``: la edición cambia el nombre y, si llega
``documento_anexo_id``, reemplaza el PDF (+1 uso al nuevo antes del commit, −1
al anterior después, como el resto de la app).

Prefijo ``/documentos-anexos``:

- ``GET    /documentos-anexos?expediente_id=&etapa_tipo=&etapa_ref_id=``
- ``POST   /documentos-anexos``
- ``PUT    /documentos-anexos/{anexo_id}``  ``{expediente_id, nombre, documento_anexo_id?}``
- ``DELETE /documentos-anexos/{anexo_id}?expediente_id=``
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura
from db.deps import get_db_managed
from db.models import DocumentoAnexo
from services.concurrencia import bloquear_expediente
from services.etapas import (
    ETAPA_TIPOS_ANEXO,
    auditar,
    cargar_estado,
    liberar_archivos,
    ok,
    registrar_archivos,
    validar_pdf,
)
from services.expediente import cargar_expediente

router = APIRouter()
logger = logging.getLogger(__name__)


class AnexoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    expediente_id: int = Field(..., gt=0)
    etapa_tipo: str
    etapa_ref_id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=1, max_length=100)
    documento_anexo_id: int = Field(..., gt=0, description="PDF ya subido a app-docs")


class AnexoEditar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    expediente_id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=1, max_length=100)
    documento_anexo_id: Optional[int] = Field(
        None, gt=0, description="PDF ya subido a app-docs; solo si se reemplaza el archivo",
    )


def serializar_anexo(a: DocumentoAnexo) -> dict:
    return {
        "id": a.id, "etapa_tipo": a.etapa_tipo, "etapa_ref_id": a.etapa_ref_id, "nombre": a.nombre,
        "documento_anexo_id": a.documento_anexo_id,
        "fecha_subida": a.fecha_subida.isoformat() if a.fecha_subida else None,
    }


def _validar_tipo(etapa_tipo: str) -> None:
    if etapa_tipo not in ETAPA_TIPOS_ANEXO:
        raise HTTPException(status_code=400, detail=f"etapa_tipo inválido. Permitidos: {', '.join(ETAPA_TIPOS_ANEXO)}")


async def _estado_con_fila(db: AsyncSession, expediente_id: int, etapa_tipo: str, etapa_ref_id: int, bloquear: bool):
    _validar_tipo(etapa_tipo)
    exp = await (bloquear_expediente(db, expediente_id) if bloquear else cargar_expediente(db, expediente_id))
    e = await cargar_estado(db, exp)
    if not e.pertenece(etapa_tipo, etapa_ref_id):
        raise HTTPException(status_code=404, detail="La etapa no existe en este expediente")
    return exp


async def _anexo(db: AsyncSession, anexo_id: int, expediente_id: int):
    anexo = await db.get(DocumentoAnexo, anexo_id)
    if anexo is None:
        raise HTTPException(status_code=404, detail="Documento anexo no encontrado")
    exp = await _estado_con_fila(db, expediente_id, anexo.etapa_tipo, anexo.etapa_ref_id, bloquear=True)
    return anexo, exp


@router.get("")
async def listar_anexos(
    request: Request,
    expediente_id: int = Query(..., gt=0),
    etapa_tipo: str = Query(...),
    etapa_ref_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db_managed),
):
    await requiere_lectura(request)
    await _estado_con_fila(db, expediente_id, etapa_tipo, etapa_ref_id, bloquear=False)
    anexos = (await db.execute(
        select(DocumentoAnexo)
        .where(DocumentoAnexo.etapa_tipo == etapa_tipo, DocumentoAnexo.etapa_ref_id == etapa_ref_id)
        .order_by(DocumentoAnexo.fecha_subida, DocumentoAnexo.id)
    )).scalars().all()
    return {"ok": True, "data": [serializar_anexo(a) for a in anexos]}


@router.post("", status_code=201)
async def crear_anexo(request: Request, body: AnexoIn, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await _estado_con_fila(db, body.expediente_id, body.etapa_tipo, body.etapa_ref_id, bloquear=True)
    await validar_pdf(body.documento_anexo_id, "Documento anexo")
    anexo = DocumentoAnexo(
        etapa_tipo=body.etapa_tipo, etapa_ref_id=body.etapa_ref_id, nombre=body.nombre,
        documento_anexo_id=body.documento_anexo_id,
    )
    db.add(anexo)
    await db.flush()
    await registrar_archivos([body.documento_anexo_id])
    await auditar(db, usuario, exp, "CREAR_ANEXO", f"Anexo '{body.nombre}' en {body.etapa_tipo} {body.etapa_ref_id}",
                  body.model_dump(), request)
    data = serializar_anexo(anexo)
    await db.commit()
    return ok("Documento anexo cargado", data, status_code=201)


@router.put("/{anexo_id}")
async def editar_anexo(request: Request, anexo_id: int, body: AnexoEditar, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    anexo, exp = await _anexo(db, anexo_id, body.expediente_id)
    nuevo = body.documento_anexo_id
    anterior = None
    if nuevo and nuevo != anexo.documento_anexo_id:
        await validar_pdf(nuevo, "Documento anexo")
        anterior = anexo.documento_anexo_id
        anexo.documento_anexo_id = nuevo
    anexo.nombre = body.nombre
    await db.flush()
    if anterior is not None:
        await registrar_archivos([nuevo])
    detalle = f"Anexo {anexo_id} editado" + (" (PDF reemplazado)" if anterior is not None else "")
    await auditar(db, usuario, exp, "EDITAR_ANEXO", detalle,
                  {"nombre": body.nombre, "documento_anexo_id": anexo.documento_anexo_id,
                   "documento_anterior_id": anterior}, request)
    data = serializar_anexo(anexo)
    await db.commit()
    if anterior:
        await liberar_archivos([anterior])
    return ok("Documento anexo actualizado", data)


@router.delete("/{anexo_id}")
async def eliminar_anexo(
    request: Request, anexo_id: int, expediente_id: int = Query(..., gt=0), db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    anexo, exp = await _anexo(db, anexo_id, expediente_id)
    file_id = anexo.documento_anexo_id
    datos = serializar_anexo(anexo)
    await db.delete(anexo)
    await auditar(db, usuario, exp, "ELIMINAR_ANEXO", f"Anexo '{datos['nombre']}' eliminado", datos, request)
    await db.commit()
    await liberar_archivos([file_id])
    return ok("Documento anexo eliminado", {"id": anexo_id})
