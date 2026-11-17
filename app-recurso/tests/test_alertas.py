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


def test_semaforo_en_dias_calendario():
    inicio = date(2026, 3, 6)  # viernes: los fines de semana y festivos sí cuentan
    assert svc.limite_plazo(inicio, 30, calendario=True) == date(2026, 4, 5)
    assert svc.dias_entre(inicio, date(2026, 3, 9), calendario=True) == 3
    for dias, estado in [(0, "verde"), (15, "amarillo"), (24, "rojo"), (30, "rojo"), (31, "vencido")]:
        s = svc.semaforo(inicio, 30, inicio + timedelta(days=dias), calendario=True)
        assert s["estado"] == estado and s["dias_transcurridos"] == dias, (dias, s)
        assert s["dias_restantes"] == max(30 - dias, 0)


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
    # proceso_id: el proceso donde se hace la tarea (para abrirlo desde Mis actuaciones).
    assert a["proceso_id"] == pid
    assert a["semaforo"]["dias_totales"] == 4 and a["semaforo"]["estado"] == "verde"

    # Primera versión → 3 días para la revisión completa.
    assert (await subir(client, pid)).status_code == 200
    assert (await _del_expediente(client, exp_id))["admite_revision"]["proceso_id"] == pid

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
    assert c["proceso_id"] == cpid
    assert (await subir(client, cpid, user=TECNICO)).status_code == 200
    alertas = await _del_expediente(client, exp_id)
    assert list(alertas) == ["concepto_version_final"] and alertas["concepto_version_final"]["proceso_id"] == cpid

    # Versión final del concepto → sin alertas del concepto.
    await _aprobar_pasos(client, cpid, TECNICO)
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": visita.isoformat(), **CAUDALES,
            "accion": "REQUIERE"}
    await post(client, f"/etapas/{exp_id}/conceptos/etapa2/version-final", TECNICO, body)
    # (el concepto dice REQUIERE: arranca el plazo del acto del requerimiento)
    assert list(await _del_expediente(client, exp_id)) == ["requerimiento_primera_version"]


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

    # La pestaña es de recurso_gestionar o recurso_consultar (ven todas; "mías" según el encargado).
    lector = await _todas(client, LECTOR, "todos")
    assert lector["total"] == 2 and {a["es_responsable"] for a in lector["alertas"]} == {False}
    assert (await _todas(client, LECTOR, "mios"))["total"] == 0
    await _todas(client, TECNICO, esperado=403)  # solo recurso_tecnico, sin gestionar ni consultar
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


# ─────────────────────────────────────── etapas 3 y 4 y recurso de reposición

async def _claves(client, exp_id, prefijos=None) -> list[str]:
    alertas = await _del_expediente(client, exp_id)
    return [k for k in alertas if prefijos is None or k.startswith(prefijos)]


