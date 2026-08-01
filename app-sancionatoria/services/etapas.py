"""Registro único de los modelos de etapa y helpers compartidos entre los
routers de acto, involucrado y expediente."""
from typing import Type

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.expediente import Expediente
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_cesacion import EtapaCesacion
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso
from db.models.etapa_ejecucion_sancion import EtapaEjecucionSancion

# etapa_tipo (str) -> Model
ETAPA_MODELS: dict[str, Type] = {
    "etapa_indagacion": EtapaIndagacion,
    "etapa_medida_preventiva": EtapaMedidaPreventiva,
    "etapa_inicio_sancionatorio": EtapaInicioSancionatorio,
    "etapa_cesacion": EtapaCesacion,
    "etapa_formulacion_cargos": EtapaFormulacionCargos,
    "etapa_apertura_probatoria": EtapaAperturaProbatoria,
    "etapa_cierre_probatoria": EtapaCierreProbatoria,
    "etapa_decision_fondo": EtapaDecisionFondo,
    "etapa_probatoria_recurso": EtapaProbatoriaRecurso,
    "etapa_ejecucion_sancion": EtapaEjecucionSancion,
}

# Model -> nombre legible de la etapa (usado en listados, alertas y auditoría).
ETAPA_LABELS: dict[Type, str] = {
    EtapaIndagacion: "INDAGACION PRELIMINAR",
    EtapaMedidaPreventiva: "DETALLE MEDIDA PREVENTIVA",
    EtapaInicioSancionatorio: "INICIO PROCESO SANCIONATORIO",
    EtapaCesacion: "CESACION",
    EtapaFormulacionCargos: "FORMULACION DE CARGOS",
    EtapaAperturaProbatoria: "APERTURA ETAPA PROBATORIA",
    EtapaCierreProbatoria: "CIERRE ETAPA PROBATORIA",
    EtapaDecisionFondo: "DECISION DE FONDO",
    EtapaProbatoriaRecurso: "PROBATORIA DE RECURSO",
    EtapaEjecucionSancion: "EJECUCION DE LA SANCION",
}

# Model -> tipo_etapa_id legacy: el frontend todavía muestra/envía estos IDs
# numéricos en algunos listados.
ETAPA_LEGACY_ID: dict[Type, int] = {
    EtapaIndagacion: 2,
    EtapaMedidaPreventiva: 1,
    EtapaInicioSancionatorio: 9,
    EtapaCesacion: 10,
    EtapaFormulacionCargos: 4,
    EtapaAperturaProbatoria: 5,
    EtapaCierreProbatoria: 11,
    EtapaDecisionFondo: 6,
    EtapaProbatoriaRecurso: 12,
    EtapaEjecucionSancion: 7,
}


async def find_stage_by_id(db: AsyncSession, etapa_id: int):
    """Escanea las 10 tablas de etapa buscando este id.
    Retorna (etapa_tipo, Model, row) o (None, None, None)."""
    for etapa_tipo, Model in ETAPA_MODELS.items():
        row = await db.scalar(select(Model).where(Model.id == etapa_id))
        if row:
            return etapa_tipo, Model, row
    return None, None, None


async def get_expediente_con_permiso(db: AsyncSession, expediente_id: int, user_id: int):
    """Verifica que el expediente existe y el usuario es el encargado.

    Consulta combinada (id + encargado_id en el mismo WHERE): si no hay fila,
    se lanza el mismo 403 tanto si el expediente no existe como si existe pero
    no es del usuario. Evita que alguien sin acceso pueda distinguir, probando
    IDs, cuáles expedientes existen realmente (403 se mantiene, no 404, para
    no perder el toast de "sin permisos" que ya intercepta el frontend)."""
    row = (await db.execute(
        select(Expediente.id, Expediente.radicado, Expediente.encargado_id)
        .where(Expediente.id == expediente_id, Expediente.encargado_id == user_id)
    )).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    return row
