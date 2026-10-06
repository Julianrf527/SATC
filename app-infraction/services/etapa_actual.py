"""Etapa actual ("última etapa") de un expediente de infracción.

Una sola definición para GET /todos, GET /encargado/{id}, POST /filtrar y
GET /completo/{id}: la etapa MÁS AVANZADA que existe según el orden del
proceso, no la de fecha más reciente (las fechas de cada tabla no son
comparables: unas son de creación del registro y otras de negocio, que pueden
ser futuras o NULL).

Orden del proceso (el mismo de ``etapas_existentes`` en /completo y de
``TAB_TO_ETAPA`` en el frontend):

    respuesta(1) < visita(2) < concepto(3) < seguimiento(4) < cierre(5)

El valor que se devuelve es el código estable (``respuesta``, ``visita``...);
el frontend lo traduce a su etiqueta en un solo lugar.
"""
from sqlalchemy import Integer, case, func, literal, select, union_all

from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.informe_tecnico import InformeTecnico

# código -> orden en el proceso
ORDEN_ETAPAS: dict[str, int] = {
    "respuesta": 1,
    "visita": 2,
    "concepto": 3,
    "seguimiento": 4,
    "cierre": 5,
}


def _parte(columna_expediente, codigo: str):
    return select(
        columna_expediente.label("expediente_id"),
        literal(ORDEN_ETAPAS[codigo], Integer).label("orden"),
    )


def subquery_etapa_actual():
    """Subquery ``(expediente_id, tipo)`` con la etapa más avanzada de cada
    expediente que tenga al menos una etapa. Se une con OUTER JOIN: los
    expedientes sin etapas quedan con ``tipo`` NULL."""
    etapas = union_all(
        _parte(EtapaRespuesta.expediente_id, "respuesta"),
        _parte(InformeTecnico.expediente_id, "visita").where(InformeTecnico.tipo_informe == "VISITA"),
        _parte(EtapaAcogerConcepto.expediente_id, "concepto"),
        _parte(InformeTecnico.expediente_id, "seguimiento").where(InformeTecnico.tipo_informe == "SEGUIMIENTO"),
        _parte(EtapaCierre.expediente_id, "cierre"),
    ).subquery()

    maxima = (
        select(etapas.c.expediente_id, func.max(etapas.c.orden).label("orden"))
        .group_by(etapas.c.expediente_id)
        .subquery()
    )
    tipo = case(
        {orden: codigo for codigo, orden in ORDEN_ETAPAS.items()},
        value=maxima.c.orden,
    )
    return select(maxima.c.expediente_id, tipo.label("tipo")).subquery()