async def test_flujo_requerimiento_concepto_adicional_y_decision(client, stubs, expediente):
    exp_id = expediente.id
    hoy = svc.hoy_bogota().isoformat()
    await admite_firmado(client, stubs, exp_id)
    await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES, accion="REQUIERE")

    # 6 días desde la versión final del concepto, aunque nadie se haya asignado (sin encargado).
    a = (await _del_expediente(client, exp_id))["requerimiento_primera_version"]
    assert a["encargado_id"] is None and a["es_responsable"] is False
    assert a["fecha_inicio"] == hoy and a["semaforo"]["dias_totales"] == 6 and a["etapa"] == "Requerimiento"
    assert "concepto técnico de la etapa 2" in a["plazo_legal"]

    pid = (await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/asignarme")).json()["data"]["proceso_id"]
    a = (await _del_expediente(client, exp_id))["requerimiento_primera_version"]
    assert a["encargado_id"] == ABOGADO and a["fecha_inicio"] == hoy
    assert (await subir(client, pid)).status_code == 200
    a = (await _del_expediente(client, exp_id))["requerimiento_revision"]
    assert list(await _del_expediente(client, exp_id)) == ["requerimiento_revision"]
    assert a["semaforo"]["dias_totales"] == 4
    await _aprobar_pasos(client, pid, ABOGADO)
    a = (await _del_expediente(client, exp_id))["requerimiento_version_final"]
    assert a["semaforo"]["dias_totales"] == 2
    await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/version-final", json=acto_body(stubs))
    # Acto cargado: el técnico adicional espera la respuesta del usuario.
    assert await _del_expediente(client, exp_id) == {}

    req = (await etapas(client, exp_id))["requerimiento"]
    await put(client, f"/etapas/{exp_id}/requerimientos/etapa3/respuesta", json={
        "version": req["version"], "radicado_oficio_entrada": "2026ER1", "fecha_oficio_entrada": "2026-06-01",
        "doc_oficio_entrada_id": stubs.files.registrar()})
    a = (await _del_expediente(client, exp_id))["concepto_adicional_tecnico"]
    assert list(await _del_expediente(client, exp_id)) == ["concepto_adicional_tecnico"]
    # Cuenta desde que se registró la respuesta (hoy), no desde la fecha del oficio.
    assert a["fecha_inicio"] == hoy and a["encargado_id"] == ABOGADO and a["semaforo"]["dias_totales"] == 5
    assert a["etapa"] == "Concepto técnico adicional"

    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": TECNICO})
    a = (await _del_expediente(client, exp_id))["concepto_adicional_primera_version"]
    assert a["encargado_id"] == TECNICO and a["fecha_inicio"] == hoy and a["semaforo"]["dias_totales"] == 5
    cpid = buscar_concepto(await etapas(client, exp_id), "adicional")["proceso"]["proceso_id"]
    assert (await subir(client, cpid, user=TECNICO)).status_code == 200
    a = (await _del_expediente(client, exp_id))["concepto_adicional_revision"]
    assert a["semaforo"]["dias_totales"] == 2
    await _aprobar_pasos(client, cpid, TECNICO)
    a = (await _del_expediente(client, exp_id))["concepto_adicional_version_final"]
    assert a["semaforo"]["dias_totales"] == 1 and a["plazo_legal"].startswith("1 día hábil ")
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/version-final", TECNICO,
               {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20"})

    # Concepto adicional cargado → 6 días para la primera versión de la decisión.
    a = (await _del_expediente(client, exp_id))["decision_primera_version"]
    assert list(await _del_expediente(client, exp_id)) == ["decision_primera_version"]
    assert a["encargado_id"] is None and a["fecha_inicio"] == hoy and a["semaforo"]["dias_totales"] == 6
    assert "concepto técnico adicional" in a["plazo_legal"] and a["etapa"] == "Decisión"

    await con_constancia(client, stubs, exp_id)
    dpid = (await post(client, f"/etapas/{exp_id}/decision/asignarme")).json()["data"]["proceso_id"]
    assert (await _del_expediente(client, exp_id))["decision_primera_version"]["encargado_id"] == ABOGADO
    assert (await subir(client, dpid)).status_code == 200
    assert (await _del_expediente(client, exp_id))["decision_revision"]["semaforo"]["dias_totales"] == 4
    await _aprobar_pasos(client, dpid, ABOGADO)
    assert (await _del_expediente(client, exp_id))["decision_version_final"]["semaforo"]["dias_totales"] == 2
    await post(client, f"/etapas/{exp_id}/decision/version-final", json=acto_body(stubs, decision="NEGADA"))
    assert await _del_expediente(client, exp_id) == {}


async def test_decision_cuenta_desde_el_concepto_de_la_etapa_2_si_decide(client, stubs, expediente):
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES, accion="DECIDE")
    alertas = await _del_expediente(client, exp_id)
    assert list(alertas) == ["decision_primera_version"]
    a = alertas["decision_primera_version"]
    assert a["fecha_inicio"] == svc.hoy_bogota().isoformat() and "etapa 2" in a["plazo_legal"]


async def test_vencimiento_en_dias_habiles_del_requerimiento(client, stubs, monkeypatch, expediente):
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES)
    inicio = svc.hoy_bogota()
    _hoy(monkeypatch, svc.sumar_habiles(inicio, 6))
    assert (await _del_expediente(client, exp_id))["requerimiento_primera_version"]["semaforo"]["estado"] == "rojo"
    _hoy(monkeypatch, svc.sumar_habiles(inicio, 6) + timedelta(days=1))
    a = (await _del_expediente(client, exp_id))["requerimiento_primera_version"]
    assert a["semaforo"]["estado"] == "vencido" and a["fecha_limite"] == svc.sumar_habiles(inicio, 6).isoformat()


async def _recurso(client, stubs, con_decision, catalogo, requiere: bool) -> int:
    exp_id, data = await con_decision("NEGADA", None)
    await notificar(client, stubs, catalogo, exp_id, data["acto_id"])
    await post(client, f"/etapas/{exp_id}/recurso", json={
        "radicado": "2026ER77", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar(),
        "requiere_pruebas": requiere,
    }, esperado=201)
    return exp_id


