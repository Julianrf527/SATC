"""Alertas de vencimiento (services/alertas.py, routes/alertas.py)."""
from datetime import date, timedelta

import pytest

import routes.alertas as rutas_alertas
from services import alertas as svc
from services.revision_documentos import CADENAS
from tests.fixtures_etapas import *  # noqa: F401,F403
from tests.fixtures_etapas import REVISOR_POR_PERMISO


# ───────────────────────────────────────────────────── reglas puras (sin BD)

def test_dias_habiles_saltan_fines_de_semana_y_festivos():
    # Vie 2026-01-02 + 1 hábil = lun 2026-01-05 (sábado y domingo no cuentan).
    assert svc.sumar_habiles(date(2026, 1, 2), 1) == date(2026, 1, 5)
    # Lun 2026-01-12 es festivo (Reyes Magos trasladado): de vie 9 → mar 13.
    assert svc.sumar_habiles(date(2026, 1, 9), 1) == date(2026, 1, 13)
    assert svc.habiles_entre(date(2026, 1, 9), date(2026, 1, 13)) == 1
    assert svc.habiles_entre(date(2026, 1, 13), date(2026, 1, 9)) == 0


@pytest.mark.parametrize("transcurridos, estado", [(0, "verde"), (3, "amarillo"), (4, "rojo")])
def test_semaforo_por_porcentaje(transcurridos, estado):
    inicio = date(2026, 3, 2)  # lunes, semana sin festivos
    hoy = svc.sumar_habiles(inicio, transcurridos) if transcurridos else inicio
    s = svc.semaforo(inicio, 5, hoy)
    assert s["estado"] == estado and s["dias_transcurridos"] == transcurridos and s["dias_totales"] == 5
    assert s["dias_restantes"] == 5 - transcurridos and s["esta_vencido"] is False


def test_semaforo_vencido_al_pasar_el_ultimo_dia():
    inicio = date(2026, 3, 2)
    limite = svc.sumar_habiles(inicio, 3)
    assert svc.semaforo(inicio, 3, limite)["estado"] == "rojo"
    s = svc.semaforo(inicio, 3, limite + timedelta(days=1))
    assert s["estado"] == "vencido" and s["urgencia"] == "critico" and s["dias_restantes"] == 0


def test_advertencia_visita():
    numerado = date(2026, 3, 2)
    limite = svc.limite_visita(numerado)
    assert limite == date(2026, 3, 16)
    assert svc.advertencia_visita(numerado, limite) is None
    assert svc.advertencia_visita(numerado, numerado) is None
    fuera = svc.advertencia_visita(numerado, limite + timedelta(days=1))
    assert "fuera de los 10 días hábiles" in fuera and "16/03/2026" in fuera and "indicadores" in fuera
    antes = svc.advertencia_visita(numerado, numerado - timedelta(days=1))
    assert "anterior a la fecha de numerado" in antes and "02/03/2026" in antes
    assert svc.advertencia_visita(None, numerado) is None and svc.advertencia_visita(numerado, None) is None


# ─────────────────────────────────────────────────────────── por HTTP

def _hoy(monkeypatch, d: date) -> None:
    monkeypatch.setattr(rutas_alertas, "hoy_bogota", lambda: d)


async def _todas(client, user, alcance="todos", esperado=200, **params):
    r = await client.get("/alertas/todas", params={"alcance": alcance, **params}, headers=headers(user))
    assert r.status_code == esperado, r.text
    return r.json()


async def _aprobar_pasos(client, pid: int, encargado: int) -> None:
    """Aprueba toda la cadena de un proceso que ya tiene versión (sin subir otra)."""
    det = (await client.get(f"/revision-documentos/{pid}", headers=headers(encargado))).json()
    for paso in CADENAS[det["tipo_documento"]].pasos:
        for permiso in paso:
            r = await revisar(client, pid, "aprobado", REVISOR_POR_PERMISO[permiso])
            assert r.status_code == 200, r.text


async def _del_expediente(client, exp_id, user=ABOGADO) -> dict:
    r = await client.get(f"/alertas/{exp_id}", headers=headers(user))
    assert r.status_code == 200, r.text
    return r.json()["alertas"]


