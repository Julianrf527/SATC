"""Super gestión — cargue directo / histórico (plan §2.1, fase 12).

Solo ``recurso_super_gestion``. Carga cualquier etapa con su documento final y
sus datos **omitiendo** la revisión, la asignación ("Asignarme") y las
validaciones §6. Las restricciones de la BD (``unique``, ``not null``, FKs)
SÍ aplican: los campos obligatorios para crear una fila se exigen (400) y los
duplicados dan 409. Referencia: cargue manual de infraction (``reports.py``).

Semántica común (todos ``POST``, body JSON, ``version`` opcional):

- Si la fila no existe se crea; si existe se actualizan SOLO los campos enviados
  (no nulos). Si llega ``version`` y no coincide → 409.
- ``acto`` (``{numerado, fecha_numerado, file_id}``): crea y enlaza el acto
  administrativo si la fila aún no tiene (si ya tiene → 409: corregirlo con
  ``PUT /actos/administrativos/{id}``). Si había un proceso de revisión abierto
  se cierra (``cerrar_proceso_vigente``).
- En los conceptos, ``file_id`` es el concepto firmado (cierra su proceso).
- ``encargado_acto_id`` (opcional): abogado que figura como encargado (el
  front lo elige de ``GET /etapas/abogados``). Si no llega al crear la fila,
  la etapa queda SIN encargado (NULL, expedientes viejos): no se crea proceso
  de revisión y solo super gestión gestiona su acto. Al actualizar, si no
  llega se conserva el que había. La persona elegida SÍ se valida (aunque el
  resto del cargue directo omita §6): el abogado debe tener
  ``recurso_gestionar`` y el técnico (``tecnico_id`` / ``tecnico_encargado_id``)
  ``recurso_tecnico``; si no → 400. Solo se valida cuando el valor cambia.
- Todos los archivos deben ser PDF ya subidos a app-docs.
- Si la fila queda con encargado (abogado/técnico) y SIN documento final, su
  proceso de revisión queda alineado: se crea en ``pendiente_carga`` si no
  existe y, si existe, su encargado (``creador_id``) pasa al de la fila
  (``_sincronizar_proceso``). Así el encargado sigue el flujo normal.

Endpoints (prefijo ``/super-gestion``):

- ``POST /{expediente_id}/admite``
- ``POST /{expediente_id}/conceptos/{tipo}`` (etapa2|adicional|memorias|subsanacion|obras|obras_segundo)
- ``POST /{expediente_id}/requerimientos/{ambito}`` (etapa3|memorias|obras)
- ``POST /{expediente_id}/decision``
- ``POST /{expediente_id}/recurso``
- ``POST /{expediente_id}/memorias``
- ``POST /{expediente_id}/memorias/subsanacion``
- ``POST /{expediente_id}/obras``
- ``POST /{expediente_id}/obras/nuevo-informe``
- ``POST /terceros/{vinculo_id}/acto``
"""
import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import Usuario, requiere_permiso
from core.permission import Permission
from db.deps import get_db_managed
from db.models import (
    ActoAdmite,
    Decision,
    InformeUsuario,
    MemoriasCalculo,
    ReciboSatisfaccionObras,
    RecursoReposicion,
    Requerimiento,
    ResultadoRecurso,
    Subsanacion,
    TipoActo,
    TipoDecision,
    TipoVinculo,
)
from services.actos import crear_acto
from services.concurrencia import MSG_MODIFICADO, bloquear_expediente, integridad_a_409
from services.etapas import (
    AMBITOS_REQUERIMIENTO,
    PADRES_CONCEPTO,
    TIPOS_CONCEPTO,
    auditar,
    cargar_estado,
    crear_concepto,
    crear_proceso_etapa,
    enlazar_hijo,
    exigir_abogado,
    exigir_tecnico,
    liberar_archivos,
    ok,
    preparar_acto,
    registrar_archivos,
    subir_version,
    validar_pdf,
)
from services.expediente_involucrados import obtener_vinculo
from services.revision_documentos import Avisos, cerrar_proceso_vigente, proceso_vigente, reasignar_encargado