async def test_recurso_sin_pruebas_60_dias_calendario(client, rv_permisos, con_decision, catalogo, monkeypatch):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, requiere=False)
    hoy = svc.hoy_bogota()
    assert await _claves(client, exp_id, "recurso_") == ["recurso_acto"]
    a = (await _del_expediente(client, exp_id))["recurso_acto"]
    # La fecha del escrito (2026-06-10) no importa: cuenta desde que se registró el recurso.
    assert a["fecha_inicio"] == hoy.isoformat() and a["fecha_limite"] == (hoy + timedelta(days=60)).isoformat()
    assert a["semaforo"]["dias_totales"] == 60 and "calendario" in a["plazo_legal"] and a["encargado_id"] is None
    assert a["proceso_id"] is None  # nadie ha tomado el acto: aún no hay proceso
    assert a["etapa"] == "Recurso de reposición"

    for dias, estado in [(30, "amarillo"), (48, "rojo"), (61, "vencido")]:
        _hoy(monkeypatch, hoy + timedelta(days=dias))
        assert (await _del_expediente(client, exp_id))["recurso_acto"]["semaforo"]["estado"] == estado

    _hoy(monkeypatch, hoy)
    await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso", ABOGADO2, resultado="CONFIRMA")
    assert await _claves(client, exp_id, "recurso_") == []


