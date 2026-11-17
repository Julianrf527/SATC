"""
Permisos de los endpoints de lectura de expedientes (routes/file_query.py).

Antes solo validaban el token del gateway: cualquier usuario autenticado podía
listar todos los expedientes, abrir cualquiera o leer los datos personales de
los quejosos llamando la API directamente. Cada endpoint exige ahora el mismo
permiso que la pantalla del frontend que lo consume:

  GET  /expedientes                 -> infraccion_asignar (/infraction/assign_manage)
  GET  /expedientes/todos           -> infraccion_consultar (/infraction/consult)
  GET  /expedientes/encargado/{id}  -> ser el encargado + infraccion_gestionar
  GET  /expedientes/completo/{id}   -> infraccion_consultar, o infraccion_gestionar
                                       y ser el encargado
  GET  /expedientes/denunciantes    -> consultar, gestionar o auditoria_infracciones
  POST /expedientes/filtrar         -> "todos" con consultar; "propios" con gestionar
"""
import pytest

import routes.file_query as query_mod
from tests.conftest import gateway_headers

CONSULTAR = "infraccion_consultar"
GESTIONAR = "infraccion_gestionar"
ASIGNAR = "infraccion_asignar"
AUDITORIA = "auditoria_infracciones"


@pytest.fixture
def permisos(monkeypatch):
    """permisos({...}) fija los permisos que tiene el usuario de la petición."""

    def _set(permitidos: set[str]):
        async def _verify(user_id, permission):
            return permission in permitidos

        monkeypatch.setattr(query_mod, "verify_permission", _verify)

    return _set


@pytest.fixture
def sin_usuarios(monkeypatch):
    async def _vacio(permission_name):
        return {}

    monkeypatch.setattr(query_mod, "get_users_by_permission", _vacio)


class TestTodos:
    async def test_sin_permiso_403(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        await make_expediente(abogado_responsable_id=5)
        resp = await client.get("/expedientes/todos", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_sin_token_403(self, client):
        resp = await client.get("/expedientes/todos")
        assert resp.status_code == 403

    async def test_con_consultar_ve_todos(self, client, permisos, make_expediente):
        permisos({CONSULTAR})
        a = await make_expediente(abogado_responsable_id=5)
        b = await make_expediente(abogado_responsable_id=9)
        resp = await client.get("/expedientes/todos", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert {e["id"] for e in resp.json()["data"]} == {a.id, b.id}


class TestEncargado:
    async def test_propios_con_gestionar(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        propio = await make_expediente(abogado_responsable_id=5)
        await make_expediente(abogado_responsable_id=9)
        resp = await client.get("/expedientes/encargado/5", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert [e["id"] for e in resp.json()["data"]] == [propio.id]

    async def test_de_otro_usuario_403(self, client, permisos, make_expediente):
        permisos({GESTIONAR, CONSULTAR})
        await make_expediente(abogado_responsable_id=9)
        resp = await client.get("/expedientes/encargado/9", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_sin_gestionar_403(self, client, permisos, make_expediente):
        permisos(set())
        await make_expediente(abogado_responsable_id=5)
        resp = await client.get("/expedientes/encargado/5", headers=gateway_headers(5))
        assert resp.status_code == 403


class TestCompleto:
    async def test_consultar_abre_cualquiera(self, client, permisos, make_expediente):
        permisos({CONSULTAR})
        exp = await make_expediente(abogado_responsable_id=9)
        resp = await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == exp.id

    async def test_consultar_inexistente_404(self, client, permisos):
        permisos({CONSULTAR})
        resp = await client.get("/expedientes/completo/9999", headers=gateway_headers(5))
        assert resp.status_code == 404

    async def test_gestionar_abre_el_suyo(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        exp = await make_expediente(abogado_responsable_id=5)
        resp = await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code == 200

    async def test_gestionar_ajeno_403(self, client, permisos, make_expediente):
        permisos({GESTIONAR})
        exp = await make_expediente(abogado_responsable_id=9)
        resp = await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_gestionar_inexistente_403(self, client, permisos):
        permisos({GESTIONAR})
        resp = await client.get("/expedientes/completo/9999", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_encargado_sin_permiso_403(self, client, permisos, make_expediente):
        permisos(set())
        exp = await make_expediente(abogado_responsable_id=5)
        resp = await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code == 403


class TestDenunciantes:
    @pytest.mark.parametrize("permiso", [CONSULTAR, GESTIONAR, AUDITORIA])
    async def test_con_permiso_200(self, client, permisos, permiso):
        permisos({permiso})
        resp = await client.get("/expedientes/denunciantes", headers=gateway_headers(5))
        assert resp.status_code == 200

    async def test_sin_permiso_403(self, client, permisos):
        permisos({ASIGNAR})
        resp = await client.get("/expedientes/denunciantes", headers=gateway_headers(5))
        assert resp.status_code == 403


class TestListadoAsignacion:
    async def test_sin_asignar_403(self, client, permisos, sin_usuarios):
        permisos({CONSULTAR, GESTIONAR})
        resp = await client.get("/expedientes", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_con_asignar_200(self, client, permisos, sin_usuarios, make_expediente):
        permisos({ASIGNAR})
        exp = await make_expediente(abogado_responsable_id=9)
        resp = await client.get("/expedientes", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert [e["id"] for e in resp.json()["data"]] == [exp.id]


class TestFiltrar:
    async def test_sin_permisos_403(self, client, permisos):
        permisos(set())
        resp = await client.post("/expedientes/filtrar", json={}, headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_todos_solo_con_consultar_200(self, client, permisos, make_expediente):
        permisos({CONSULTAR})
        await make_expediente(abogado_responsable_id=9)
        resp = await client.post(
            "/expedientes/filtrar", json={"alcance": "todos"}, headers=gateway_headers(5)
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    async def test_propios_solo_con_consultar_403(self, client, permisos):
        permisos({CONSULTAR})
        resp = await client.post("/expedientes/filtrar", json={}, headers=gateway_headers(5))
        assert resp.status_code == 403


class TestCatalogos:
    """Recursos y tipos de afectación son catálogos no sensibles: basta la sesión."""

    @pytest.mark.parametrize("ruta", ["/expedientes/recursos-afectados", "/expedientes/tipos-afectacion"])
    async def test_sin_permisos_200(self, client, permisos, ruta):
        permisos(set())
        resp = await client.get(ruta, headers=gateway_headers(5))
        assert resp.status_code == 200