router = APIRouter()
logger = logging.getLogger(__name__)

DESCRIPCION_CIERRE = "Cargue directo por super gestión: documento final cargado sin revisión"


# ─────────────────────────────────────────────────────────────── esquemas

class ActoSuper(BaseModel):
    clase_acto: Literal["AUTO", "RES"]
    numerado: int | str
    fecha_numerado: date
    file_id: int = Field(..., gt=0)


class _Base(BaseModel):
    version: Optional[int] = Field(None, ge=1)


class _ConActo(_Base):
    encargado_acto_id: Optional[int] = Field(None, gt=0)
    acto: Optional[ActoSuper] = None


class AdmiteSuper(_ConActo):
    doc_oficio_alcaldia_id: Optional[int] = Field(None, gt=0)
    doc_fijacion_aviso_id: Optional[int] = Field(None, gt=0)
    doc_constancia_fijacion_aviso_id: Optional[int] = Field(None, gt=0)
    tecnico_id: Optional[int] = Field(None, gt=0, description="Técnico del concepto de la etapa 2")
    fecha_visita_tecnica: Optional[date] = None


class ConceptoSuper(_Base):
    tecnico_encargado_id: Optional[int] = Field(None, gt=0)
    fecha_visita_tecnica: Optional[date] = None
    fecha_aceptacion: Optional[date] = None
    caudal_fuente: Optional[float] = Field(None, ge=0)
    caudal_disponible: Optional[float] = Field(None, ge=0)
    caudal_otorgado: Optional[float] = Field(None, ge=0)
    num_usuarios: Optional[int] = Field(None, ge=0)
    cumple: Optional[bool] = None
    file_id: Optional[int] = Field(None, gt=0, description="Concepto firmado (PDF)")


class RequerimientoSuper(_ConActo):
    radicado_oficio_entrada: Optional[str] = Field(None, min_length=1, max_length=15)
    fecha_oficio_entrada: Optional[date] = None
    doc_oficio_entrada_id: Optional[int] = Field(None, gt=0)


class DecisionSuper(_ConActo):
    decision: Optional[TipoDecision] = None
    requiere_memorias: Optional[bool] = None
    fecha_ejecutoria: Optional[date] = None


class RadicadoSuper(_Base):
    radicado: Optional[str] = Field(None, min_length=1, max_length=15)
    fecha_radicado: Optional[date] = None
    file_id: Optional[int] = Field(None, gt=0)


class RadicadoActoSuper(RadicadoSuper):
    encargado_acto_id: Optional[int] = Field(None, gt=0)
    acto: Optional[ActoSuper] = None


class RecursoSuper(RadicadoActoSuper):
    resultado: Optional[ResultadoRecurso] = None


class TerceroActoSuper(BaseModel):
    acto: ActoSuper


# ─────────────────────────────────────────────────────────────── helpers

