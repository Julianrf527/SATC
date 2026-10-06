"""Borrado en cascada de las etapas de un expediente de infracción.

Un mismo código calcula QUÉ se borra y lo borra, para que la vista previa
(``GET /informes/{id}/cambiar-modo/impacto``) y el borrado real
(``PUT /informes/{id}/cambiar-modo``, cambio de tipo de concepto) coincidan:
cada función recibe una ``Cascada`` donde anota lo encontrado y, solo si
``cascada.ejecutar`` es verdadero, borra las filas.

Orden del proceso (``services.etapa_actual.ORDEN_ETAPAS``):

    respuesta < visita < concepto < seguimiento < cierre

Al cambiar el modo de un informe de VISITA se borran concepto, seguimiento y
cierre; al cambiar el de SEGUIMIENTO, solo el cierre.

Usos de archivo (``numero_usos`` en app-docs): cada registro que guarda un
archivo le sumó UN uso al crearse (``increment_file_usage`` con los ids del
registro, sin repetir). Se resta lo mismo: uno por archivo distinto de cada
registro borrado (acto, notificación, comunicación, oficio, solicitud, el
informe aceptado —uso propio—, cada versión y cada adjunto de revisión). Así
el informe aceptado y su versión, que comparten archivo, restan dos usos y no
uno ni tres. Las restas NO se aplican aquí: se acumulan en ``cascada.usos`` y
el llamador las aplica con ``aplicar_restas`` justo antes del commit.

Ninguna función hace commit.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Iterable, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_proceso import MODELOS_INFORME
from db.models.informe_recurso_afectado import InformeRecursoAfectado
from db.models.informe_tecnico import InformeTecnico
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from services.etapa_actual import ORDEN_ETAPAS

logger = logging.getLogger(__name__)

ETIQUETAS = {
    "respuesta": "Respuesta",
    "visita": "Visita técnica",
    "concepto": "Acoger concepto",
    "seguimiento": "Visita de seguimiento",
    "cierre": "Cierre",
}

# clave -> (singular, plural), en el orden en que se listan en el detalle.
ELEMENTOS: dict[str, tuple[str, str]] = {
    "actos": ("acto administrativo", "actos administrativos"),
    "notificaciones": ("notificación", "notificaciones"),
    "comunicaciones": ("comunicación", "comunicaciones"),
    "oficios": ("oficio remite", "oficios remite"),
    "solicitudes": ("solicitud de información", "solicitudes de información"),
    "informes": ("informe técnico", "informes técnicos"),
    "procesos": ("proceso de revisión", "procesos de revisión"),
    "versiones": ("versión", "versiones"),
    "revisiones": ("revisión", "revisiones"),
    "filas_matriz": ("fila de la matriz de recursos", "filas de la matriz de recursos"),
}


# ══════════════════════════════════════════════════════════════ resultado

@dataclass
class EtapaEliminada:
    codigo: str
    conteos: Counter = field(default_factory=Counter)
    ids: dict[str, list[int]] = field(default_factory=dict)

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS[self.codigo]

    def anotar(self, clave: str, id_: int) -> None:
        self.conteos[clave] += 1
        self.ids.setdefault(clave, []).append(id_)

    @property
    def detalle(self) -> str:
        partes = []
        for clave, (singular, plural) in ELEMENTOS.items():
            n = self.conteos.get(clave, 0)
            if n:
                partes.append(f"{n} {singular if n == 1 else plural}")
        return ", ".join(partes) if partes else "la etapa, sin documentos asociados"

    def a_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "etiqueta": self.etiqueta,
            "detalle": self.detalle,
            "conteos": {k: v for k, v in self.conteos.items() if v},
        }


@dataclass
class Cascada:
    """Lo que se borra (o se borraría, si ``ejecutar`` es falso)."""

    ejecutar: bool = True
    etapas: dict[str, EtapaEliminada] = field(default_factory=dict)
    usos: Counter = field(default_factory=Counter)  # file_id -> usos a restar

    def etapa(self, codigo: str) -> EtapaEliminada:
        if codigo not in self.etapas:
            self.etapas[codigo] = EtapaEliminada(codigo)
        return self.etapas[codigo]

    def restar(self, *file_ids: Optional[int]) -> None:
        """Un uso por archivo distinto del registro (igual que al incrementar)."""
        for fid in {f for f in file_ids if f}:
            self.usos[fid] += 1

    @property
    def ordenadas(self) -> list[EtapaEliminada]:
        return sorted(self.etapas.values(), key=lambda e: ORDEN_ETAPAS[e.codigo])

    def a_dict(self) -> dict:
        return {"etapas": [e.a_dict() for e in self.ordenadas]}

    def auditoria(self) -> dict:
        """Resumen para ``datos_anteriores`` del log."""
        return {
            "etapas_eliminadas": [
                {"codigo": e.codigo, "detalle": e.detalle, "ids": e.ids} for e in self.ordenadas
            ],
            "usos_restados": {str(k): v for k, v in sorted(self.usos.items())},
        }


# ═══════════════════════════════════════════════════════════════ piezas

async def _eliminar_acto(db: AsyncSession, acto_id: Optional[int], etapa: EtapaEliminada, cascada: Cascada) -> bool:
    """Acto + sus notificaciones (citación/notificación) y comunicaciones.
    El dueño (concepto/cierre) debe soltar ``acto_administrativo_id`` antes
    de que se haga flush del borrado (FK RESTRICT): ver ``_soltar_acto``."""
    if not acto_id:
        return False
    acto = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if acto is None:
        return False
    etapa.anotar("actos", acto.id)
    cascada.restar(acto.documento_acto_administrativo_id)

    notifs = (await db.execute(
        select(Notificacion).where(Notificacion.acto_administrativo_id == acto.id).order_by(Notificacion.id)
    )).scalars().all()
    for n in notifs:
        etapa.anotar("notificaciones", n.id)
        cascada.restar(n.documento_citacion_id, n.documento_notificacion_id)

    coms = (await db.execute(
        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id).order_by(Comunicacion.id)
    )).scalars().all()
    for c in coms:
        etapa.anotar("comunicaciones", c.id)
        cascada.restar(c.documento_comunicacion_id)

    if cascada.ejecutar:
        await db.delete(acto)  # cascade ORM: notificaciones y comunicación
    return True


async def _soltar_y_eliminar_acto(db: AsyncSession, dueno, etapa: EtapaEliminada, cascada: Cascada) -> None:
    acto_id = dueno.acto_administrativo_id
    if not acto_id:
        return
    if cascada.ejecutar:
        dueno.acto_administrativo_id = None
        await db.flush()
    await _eliminar_acto(db, acto_id, etapa, cascada)
    if cascada.ejecutar:
        await db.flush()


async def eliminar_datos_concepto(
    db: AsyncSession, concepto: EtapaAcogerConcepto, cascada: Cascada, *, incluir_solicitud: bool
) -> EtapaEliminada:
    """Acto (con notificaciones y comunicaciones) y oficio remite del
    concepto; la solicitud de información solo si ``incluir_solicitud`` (al
    cambiar el TIPO de concepto se conserva: es independiente del tipo)."""
    etapa = cascada.etapa("concepto")
    await _soltar_y_eliminar_acto(db, concepto, etapa, cascada)

    oficio = await db.scalar(select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == concepto.id))
    if oficio is not None:
        etapa.anotar("oficios", oficio.id)
        cascada.restar(oficio.archivo_remite_id)
        if cascada.ejecutar:
            await db.delete(oficio)
            await db.flush()

    if incluir_solicitud:
        solicitud = await db.scalar(
            select(SolicitudInformacion).where(SolicitudInformacion.etapa_acoger_concepto_id == concepto.id)
        )
        if solicitud is not None:
            etapa.anotar("solicitudes", solicitud.id)
            cascada.restar(solicitud.archivo_solicitud_id)
            if cascada.ejecutar:
                await db.delete(solicitud)
                await db.flush()
    return etapa


async def eliminar_concepto(db: AsyncSession, expediente_id: int, cascada: Cascada) -> None:
    """Etapa Acoger concepto completa: acto, notificaciones, comunicaciones,
    oficio remite, solicitud de información y la propia etapa."""
    conceptos = (await db.execute(
        select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
        .order_by(EtapaAcogerConcepto.id)
    )).scalars().all()
    for concepto in conceptos:
        await eliminar_datos_concepto(db, concepto, cascada, incluir_solicitud=True)
        cascada.etapa("concepto").ids.setdefault("etapa", []).append(concepto.id)
        if cascada.ejecutar:
            await db.delete(concepto)
            await db.flush()


async def eliminar_cierre(db: AsyncSession, expediente_id: int, cascada: Cascada) -> bool:
    """Etapa Cierre: su acto (con notificaciones y comunicaciones) y la etapa."""
    cierres = (await db.execute(
        select(EtapaCierre).where(EtapaCierre.expediente_id == expediente_id).order_by(EtapaCierre.id)
    )).scalars().all()
    for cierre in cierres:
        etapa = cascada.etapa("cierre")
        etapa.ids.setdefault("etapa", []).append(cierre.id)
        await _soltar_y_eliminar_acto(db, cierre, etapa, cascada)
        if cascada.ejecutar:
            await db.delete(cierre)
            await db.flush()
    return bool(cierres)


async def eliminar_seguimiento(db: AsyncSession, expediente_id: int, cascada: Cascada) -> None:
    """Informe(s) técnico(s) de SEGUIMIENTO con sus procesos de revisión
    (versiones, revisiones, auditoría, revisores), su matriz y su archivo.

    Bloqueos: primero los informes (por id) y después sus procesos — el
    mismo orden informe -> proceso de /informes y /revision-informes."""
    M = MODELOS_INFORME
    stmt = (
        select(InformeTecnico)
        .where(InformeTecnico.expediente_id == expediente_id, InformeTecnico.tipo_informe == "SEGUIMIENTO")
        .order_by(InformeTecnico.id)
    )
    if cascada.ejecutar:
        stmt = stmt.with_for_update()
    informes = (await db.execute(stmt)).scalars().all()
    if not informes:
        return
    etapa = cascada.etapa("seguimiento")
    informe_ids = [i.id for i in informes]

    pstmt = select(M.proceso).where(M.proceso.informe_id.in_(informe_ids)).order_by(M.proceso.id)
    if cascada.ejecutar:
        pstmt = pstmt.with_for_update()
    procesos = (await db.execute(pstmt)).scalars().all()
    proceso_ids = [p.id for p in procesos]

    for informe in informes:
        etapa.anotar("informes", informe.id)
        cascada.restar(informe.documento_informe_id)  # uso propio del informe aceptado

    for p in procesos:
        etapa.anotar("procesos", p.id)
    if proceso_ids:
        versiones = (await db.execute(
            select(M.version.id, M.version.file_id).where(M.version.proceso_id.in_(proceso_ids)).order_by(M.version.id)
        )).all()
        for vid, fid in versiones:
            etapa.anotar("versiones", vid)
            cascada.restar(fid)
        revisiones = (await db.execute(
            select(M.revision.id, M.revision.adjunto_file_id)
            .where(M.revision.proceso_id.in_(proceso_ids)).order_by(M.revision.id)
        )).all()
        for rid, adjunto in revisiones:
            etapa.anotar("revisiones", rid)
            cascada.restar(adjunto)

    filas = (await db.execute(
        select(InformeRecursoAfectado.id).where(InformeRecursoAfectado.informe_id.in_(informe_ids))
    )).scalars().all()
    for fid in filas:
        etapa.anotar("filas_matriz", fid)

    if not cascada.ejecutar:
        return
    if proceso_ids:
        for modelo in (M.auditoria, M.revision, M.version, M.asignacion):
            await db.execute(delete(modelo).where(modelo.proceso_id.in_(proceso_ids)))
        await db.execute(delete(M.proceso).where(M.proceso.id.in_(proceso_ids)))
    await db.execute(delete(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id.in_(informe_ids)))
    for informe in informes:
        await db.delete(informe)
    await db.flush()


# ═════════════════════════════════════════════════════════════ orquestador

ETAPAS_POSTERIORES = {
    "visita": ("concepto", "seguimiento", "cierre"),
    "seguimiento": ("cierre",),
}

_ELIMINADORES = {
    "concepto": eliminar_concepto,
    "seguimiento": eliminar_seguimiento,
    "cierre": eliminar_cierre,
}


def etapa_de_informe(tipo_informe: Optional[str]) -> Optional[str]:
    return {"VISITA": "visita", "SEGUIMIENTO": "seguimiento"}.get((tipo_informe or "").upper())


async def eliminar_etapas_posteriores(
    db: AsyncSession, expediente_id: int, desde: Optional[str], *, ejecutar: bool = True
) -> Cascada:
    """Borra (o, con ``ejecutar=False``, solo calcula) las etapas posteriores
    a ``desde`` ('visita' | 'seguimiento'). Se borran de la última a la
    primera (cierre, seguimiento, concepto) para no violar FKs."""
    cascada = Cascada(ejecutar=ejecutar)
    for codigo in reversed(ETAPAS_POSTERIORES.get(desde or "", ())):
        await _ELIMINADORES[codigo](db, expediente_id, cascada)
    return cascada


# ═══════════════════════════════════════════════════════ usos de archivo

Llamada = Callable[[list[int]], Awaitable[dict]]


def rondas(usos: Counter) -> list[list[int]]:
    """app-docs resta UN uso por id en cada llamada (``WHERE id IN``), aunque
    el id venga repetido: un archivo con 2 usos a restar va en 2 llamadas."""
    resultado = []
    n = 1
    while True:
        ids = sorted(fid for fid, veces in usos.items() if veces >= n)
        if not ids:
            return resultado
        resultado.append(ids)
        n += 1


class ErrorRestaUsos(Exception):
    pass


async def aplicar_restas(
    usos: Counter, decrementar: Llamada, incrementar: Optional[Llamada] = None, *, estricto: bool = True
) -> list[list[int]]:
    """Aplica las restas. Con ``estricto``, si una llamada falla se
    devuelven (best-effort, con ``incrementar``) las ya aplicadas y se lanza
    ``ErrorRestaUsos`` para que el llamador haga rollback."""
    aplicadas: list[list[int]] = []
    for ids in rondas(usos):
        res = await decrementar(ids)
        if estricto and not (isinstance(res, dict) and res.get("ok")):
            await compensar(aplicadas, incrementar)
            raise ErrorRestaUsos(f"No se pudo restar el uso de los archivos {ids}: {res}")
        aplicadas.append(ids)
    return aplicadas


async def compensar(aplicadas: Iterable[list[int]], incrementar: Optional[Llamada]) -> None:
    if incrementar is None:
        return
    for ids in aplicadas:
        try:
            await incrementar(ids)
        except Exception as e:  # best-effort
            logger.error(f"No se pudo devolver el uso de los archivos {ids}: {e}")
