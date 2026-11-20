"""Matriz de recursos afectados del informe técnico de VISITA.

Es obligatoria al aceptar un informe de VISITA: el técnico la diligencia al
cargar la versión firmada (``POST /revision-informes/{id}/version-final``) y
super gestión al hacer el cargue manual (``POST /informes/{id}/cargue-manual``).
Después solo se edita la matriz, nunca el informe (``PUT /informes/{id}/recursos``):

- el técnico asignado, mientras el expediente no tenga la etapa Acoger concepto;
- super gestión (``infraccion_super_gestion``), si el informe es MANUAL.

Una sola fuente para validar y guardar: las tres rutas usan este módulo.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.permission import Permission
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.informe_recurso_afectado import RECURSOS_MATRIZ, InformeRecursoAfectado
from db.models.informe_tecnico import InformeTecnico
import services.users as users_svc

MAGNITUDES = ("LEVE", "MODERADO", "GRAVE")
REVERSIBILIDADES = ("REVERSIBLE", "IRREVERSIBLE")

MSG_MATRIZ_OBLIGATORIA = "La matriz de recursos afectados es obligatoria en los informes de VISITA"
MSG_CONCEPTO_EXISTE = (
    "El expediente ya tiene la etapa Acoger concepto: la matriz ya no se puede editar"
)


class FilaRecurso(BaseModel):
    recurso: str
    magnitud: Optional[str] = None
    reversibilidad: Optional[str] = None
    no_existe: bool = False


def aplica_matriz(informe: InformeTecnico) -> bool:
    return (informe.tipo_informe or "").upper() == "VISITA"


def validar_matriz(filas: Optional[list[FilaRecurso]]) -> list[FilaRecurso]:
    """La matriz completa: una fila por cada recurso de ``RECURSOS_MATRIZ``,
    cada una con ``no_existe`` o con magnitud y reversibilidad. 400 si no."""
    if not filas:
        raise HTTPException(status_code=400, detail=MSG_MATRIZ_OBLIGATORIA)
    vistos: set[str] = set()
    for fila in filas:
        if fila.recurso not in RECURSOS_MATRIZ:
            raise HTTPException(status_code=400, detail=f"Recurso inválido: {fila.recurso}")
        if fila.recurso in vistos:
            raise HTTPException(status_code=400, detail=f"Recurso repetido: {fila.recurso}")
        vistos.add(fila.recurso)
        if fila.magnitud and fila.magnitud not in MAGNITUDES:
            raise HTTPException(status_code=400, detail=f"Magnitud inválida: {fila.magnitud}")
        if fila.reversibilidad and fila.reversibilidad not in REVERSIBILIDADES:
            raise HTTPException(status_code=400, detail=f"Reversibilidad inválida: {fila.reversibilidad}")
        if not fila.no_existe and not (fila.magnitud and fila.reversibilidad):
            raise HTTPException(
                status_code=400,
                detail=f"El recurso {fila.recurso} debe marcar 'no existe' o tener magnitud y reversibilidad",
            )
    faltan = [r for r in RECURSOS_MATRIZ if r not in vistos]
    if faltan:
        raise HTTPException(
            status_code=400,
            detail=f"Falta diligenciar en la matriz: {', '.join(faltan)}",
        )
    return filas


def parsear_matriz(texto: Optional[str]) -> Optional[list[FilaRecurso]]:
    """Matriz enviada como JSON en un campo de formulario multipart."""
    if texto is None or not texto.strip():
        return None
    try:
        datos = json.loads(texto)
        if not isinstance(datos, list):
            raise ValueError
        return [FilaRecurso(**fila) for fila in datos]
    except (ValueError, TypeError, ValidationError):
        raise HTTPException(status_code=400, detail="La matriz de recursos afectados no tiene un formato válido")


async def guardar_matriz(db: AsyncSession, informe_id: int, filas: list[FilaRecurso]) -> None:
    """Upsert por recurso (no hace commit)."""
    existentes = {
        f.recurso: f for f in (await db.execute(
            select(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe_id)
        )).scalars().all()
    }
    for fila in filas:
        magnitud = None if fila.no_existe else fila.magnitud
        reversibilidad = None if fila.no_existe else fila.reversibilidad
        actual = existentes.get(fila.recurso)
        if actual:
            actual.magnitud, actual.reversibilidad, actual.no_existe = magnitud, reversibilidad, fila.no_existe
        else:
            db.add(InformeRecursoAfectado(
                informe_id=informe_id,
                recurso=fila.recurso,
                magnitud=magnitud,
                reversibilidad=reversibilidad,
                no_existe=fila.no_existe,
            ))
    await db.flush()


async def matriz_para_auditoria(db: AsyncSession, informe_id: int) -> list[dict]:
    filas = (await db.execute(
        select(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe_id)
    )).scalars().all()
    por_recurso = {f.recurso: f for f in filas}
    return [
        {
            "recurso": r,
            "magnitud": por_recurso[r].magnitud,
            "reversibilidad": por_recurso[r].reversibilidad,
            "no_existe": por_recurso[r].no_existe,
        }
        for r in RECURSOS_MATRIZ if r in por_recurso
    ]


async def expedientes_con_concepto(db: AsyncSession, expediente_ids: list[int]) -> set[int]:
    if not expediente_ids:
        return set()
    return set((await db.execute(
        select(EtapaAcogerConcepto.expediente_id)
        .where(EtapaAcogerConcepto.expediente_id.in_(expediente_ids))
        .distinct()
    )).scalars().all())


def tecnico_puede_editar(informe: InformeTecnico, user_id: int, tiene_concepto: bool) -> bool:
    """Regla del técnico (sin consultas): VISITA aceptada, es el técnico
    asignado y el expediente aún no tiene Acoger concepto."""
    return (
        aplica_matriz(informe)
        and informe.fecha_aceptacion_informe is not None
        and informe.profesional_asignado_id == user_id
        and not tiene_concepto
    )


async def exigir_edicion_matriz(db: AsyncSession, informe: InformeTecnico, user_id: int) -> None:
    """403/400 si ``user_id`` no puede editar la matriz de ``informe``."""
    if not aplica_matriz(informe):
        raise HTTPException(status_code=400, detail="La matriz de recursos afectados solo aplica a informes de VISITA")
    if informe.fecha_aceptacion_informe is None:
        raise HTTPException(status_code=400, detail="El informe aún no ha sido aceptado")

    if informe.modo == "MANUAL" and await users_svc.verify_permission(user_id, Permission.MANUAL_UPLOAD):
        return
    if informe.profesional_asignado_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar esta matriz")
    if informe.expediente_id in await expedientes_con_concepto(db, [informe.expediente_id]):
        raise HTTPException(status_code=400, detail=MSG_CONCEPTO_EXISTE)