class Cargue:
    """Acumula cambios de archivos (+1 antes del commit, −1 después)."""

    def __init__(self, db: AsyncSession, usuario: Usuario):
        self.db = db
        self.usuario = usuario
        self.nuevos: list[int] = []
        self.anteriores: list[int] = []
        self.actos: list[int] = []

    async def campos(self, fila, valores: dict, docs: dict[str, str] | None = None) -> None:
        """Aplica los valores no nulos; ``docs`` = {campo: etiqueta} de archivos (PDF)."""
        docs = docs or {}
        for campo, v in valores.items():
            if v is None:
                continue
            if campo in docs:
                anterior = getattr(fila, campo, None)
                if anterior == v:
                    continue
                await validar_pdf(v, docs[campo])
                self.nuevos.append(v)
                if anterior:
                    self.anteriores.append(anterior)
            setattr(fila, campo, v)

    async def acto(self, fila, etapa_tipo: str, tipo_acto: TipoActo, datos: Optional[ActoSuper]) -> None:
        if datos is None:
            return
        if fila.acto_admin_id:
            raise HTTPException(
                status_code=409,
                detail="Esta etapa ya tiene acto administrativo; corrígelo con PUT /actos/administrativos/{id}",
            )
        await validar_pdf(datos.file_id, "Acto administrativo")
        await preparar_acto(self.db, tipo_acto, datos)  # type: ignore[arg-type]
        await self.db.flush()
        await cerrar_proceso_vigente(self.db, etapa_tipo, fila.id, usuario_id=self.usuario.user_id,
                                     descripcion=DESCRIPCION_CIERRE)
        acto = await crear_acto(self.db, tipo_acto=tipo_acto, clase_acto=datos.clase_acto, numerado=datos.numerado,
                                fecha_numerado=datos.fecha_numerado, documento_id=datos.file_id,
                                user_id=self.usuario.user_id)
        fila.acto_admin_id = acto.id
        self.actos.append(acto.id)

    async def terminar(self, exp, evento: str, detalle: str, datos: dict, request: Request) -> None:
        await self.db.flush()
        await registrar_archivos(self.nuevos)
        await auditar(self.db, self.usuario, exp, evento, detalle, datos, request)
        await self.db.commit()
        await liberar_archivos(self.anteriores)


def _version(fila, version: Optional[int]) -> None:
    if fila is not None and version is not None and getattr(fila, "version", None) != version:
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)


def _obligatorios(body, campos: dict[str, str], que: str) -> None:
    faltan = [nombre for c, nombre in campos.items() if getattr(body, c, None) is None]
    if faltan:
        raise HTTPException(status_code=400, detail=f"Para crear {que} faltan: {', '.join(faltan)}")


async def _guardar_nueva(db: AsyncSession, fila, mensaje: str = "Ya existe, otra persona lo creó al mismo tiempo. Recarga"):
    async with integridad_a_409(db, mensaje):
        db.add(fila)
        await db.flush()


def _resp(fila, cargue: Cargue, **extra) -> dict:
    return {"id": fila.id, "version": getattr(fila, "version", None),
            "acto_id": cargue.actos[0] if cargue.actos else getattr(fila, "acto_admin_id", None), **extra}


async def _inicio(request: Request, db: AsyncSession, expediente_id: int):
    usuario = await requiere_permiso(request, Permission.SUPER_MANAGE)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    return usuario, exp, e, Cargue(db, usuario)


async def _abogado_elegido(body, fila) -> None:
    """El abogado elegido (``encargado_acto_id``) tiene ``recurso_gestionar``."""
    await exigir_abogado(getattr(body, "encargado_acto_id", None), getattr(fila, "encargado_acto_id", None))


async def _sincronizar_proceso(
    db: AsyncSession, usuario: Usuario, exp, fila, *, etapa_tipo: str, tipo_documento: str,
    encargado_id: Optional[int], terminada: bool, avisos: Avisos,
) -> None:
    """Fila con encargado y sin documento final → su proceso vigente existe y
    tiene a ese encargado como ``creador_id`` (misma transacción del cargue)."""
    if terminada or not encargado_id:
        return
    await db.flush()
    proceso = await proceso_vigente(db, etapa_tipo, fila.id, para_actualizar=True)
    if proceso is None:
        async with integridad_a_409(db):
            await crear_proceso_etapa(
                db, expediente_id=exp.id, tipo_documento=tipo_documento, etapa_tipo=etapa_tipo,
                etapa_ref_id=fila.id, encargado_id=encargado_id, usuario=usuario, avisos=avisos,
            )
    else:
        await reasignar_encargado(db, proceso, encargado_id, usuario_id=usuario.user_id, avisos=avisos,
                                  descripcion="Encargado reasignado por super gestión")


async def _sincronizar_acto(db, usuario, exp, fila, etapa_tipo: str, tipo_documento: str, avisos: Avisos) -> None:
    await _sincronizar_proceso(db, usuario, exp, fila, etapa_tipo=etapa_tipo, tipo_documento=tipo_documento,
                               encargado_id=fila.encargado_acto_id, terminada=bool(fila.acto_admin_id),
                               avisos=avisos)