async def test_recurso_con_pruebas_30_y_30_y_cambio_de_respuesta(client, rv_permisos, con_decision, catalogo):
    from tests.test_practica_pruebas import _auto_pruebas, _cambiar

    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, requiere=False)
    hoy = svc.hoy_bogota().isoformat()
    # No → Sí: pasa a la regla con pruebas, contando desde que se registró el recurso.
    await _cambiar(client, exp_id, True)
    assert await _claves(client, exp_id, "recurso_") == ["recurso_concepto_pruebas"]
    a = (await _del_expediente(client, exp_id))["recurso_concepto_pruebas"]
    assert a["fecha_inicio"] == hoy and a["semaforo"]["dias_totales"] == 30 and a["encargado_id"] is None
    assert a["proceso_id"] is None

    # Asignado el auto de pruebas: a cargo del abogado; cargado el auto: del técnico del concepto.
    await post(client, f"/etapas/{exp_id}/recurso/pruebas/asignarme", ABOGADO2)
    assert (await _del_expediente(client, exp_id))["recurso_concepto_pruebas"]["encargado_id"] == ABOGADO2
    await _cambiar(client, exp_id, False, esperado=409)  # (práctica iniciada: pide confirmar)
    arbol = await etapas(client, exp_id)
    pid = arbol["decision"]["recurso"]["pruebas"]["proceso"]["proceso_id"]
    # Sin concepto de pruebas aún, la tarea vive en el proceso del auto.
    assert (await _del_expediente(client, exp_id))["recurso_concepto_pruebas"]["proceso_id"] == pid
    await aprobar_para_firma(client, pid, ABOGADO2)
    await post(client, f"/etapas/{exp_id}/recurso/pruebas/version-final", ABOGADO2,
               acto_body(stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-06-20"))
    a = (await _del_expediente(client, exp_id))["recurso_concepto_pruebas"]
    assert a["encargado_id"] == TECNICO and a["fecha_inicio"] == hoy
    concepto = buscar_concepto(await etapas(client, exp_id), "pruebas")
    # Ya existe el concepto de pruebas: la tarea pasa a su proceso.
    assert concepto["proceso"] and a["proceso_id"] == concepto["proceso"]["proceso_id"] != pid

    # Concepto de pruebas cargado → 30 días desde su versión final para el acto que resuelve.
    await concepto_firmado(client, stubs, exp_id, "pruebas")
    assert await _claves(client, exp_id, "recurso_") == ["recurso_acto_tras_pruebas"]
    a = (await _del_expediente(client, exp_id))["recurso_acto_tras_pruebas"]
    assert a["fecha_inicio"] == hoy and a["semaforo"]["dias_totales"] == 30 and "concepto técnico de pruebas" in a["plazo_legal"]

    await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso", ABOGADO2, resultado="CONFIRMA")
    assert await _claves(client, exp_id, "recurso_") == []


async def test_recurso_si_a_no_vuelve_a_60_dias(client, rv_permisos, con_decision, catalogo):
    from tests.test_practica_pruebas import _cambiar

    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, requiere=True)
    assert await _claves(client, exp_id, "recurso_") == ["recurso_concepto_pruebas"]
    await _cambiar(client, exp_id, False)
    a = (await _del_expediente(client, exp_id))["recurso_acto"]
    assert a["fecha_inicio"] == svc.hoy_bogota().isoformat() and a["semaforo"]["dias_totales"] == 60


# ───────────────────────────────────────────── fechas que llenan los triggers

async def test_triggers_fecha_version_final_y_respuesta(db_session):
    from datetime import datetime, timezone

    from sqlalchemy import update

    from db.models import ConceptoTecnico, Requerimiento

    fija = datetime(2026, 1, 5, 15, tzinfo=timezone.utc)
    c = ConceptoTecnico(tecnico_encargado_id=TECNICO)
    req = Requerimiento()
    db_session.add_all([c, req])
    await db_session.flush()
    await db_session.refresh(c)
    assert c.fecha_version_final is None

    # Primer PDF (ORM) → nace la fecha; reemplazarlo no la cambia; quitarlo la borra.
    c.doc_concepto_tecnico_id = 1
    await db_session.flush()
    await db_session.refresh(c)
    assert c.fecha_version_final is not None
    await db_session.execute(update(ConceptoTecnico).where(ConceptoTecnico.id == c.id).values(fecha_version_final=fija))
    await db_session.execute(update(ConceptoTecnico).where(ConceptoTecnico.id == c.id).values(doc_concepto_tecnico_id=2))
    await db_session.refresh(c)
    assert c.fecha_version_final == fija
    await db_session.execute(update(ConceptoTecnico).where(ConceptoTecnico.id == c.id).values(doc_concepto_tecnico_id=None))
    await db_session.refresh(c)
    assert c.fecha_version_final is None

    # Respuesta del usuario con UPDATE directo (como actualizar_versionado).
    await db_session.execute(update(Requerimiento).where(Requerimiento.id == req.id).values(doc_oficio_entrada_id=7))
    await db_session.refresh(req)
    primera = req.fecha_registro_respuesta
    assert primera is not None
    await db_session.execute(update(Requerimiento).where(Requerimiento.id == req.id).values(doc_oficio_entrada_id=8))
    await db_session.refresh(req)
    assert req.fecha_registro_respuesta == primera
    await db_session.rollback()


async def test_migracion_fechas_de_alertas_en_filas_existentes(expediente, db_session):
    """Simula el esquema anterior (sin las columnas ni los triggers): la
    migración completa las filas existentes con las fechas de respaldo."""
    from sqlalchemy import text

    from db.migrations import aplicar_migraciones
    from tests.conftest import engine

    async with engine.begin() as conn:
        for sql in (
            "DROP TRIGGER IF EXISTS concepto_fecha_version_final ON concepto_tecnico",
            "DROP TRIGGER IF EXISTS requerimiento_fecha_respuesta ON requerimiento",
            "ALTER TABLE recurso_reposicion DROP COLUMN fecha_creacion",
            "ALTER TABLE concepto_tecnico DROP COLUMN fecha_version_final",
            "ALTER TABLE requerimiento DROP COLUMN fecha_registro_respuesta",
        ):
            await conn.execute(text(sql))
        dec = (await conn.execute(text("INSERT INTO decision (expediente_id, version) VALUES (:e, 1) RETURNING id"),
                                  {"e": expediente.id})).scalar_one()
        await conn.execute(text(
            "INSERT INTO recurso_reposicion (decision_id, radicado, fecha_radicado, doc_recurso_id, requiere_pruebas, version) "
            "VALUES (:d, 'R1', DATE '2026-06-10', 1, false, 1)"), {"d": dec})
        await conn.execute(text(
            "INSERT INTO concepto_tecnico (tecnico_encargado_id, doc_concepto_tecnico_id, fecha_aceptacion, version) "
            "VALUES (32, 5, DATE '2026-05-20', 1), (32, NULL, NULL, 1)"))
        await conn.execute(text(
            "INSERT INTO requerimiento (doc_oficio_entrada_id, fecha_oficio_entrada, version) "
            "VALUES (6, DATE '2026-06-01', 1)"))
    async with engine.begin() as conn:
        await aplicar_migraciones(conn)
        await aplicar_migraciones(conn)  # idempotente

    def bogota(sql):
        return f"SELECT ({sql} AT TIME ZONE 'America/Bogota')::date"
    assert (await db_session.execute(text(bogota("fecha_creacion") + " FROM recurso_reposicion"))).scalar_one() == date(2026, 6, 10)
    fechas = (await db_session.execute(text(
        bogota("fecha_version_final") + " FROM concepto_tecnico ORDER BY id"))).scalars().all()
    assert fechas == [date(2026, 5, 20), None]
    assert (await db_session.execute(text(
        bogota("fecha_registro_respuesta") + " FROM requerimiento"))).scalar_one() == date(2026, 6, 1)
    # El esquema queda como el del modelo: NOT NULL con DEFAULT y triggers activos.
    assert (await db_session.execute(text(
        "SELECT is_nullable, column_default IS NOT NULL FROM information_schema.columns "
        "WHERE table_name = 'recurso_reposicion' AND column_name = 'fecha_creacion'"))).one() == ("NO", True)
    assert (await db_session.execute(text(
        "SELECT count(*) FROM pg_trigger WHERE tgname IN ('concepto_fecha_version_final', 'requerimiento_fecha_respuesta')"
    ))).scalar_one() == 2