async def test_flujo_auto_admite_y_concepto(client, stubs, expediente):
    exp_id = expediente.id
    assert await _del_expediente(client, exp_id) == {}

    # Asignarse → 4 días para la primera versión, a cargo del abogado.
    pid = (await post(client, f"/etapas/{exp_id}/admite/asignarme")).json()["data"]["proceso_id"]
    alertas = await _del_expediente(client, exp_id)
    assert list(alertas) == ["admite_primera_version"]
    a = alertas["admite_primera_version"]
    assert a["encargado_id"] == ABOGADO and a["expediente_id"] == exp_id and a["es_responsable"] is True
    assert a["semaforo"]["dias_totales"] == 4 and a["semaforo"]["estado"] == "verde"

    # Primera versión → 3 días para la revisión completa.
    assert (await subir(client, pid)).status_code == 200
    assert list(await _del_expediente(client, exp_id)) == ["admite_revision"]

    # Aprobado para firma → 3 días para la versión final.
    await _aprobar_pasos(client, pid, ABOGADO)
    assert list(await _del_expediente(client, exp_id)) == ["admite_version_final"]

    # Versión final: nace el concepto (16 días desde la visita, a cargo del técnico).
    visita = svc.hoy_bogota()
    await post(client, f"/etapas/{exp_id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica=visita.isoformat(), fecha_numerado=visita.isoformat()))
    alertas = await _del_expediente(client, exp_id)
    assert list(alertas) == ["concepto_primera_version"]
    c = alertas["concepto_primera_version"]
    assert c["encargado_id"] == TECNICO and c["fecha_inicio"] == visita.isoformat()
    assert c["semaforo"]["dias_totales"] == 16

    # Primera versión del concepto → 5 días hasta la versión final.
    cpid = buscar_concepto(await etapas(client, exp_id), "etapa2")["proceso"]["proceso_id"]
    assert (await subir(client, cpid, user=TECNICO)).status_code == 200
    assert list(await _del_expediente(client, exp_id)) == ["concepto_version_final"]

    # Versión final del concepto → sin alertas del concepto.
    await _aprobar_pasos(client, cpid, TECNICO)
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": visita.isoformat(), **CAUDALES}
    await post(client, f"/etapas/{exp_id}/conceptos/etapa2/version-final", TECNICO, body)
    assert await _del_expediente(client, exp_id) == {}


async def test_aviso_publicado_cuenta_10_habiles_y_desaparece(client, stubs, monkeypatch, expediente):
    exp_id = expediente.id
    acto_id = (await admite_firmado(client, stubs, exp_id))["acto_id"]
    form = {"expediente_id": exp_id, "acto_admin_id": acto_id, "numerado": numerado(),
            "fecha_numerado": "2026-04-02", "fecha_envio": "2026-04-03",
            "documento_comunicacion_id": stubs.files.registrar()}
    r = await client.post("/actos/comunicaciones", data={k: str(v) for k, v in form.items()}, headers=headers(ABOGADO))
    assert r.status_code == 201, r.text

    registro = svc.hoy_bogota()  # la comunicación se registra hoy (fecha_creacion)
    _hoy(monkeypatch, svc.sumar_habiles(registro, 3))
    aviso = (await _del_expediente(client, exp_id))["admite_aviso_publicado"]
    assert "día 3 de 10" in aviso["accion_requerida"] and aviso["encargado_id"] == ABOGADO
    assert aviso["fecha_limite"] == svc.sumar_habiles(registro, 10).isoformat()

    _hoy(monkeypatch, svc.sumar_habiles(registro, 10))
    assert "día 10 de 10" in (await _del_expediente(client, exp_id))["admite_aviso_publicado"]["accion_requerida"]
    _hoy(monkeypatch, svc.sumar_habiles(registro, 10) + timedelta(days=1))
    assert "admite_aviso_publicado" not in await _del_expediente(client, exp_id)


async def test_vencida_y_devolucion_no_reinicia(client, monkeypatch, expediente):
    exp_id = expediente.id
    pid = (await post(client, f"/etapas/{exp_id}/admite/asignarme")).json()["data"]["proceso_id"]
    await subir(client, pid)
    await revisar(client, pid, "devuelto", JURIDICO)
    await subir(client, pid)
    a = (await _del_expediente(client, exp_id))["admite_revision"]
    assert a["fecha_inicio"] == svc.hoy_bogota().isoformat()  # sigue contando desde la versión 1
    _hoy(monkeypatch, svc.hoy_bogota() + timedelta(days=30))
    a = (await _del_expediente(client, exp_id))["admite_revision"]
    assert a["semaforo"]["estado"] == "vencido" and a["semaforo"]["esta_vencido"] is True


async def test_alcance_mios_todos_y_permisos(client, crear_expediente, rv_permisos):
    e1, e2 = await crear_expediente(), await crear_expediente()
    await post(client, f"/etapas/{e1.id}/admite/asignarme", ABOGADO)
    await post(client, f"/etapas/{e2.id}/admite/asignarme", ABOGADO2)

    todas = await _todas(client, ABOGADO, "todos", page=1)
    assert todas["total"] == 2 and todas["expedientes_con_alertas"] == 2
    assert todas["estadisticas_semaforo"]["verde"] == 2
    assert todas["tipos_disponibles"] == ["admite_primera_version"]
    propias = {a["radicado"]: a["es_responsable"] for a in todas["alertas"]}
    assert propias == {e1.radicado: True, e2.radicado: False}

    mias = await _todas(client, ABOGADO, "mios")
    assert [a["radicado"] for a in mias["alertas"]] == [e1.radicado]
    assert mias["alertas"][0]["expediente_id"] == e1.id and mias["estadisticas_semaforo"]["verde"] == 1

    filtrada = await _todas(client, ABOGADO, "todos", radicado=e2.radicado.lower())
    assert [a["radicado"] for a in filtrada["alertas"]] == [e2.radicado]

    # La pestaña es solo de recurso_gestionar; el bloque del expediente, de lectura.
    await _todas(client, LECTOR, esperado=403)
    await _todas(client, TECNICO, esperado=403)
    assert (await client.get(f"/alertas/{e1.id}", headers=headers(LECTOR))).status_code == 200
    assert (await client.get(f"/alertas/{e1.id}", headers=headers(EXTRANO))).status_code == 403
    assert (await client.get("/alertas/999999", headers=headers(ABOGADO))).status_code == 404


async def test_aviso_visita_en_version_final_no_bloquea(client, stubs, expediente):
    exp_id = expediente.id
    pid = (await post(client, f"/etapas/{exp_id}/admite/asignarme")).json()["data"]["proceso_id"]
    await aprobar_para_firma(client, pid, ABOGADO)
    r = await post(client, f"/etapas/{exp_id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_numerado="2026-03-02", fecha_visita_tecnica="2026-03-17"))
    advertencias = r.json()["data"]["advertencias"]
    assert len(advertencias) == 1 and "límite 16/03/2026" in advertencias[0]


async def test_aviso_visita_dentro_del_plazo(client, stubs, expediente):
    data = await acto_completo(client, stubs, f"/etapas/{expediente.id}/admite", tecnico_id=TECNICO,
                               fecha_numerado="2026-03-02", fecha_visita_tecnica="2026-03-16")
    assert data["advertencias"] == []


async def test_endpoint_aviso_visita(client, rv_permisos):
    r = await client.get("/alertas/aviso-visita", params={"fecha_numerado": "2026-03-02", "fecha_visita": "2026-03-01"},
                         headers=headers(ABOGADO))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["fecha_limite"] == "2026-03-16" and "anterior" in data["advertencia"]
    r = await client.get("/alertas/aviso-visita", params={"fecha_numerado": "2026-03-02"}, headers=headers(ABOGADO))
    assert r.json()["data"]["advertencia"] is None
    r = await client.get("/alertas/aviso-visita", params={"fecha_numerado": "2026-03-02"}, headers=headers(LECTOR))
    assert r.status_code == 403


async def test_aviso_visita_super_gestion_usa_lo_guardado(client, stubs, expediente):
    exp_id = expediente.id
    acto = {"clase_acto": "AUTO", "numerado": numerado(), "fecha_numerado": "2026-03-02",
            "file_id": stubs.files.registrar()}
    r = await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G,
                   {"acto": acto, "tecnico_id": TECNICO, "fecha_visita_tecnica": "2026-03-10"})
    assert r.json()["data"]["advertencias"] == []
    # Solo la visita en el cuerpo: el numerado se toma del acto guardado.
    r = await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {"fecha_visita_tecnica": "2026-04-30"})
    assert "límite 16/03/2026" in r.json()["data"]["advertencias"][0]
    # Sin fechas en el cuerpo, no avisa.
    r = await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G,
                   {"doc_oficio_alcaldia_id": stubs.files.registrar()})
    assert r.json()["data"]["advertencias"] == []