async def _sincronizar_concepto(db, usuario, exp, concepto, tipo: str, avisos: Avisos) -> None:
    await _sincronizar_proceso(db, usuario, exp, concepto, etapa_tipo="concepto_tecnico",
                               tipo_documento=TIPOS_CONCEPTO[tipo], encargado_id=concepto.tecnico_encargado_id,
                               terminada=bool(concepto.doc_concepto_tecnico_id), avisos=avisos)


RADICADO = {"radicado": "radicado", "fecha_radicado": "fecha de radicado", "file_id": "documento (file_id)"}


# ─────────────────────────────────────────────────────────────── etapas

@router.post("/{expediente_id}/admite")
async def super_admite(request: Request, expediente_id: int, body: AdmiteSuper,
                       db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    fila = e.admite
    _version(fila, body.version)
    await _abogado_elegido(body, fila)
    await exigir_tecnico(body.tecnico_id, e.concepto2.tecnico_encargado_id if e.concepto2 else None)
    if fila is None:
        fila = ActoAdmite(expediente_id=exp.id, encargado_acto_id=body.encargado_acto_id)
        await _guardar_nueva(db, fila)
    else:
        await c.campos(fila, {"encargado_acto_id": body.encargado_acto_id})
        subir_version(fila)
    await c.campos(fila, body.model_dump(include={
        "doc_oficio_alcaldia_id", "doc_fijacion_aviso_id", "doc_constancia_fijacion_aviso_id"}), {
        "doc_oficio_alcaldia_id": "Oficio a la Alcaldía", "doc_fijacion_aviso_id": "Fijación del aviso",
        "doc_constancia_fijacion_aviso_id": "Constancia de fijación de la Alcaldía",
    })
    await c.acto(fila, "acto_admite", TipoActo.AUTO_ADMITE, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, fila, "acto_admite", "AUTO_ADMITE", avisos)
    if e.concepto2 is None and body.tecnico_id:
        # Nace la etapa 2 con su proceso: el técnico sigue el flujo normal si su concepto no se carga aquí.
        await crear_concepto(db, tipo="etapa2", tecnico_id=body.tecnico_id, expediente_id=exp.id, usuario=usuario,
                             avisos=avisos, fecha_visita=body.fecha_visita_tecnica, validar_tecnico=False)
    elif e.concepto2 is not None and (body.tecnico_id or body.fecha_visita_tecnica):
        await c.campos(e.concepto2, {"tecnico_encargado_id": body.tecnico_id,
                                     "fecha_visita_tecnica": body.fecha_visita_tecnica})
        subir_version(e.concepto2)
        await _sincronizar_concepto(db, usuario, exp, e.concepto2, "etapa2", avisos)
    data = None
    await db.flush()
    data = _resp(fila, c)
    await c.terminar(exp, "SUPER_ADMITE", "Cargue directo del auto que admite", body.model_dump(), request)
    await avisos.enviar()
    return ok("Auto que admite cargado (super gestión)", data)


@router.post("/{expediente_id}/conceptos/{tipo}")
async def super_concepto(request: Request, expediente_id: int, tipo: str, body: ConceptoSuper,
                         db: AsyncSession = Depends(get_db_managed)):
    if tipo not in TIPOS_CONCEPTO:
        raise HTTPException(status_code=404, detail=f"Tipo de concepto desconocido: {tipo}")
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    avisos = Avisos()
    concepto = e.concepto(tipo)
    _version(concepto, body.version)
    await exigir_tecnico(body.tecnico_encargado_id, concepto.tecnico_encargado_id if concepto else None)
    if concepto is None:
        if body.tecnico_encargado_id is None:
            raise HTTPException(status_code=400, detail="Para crear el concepto falta: técnico encargado")
        padre, columna = None, None
        if tipo != "etapa2":
            atributo, columna = PADRES_CONCEPTO[tipo]
            padre = getattr(e, atributo)
            if padre is None:
                raise HTTPException(status_code=400, detail="Primero debe existir la etapa de la que depende el concepto")
        concepto, _ = await crear_concepto(
            db, tipo=tipo, tecnico_id=body.tecnico_encargado_id, expediente_id=exp.id, usuario=usuario,
            avisos=avisos, padre=padre, columna=columna, con_proceso=False, validar_tecnico=False,
        )
    else:
        subir_version(concepto)
    await c.campos(concepto, body.model_dump(exclude={"version", "file_id"}))
    if body.file_id is not None:
        await c.campos(concepto, {"doc_concepto_tecnico_id": body.file_id},
                       {"doc_concepto_tecnico_id": "Concepto técnico"})
        await cerrar_proceso_vigente(db, "concepto_tecnico", concepto.id, usuario_id=usuario.user_id,
                                     descripcion=DESCRIPCION_CIERRE)
    await _sincronizar_concepto(db, usuario, exp, concepto, tipo, avisos)
    await db.flush()
    data = _resp(concepto, c, tipo=tipo)
    data.pop("acto_id")
    await c.terminar(exp, "SUPER_CONCEPTO", f"Cargue directo del concepto ({tipo})", body.model_dump(), request)
    await avisos.enviar()
    return ok("Concepto técnico cargado (super gestión)", data)


@router.post("/{expediente_id}/requerimientos/{ambito}")
async def super_requerimiento(request: Request, expediente_id: int, ambito: str, body: RequerimientoSuper,
                              db: AsyncSession = Depends(get_db_managed)):
    if ambito not in AMBITOS_REQUERIMIENTO:
        raise HTTPException(status_code=404, detail=f"Requerimiento desconocido: {ambito}")
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    respuesta = body.model_dump(include={"radicado_oficio_entrada", "fecha_oficio_entrada", "doc_oficio_entrada_id"})
    if ambito != "etapa3" and any(v is not None for v in respuesta.values()):
        raise HTTPException(status_code=400, detail="La respuesta del usuario solo aplica al requerimiento de la etapa 3")
    req = e.requerimiento(ambito)
    _version(req, body.version)
    await _abogado_elegido(body, req)
    if req is None:
        encargado = body.encargado_acto_id  # None: sin encargado (cargue histórico)
        if ambito == "etapa3":
            req = Requerimiento(expediente_id=exp.id, encargado_acto_id=encargado)
            await _guardar_nueva(db, req)
        else:
            padre = getattr(e, ambito)
            if padre is None:
                raise HTTPException(status_code=400, detail="Primero debe existir la etapa de la que depende el requerimiento")
            req = Requerimiento(expediente_id=None, encargado_acto_id=encargado)
            async with integridad_a_409(db):
                db.add(req)
                await db.flush()
                await enlazar_hijo(db, padre, "requerimiento_id", req.id)
    else:
        await c.campos(req, {"encargado_acto_id": body.encargado_acto_id})
        subir_version(req)
    await c.campos(req, respuesta, {"doc_oficio_entrada_id": "Oficio de respuesta del usuario"})
    await c.acto(req, "requerimiento", TipoActo.REQUERIMIENTO, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, req, "requerimiento", "REQUERIMIENTO", avisos)
    await db.flush()
    data = _resp(req, c, ambito=ambito)
    await c.terminar(exp, "SUPER_REQUERIMIENTO", f"Cargue directo del requerimiento ({ambito})", body.model_dump(),
                     request)
    await avisos.enviar()
    return ok("Requerimiento cargado (super gestión)", data)


@router.post("/{expediente_id}/decision")
async def super_decision(request: Request, expediente_id: int, body: DecisionSuper,
                         db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    fila = e.decision
    _version(fila, body.version)
    await _abogado_elegido(body, fila)
    if fila is None:
        fila = Decision(expediente_id=exp.id, encargado_acto_id=body.encargado_acto_id)
        await _guardar_nueva(db, fila)
    else:
        await c.campos(fila, {"encargado_acto_id": body.encargado_acto_id})
        subir_version(fila)
    await c.campos(fila, body.model_dump(include={"decision", "requiere_memorias", "fecha_ejecutoria"}))
    await c.acto(fila, "decision", TipoActo.DECISION, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, fila, "decision", "DECISION", avisos)
    await db.flush()
    data = _resp(fila, c)
    await c.terminar(exp, "SUPER_DECISION", "Cargue directo de la decisión", body.model_dump(), request)
    await avisos.enviar()
    return ok("Decisión cargada (super gestión)", data)


@router.post("/{expediente_id}/recurso")
async def super_recurso(request: Request, expediente_id: int, body: RecursoSuper,
                        db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    if e.decision is None:
        raise HTTPException(status_code=400, detail="Primero debe existir la decisión")
    fila = e.recurso
    _version(fila, body.version)
    await _abogado_elegido(body, fila)
    nueva = fila is None
    if nueva:
        _obligatorios(body, RADICADO, "el recurso de reposición")
        fila = RecursoReposicion(decision_id=e.decision.id)
    else:
        subir_version(fila)
    await c.campos(fila, {"radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
                          "doc_recurso_id": body.file_id, "encargado_acto_id": body.encargado_acto_id,
                          "resultado": body.resultado}, {"doc_recurso_id": "Escrito del recurso"})
    if nueva:
        await _guardar_nueva(db, fila, "El expediente ya tiene recurso de reposición")
    await c.acto(fila, "recurso_reposicion", TipoActo.RECURSO, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, fila, "recurso_reposicion", "RECURSO", avisos)
    await db.flush()
    data = _resp(fila, c)
    await c.terminar(exp, "SUPER_RECURSO", "Cargue directo del recurso de reposición", body.model_dump(), request)
    await avisos.enviar()
    return ok("Recurso de reposición cargado (super gestión)", data)


@router.post("/{expediente_id}/memorias")
async def super_memorias(request: Request, expediente_id: int, body: RadicadoActoSuper,
                         db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    fila = e.memorias
    _version(fila, body.version)
    await _abogado_elegido(body, fila)
    nueva = fila is None
    if nueva:
        _obligatorios(body, RADICADO, "las memorias de cálculo")
        fila = MemoriasCalculo(expediente_id=exp.id)
    else:
        subir_version(fila)
    await c.campos(fila, {"radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
                          "doc_planos_id": body.file_id, "encargado_acto_id": body.encargado_acto_id},
                   {"doc_planos_id": "Planos"})
    if nueva:
        await _guardar_nueva(db, fila, "Ya existe, o el radicado ya está registrado")
    await c.acto(fila, "memorias_calculo", TipoActo.APRUEBA_MEMORIAS, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, fila, "memorias_calculo", "APRUEBA_MEMORIAS", avisos)
    await db.flush()
    data = _resp(fila, c)
    await c.terminar(exp, "SUPER_MEMORIAS", "Cargue directo de memorias de cálculo", body.model_dump(), request)
    await avisos.enviar()
    return ok("Memorias de cálculo cargadas (super gestión)", data)


@router.post("/{expediente_id}/memorias/subsanacion")
async def super_subsanacion(request: Request, expediente_id: int, body: RadicadoSuper,
                            db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    if e.memorias is None:
        raise HTTPException(status_code=400, detail="Primero deben existir las memorias de cálculo")
    fila = e.subsanacion
    nueva = fila is None
    if nueva:
        _obligatorios(body, RADICADO, "la subsanación")
        fila = Subsanacion()
    await c.campos(fila, {"radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
                          "doc_planos_ajustados_id": body.file_id}, {"doc_planos_ajustados_id": "Planos ajustados"})
    async with integridad_a_409(db, "El radicado ya está registrado"):
        if nueva:
            db.add(fila)
            await db.flush()
            await enlazar_hijo(db, e.memorias, "subsanacion_id", fila.id)
        await db.flush()
    data = {"id": fila.id, "version": None}
    await c.terminar(exp, "SUPER_SUBSANACION", "Cargue directo de la subsanación", body.model_dump(), request)
    return ok("Subsanación cargada (super gestión)", data)


async def _informe(db: AsyncSession, c: Cargue, informe: Optional[InformeUsuario], body: RadicadoSuper, que: str):
    nuevo = informe is None
    if nuevo:
        _obligatorios(body, RADICADO, que)
        informe = InformeUsuario()
    await c.campos(informe, {"radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
                             "doc_informe_usuario_id": body.file_id}, {"doc_informe_usuario_id": "Informe del usuario"})
    async with integridad_a_409(db, "El radicado ya está registrado"):
        if nuevo:
            db.add(informe)
        await db.flush()
    return informe, nuevo


@router.post("/{expediente_id}/obras")
async def super_obras(request: Request, expediente_id: int, body: RadicadoActoSuper,
                      db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    fila = e.obras
    _version(fila, body.version)
    await _abogado_elegido(body, fila)
    informe, _ = await _informe(db, c, e.informe_obras, body, "el recibo de obras (informe del usuario)")
    if fila is None:
        fila = ReciboSatisfaccionObras(expediente_id=exp.id, informe_usuario_id=informe.id,
                                       encargado_acto_id=body.encargado_acto_id)
        await _guardar_nueva(db, fila)
    else:
        await c.campos(fila, {"encargado_acto_id": body.encargado_acto_id})
        subir_version(fila)
    await c.acto(fila, "recibo_satisfaccion_obras", TipoActo.APRUEBA_OBRAS, body.acto)
    avisos = Avisos()
    await _sincronizar_acto(db, usuario, exp, fila, "recibo_satisfaccion_obras", "APRUEBA_OBRAS", avisos)
    await db.flush()
    data = _resp(fila, c, informe_usuario_id=informe.id)
    await c.terminar(exp, "SUPER_OBRAS", "Cargue directo del recibo de obras", body.model_dump(), request)
    await avisos.enviar()
    return ok("Recibo de obras cargado (super gestión)", data)


@router.post("/{expediente_id}/obras/nuevo-informe")
async def super_nuevo_informe(request: Request, expediente_id: int, body: RadicadoSuper,
                              db: AsyncSession = Depends(get_db_managed)):
    usuario, exp, e, c = await _inicio(request, db, expediente_id)
    if e.obras is None:
        raise HTTPException(status_code=400, detail="Primero debe existir el recibo de obras")
    informe, nuevo = await _informe(db, c, e.nuevo_informe_obras, body, "el nuevo informe del usuario")
    if nuevo:
        await enlazar_hijo(db, e.obras, "nuevo_informe_usuario_id", informe.id)
    data = {"id": informe.id, "version": None}
    await c.terminar(exp, "SUPER_NUEVO_INFORME", "Cargue directo del nuevo informe", body.model_dump(), request)
    return ok("Nuevo informe del usuario cargado (super gestión)", data)


@router.post("/terceros/{vinculo_id}/acto")
async def super_acto_tercero(request: Request, vinculo_id: int, body: TerceroActoSuper,
                             db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_permiso(request, Permission.SUPER_MANAGE)
    vinculo = await obtener_vinculo(db, vinculo_id)
    if vinculo.tipo_vinculo != TipoVinculo.TERCERO_INTERVINIENTE:
        raise HTTPException(status_code=400, detail="Este vínculo no es de un tercero interviniente")
    exp = await bloquear_expediente(db, vinculo.expediente_id)
    vinculo = await obtener_vinculo(db, vinculo_id)
    c = Cargue(db, usuario)
    await c.acto(vinculo, "expediente_involucrado", TipoActo.RECONOCE_TERCERO, body.acto)
    subir_version(vinculo)
    await db.flush()
    data = _resp(vinculo, c)
    await c.terminar(exp, "SUPER_ACTO_TERCERO", f"Acto que reconoce al tercero {vinculo.involucrado_id}",
                     body.model_dump(), request)
    return ok("Acto que reconoce al tercero cargado (super gestión)", data)
