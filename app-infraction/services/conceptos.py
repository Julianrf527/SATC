"""Acoger concepto de un expediente por instancia.

Hay dos etapas de acoger concepto sobre la misma tabla
(``etapa_acoger_concepto.instancia``): la de la visita técnica (etapa 3) y la
de la visita de seguimiento (etapa 5). Toda consulta "el concepto del
expediente" debe decir cuál; por defecto, el de la visita.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.etapa_acoger_concepto import (
    INSTANCIA_SEGUIMIENTO,
    INSTANCIA_VISITA,
    EtapaAcogerConcepto,
)

# Código de etapa (services.etapa_actual / cascada) de cada instancia.
CODIGO_ETAPA = {INSTANCIA_VISITA: "concepto", INSTANCIA_SEGUIMIENTO: "concepto_seguimiento"}
NOMBRE_ETAPA = {INSTANCIA_VISITA: "Etapa concepto", INSTANCIA_SEGUIMIENTO: "Etapa concepto seguimiento"}
# Informe técnico cuya aceptación habilita crear cada instancia.
INFORME_HABILITANTE = {INSTANCIA_VISITA: "VISITA", INSTANCIA_SEGUIMIENTO: "SEGUIMIENTO"}


async def concepto_de(
    db: AsyncSession, expediente_id: int, instancia: str = INSTANCIA_VISITA
) -> Optional[EtapaAcogerConcepto]:
    return await db.scalar(
        select(EtapaAcogerConcepto)
        .where(EtapaAcogerConcepto.expediente_id == expediente_id, EtapaAcogerConcepto.instancia == instancia)
        .order_by(EtapaAcogerConcepto.id)
        .limit(1)
    )
