"""
El rol de cargue manual (infraccion_cargue) no debe esperar a que venza el
término real del Auto de Requerimiento para poder crear la etapa de
Seguimiento — necesario para cargar expedientes históricos sin esperar días.
"""
from datetime import date, timedelta

import routes.stage_informe as stage_informe_mod
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from tests.conftest import gateway_headers


async def _true(*a, **k):
    return True


async def _false(*a, **k):
    return False


class TestSeguimientoCreableAutoRequerimiento:
    async def _make_concepto(self, db_session, expediente_id: int, dias_desde_hoy: int):
        concepto = EtapaAcogerConcepto(
            expediente_id=expediente_id,
            tipo_acogida_concepto="AUTO_REQUERIMIENTO",
            dias_termino=30,
            fecha_termino_calculada=date.today() + timedelta(days=dias_desde_hoy),
        )
        db_session.add(concepto)
        await db_session.flush()
        return concepto

    async def test_termino_no_vencido_bloquea_sin_permiso(self, client, make_expediente, db_session, monkeypatch):
        monkeypatch.setattr(stage_informe_mod, "verify_permission", _false)

        exp = await make_expediente(abogado_responsable_id=7)
        await self._make_concepto(db_session, exp.id, dias_desde_hoy=5)

        resp = await client.get(f"/stage/technical-report/{exp.id}/SEGUIMIENTO", headers=gateway_headers(7))
        assert resp.status_code == 404
        body = resp.json()
        assert body["creable"] is False
        assert "Faltan" in body["creable_msg"]

    async def test_termino_no_vencido_permite_con_permiso_cargue(self, client, make_expediente, db_session, monkeypatch):
        monkeypatch.setattr(stage_informe_mod, "verify_permission", _true)

        exp = await make_expediente(abogado_responsable_id=7)
        await self._make_concepto(db_session, exp.id, dias_desde_hoy=5)

        resp = await client.get(f"/stage/technical-report/{exp.id}/SEGUIMIENTO", headers=gateway_headers(7))
        assert resp.status_code == 404
        body = resp.json()
        assert body["creable"] is True

    async def test_termino_vencido_permite_sin_permiso(self, client, make_expediente, db_session, monkeypatch):
        monkeypatch.setattr(stage_informe_mod, "verify_permission", _false)

        exp = await make_expediente(abogado_responsable_id=7)
        await self._make_concepto(db_session, exp.id, dias_desde_hoy=-1)

        resp = await client.get(f"/stage/technical-report/{exp.id}/SEGUIMIENTO", headers=gateway_headers(7))
        assert resp.status_code == 404
        body = resp.json()
        assert body["creable"] is True

