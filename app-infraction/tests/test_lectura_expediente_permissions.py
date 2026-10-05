"""
Permisos de las lecturas de un expediente fuera de file_query.py (auditoría
2026-10, hallazgos A19-A26). Antes solo validaban el token del gateway.

Regla (services.etapas.exigir_lectura_expediente, la misma de /completo):
  - infraccion_consultar ve cualquier expediente;
  - infraccion_gestionar solo los que tiene a cargo;
  - ajeno o inexistente -> 403 (no revela qué IDs existen).

Casos especiales:
  GET /etapas/migracion/medida/{radicado} -> además sancionatorio_gestionar
      ve cualquiera (lo consume la gestión de sancionatorio).
  GET /involucrados/{id}/expedientes      -> infraccion_consultar o
      involucrado_gestionar.
"""
import pytest

import routes.involved as involved_mod
import routes.stage_cierre as cierre_mod
import routes.stage_informe as informe_mod
import services.etapas as etapas_mod
from tests.conftest import gateway_headers

CONSULTAR = "infraccion_consultar"
GESTIONAR = "infraccion_gestionar"
SANC_GESTIONAR = "sancionatorio_gestionar"
INV_GESTIONAR = "involucrado_gestionar"

USUARIO = 5
OTRO = 9


@pytest.fixture
def permisos(monkeypatch):
    def _set(permitidos: set[str]):
        async def _verify(user_id, permission):
            return permission in permitidos

        for mod in (etapas_mod, cierre_mod, involved_mod, informe_mod):
            monkeypatch.setattr(mod, "verify_permission", _verify)

    return _set


# Lecturas por expediente_id. El código "autorizado" es el que devuelve el
# endpoint cuando pasa el permiso sobre un expediente sin datos (etapa aún no
# creada, sin documentos, sin involucrados).
LECTURAS = [
    ("/etapas/respuesta/{id}", 404),
    ("/etapas/concepto/{id}", 404),
    ("/etapas/cierre/{id}", 404),
    ("/etapas/informe-tecnico/{id}/VISITA", 404),
    ("/expedientes/descargar/{id}", 404),
    ("/involucrados/expediente/{id}", 200),
]


@pytest.mark.parametrize("ruta,autorizado", LECTURAS)
class TestLecturasPorExpediente:
    async def test_sin_permisos_403(self, client, permisos, make_expediente, ruta, autorizado):
        permisos(set())
        exp = await make_expediente(abogado_responsable_id=USUARIO)
        resp = await client.get(ruta.format(id=exp.id), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    async def test_sin_token_403(self, client, make_expediente, ruta, autorizado):
        exp = await make_expediente(abogado_responsable_id=USUARIO)
        resp = await client.get(ruta.format(id=exp.id))
        assert resp.status_code == 403

    async def test_consultar_ve_ajeno(self, client, permisos, make_expediente, ruta, autorizado):
        permisos({CONSULTAR})
        exp = await make_expediente(abogado_responsable_id=OTRO)
        resp = await client.get(ruta.format(id=exp.id), headers=gateway_headers(USUARIO))
        assert resp.status_code == autorizado

    async def test_consultar_inexistente_403(self, client, permisos, ruta, autorizado):
        permisos({CONSULTAR})
        resp = await client.get(ruta.format(id=987654), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    async def test_gestionar_ve_propio(self, client, permisos, make_expediente, ruta, autorizado):
        permisos({GESTIONAR})
        exp = await make_expediente(abogado_responsable_id=USUARIO)
        resp = await client.get(ruta.format(id=exp.id), headers=gateway_headers(USUARIO))
        assert resp.status_code == autorizado

    async def test_gestionar_ajeno_403(self, client, permisos, make_expediente, ruta, autorizado):
        permisos({GESTIONAR})
        exp = await make_expediente(abogado_responsable_id=OTRO)
        resp = await client.get(ruta.format(id=exp.id), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    async def test_encargado_sin_gestionar_403(self, client, permisos, make_expediente, ruta, autorizado):
        """Le quitaron el permiso pero sigue como encargado: ya no lee."""
        permisos({"infraccion_alertas"})
        exp = await make_expediente(abogado_responsable_id=USUARIO)
        resp = await client.get(ruta.format(id=exp.id), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403


class TestMigracionMedida:
    RUTA = "/etapas/migracion/medida/{rad}"

    async def test_sin_permisos_403(self, client, permisos, make_expediente):
        permisos(set())
        await make_expediente(abogado_responsable_id=USUARIO, radicado="RAD-MIG-1")
        resp = await client.get(self.RUTA.format(rad="RAD-MIG-1"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    async def test_sancionatorio_gestionar_ve_cualquiera(self, client, permisos, make_expediente):
        permisos({SANC_GESTIONAR})
        await make_expediente(abogado_responsable_id=OTRO, radicado="RAD-MIG-2")
        resp = await client.get(self.RUTA.format(rad="RAD-MIG-2"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 200
        assert resp.json()["ok"] is False  # sin medida, pero autorizado

    async def test_sancionatorio_gestionar_radicado_inexistente_200(self, client, permisos):
        permisos({SANC_GESTIONAR})
        resp = await client.get(self.RUTA.format(rad="NO-EXISTE"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 200
        assert resp.json()["ok"] is False

    async def test_consultar_ve_cualquiera(self, client, permisos, make_expediente):
        permisos({CONSULTAR})
        await make_expediente(abogado_responsable_id=OTRO, radicado="RAD-MIG-3")
        resp = await client.get(self.RUTA.format(rad="RAD-MIG-3"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 200

    async def test_gestionar_propio_ok(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        await make_expediente(abogado_responsable_id=USUARIO, radicado="RAD-MIG-4")
        resp = await client.get(self.RUTA.format(rad="RAD-MIG-4"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 200

    async def test_gestionar_ajeno_403(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        await make_expediente(abogado_responsable_id=OTRO, radicado="RAD-MIG-5")
        resp = await client.get(self.RUTA.format(rad="RAD-MIG-5"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    async def test_gestionar_inexistente_403(self, client, permisos):
        permisos({GESTIONAR})
        resp = await client.get(self.RUTA.format(rad="NO-EXISTE"), headers=gateway_headers(USUARIO))
        assert resp.status_code == 403


class TestExpedientesDeInvolucrado:
    RUTA = "/involucrados/42/expedientes"

    @pytest.mark.parametrize("permitidos", [set(), {GESTIONAR}, {SANC_GESTIONAR}])
    async def test_sin_permiso_403(self, client, permisos, make_expediente, link_involucrado, permitidos):
        permisos(permitidos)
        exp = await make_expediente(abogado_responsable_id=USUARIO)
        await link_involucrado(exp.id, involucrado_id=42)
        resp = await client.get(self.RUTA, headers=gateway_headers(USUARIO))
        assert resp.status_code == 403

    @pytest.mark.parametrize("permitidos", [{CONSULTAR}, {INV_GESTIONAR}])
    async def test_con_permiso_ok(self, client, permisos, make_expediente, link_involucrado, permitidos):
        permisos(permitidos)
        exp = await make_expediente(abogado_responsable_id=OTRO)
        await link_involucrado(exp.id, involucrado_id=42)
        resp = await client.get(self.RUTA, headers=gateway_headers(USUARIO))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1
