"""Mis informes (/mis-documentos): una lista con todos mis documentos (encargado y revisor)."""
from core.permission import Permission
from tests.fixtures_revision import *  # noqa: F401,F403


async def _mis(client, user, **params):
    r = await client.get("/mis-documentos", params=params, headers=headers(user))
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _ids(d: dict) -> set[int]:
    return {f["proceso_id"] for f in d["documentos"]}


def _fila(d: dict, pid: int) -> dict:
    return next(f for f in d["documentos"] if f["proceso_id"] == pid)


async def test_encargado_ve_sus_documentos_en_todos_los_estados(client, rv_proceso, crear_expediente):
    _, _, auto = await rv_proceso("AUTO_ADMITE")
    _, _, decision = await rv_proceso("DECISION")
    _, _, concepto = await rv_proceso("CONCEPTO_ETAPA2", encargado=TECNICO)

    # Recién asignados: del encargado, requieren su acción; nadie los revisa aún.
    d = await _mis(client, ABOGADO)
    assert _ids(d) == {auto.id, decision.id}
    assert d["conteos"] == {"total": 2, "requieren_accion": 2}
    fila = _fila(d, auto.id)
    assert fila["estado_proceso"]["codigo"] == "pendiente_carga" and fila["requiere_mi_accion"] is True
    assert fila["rol"] == "encargado" and fila["roles"] == ["encargado"]
    assert fila["tipo_documento_etiqueta"] == "Auto que admite"
    assert fila["expediente_codigo"].startswith("CA ") and fila["expediente_radicado"]
    assert fila["etapa_tipo"] == "acto_admite"
    assert "primera versión" in fila["accion_pendiente"]
    assert _ids(await _mis(client, TECNICO)) == {concepto.id}
    assert (await _mis(client, JURIDICO))["documentos"] == []
    assert (await _mis(client, PROYECTO))["documentos"] == []

    # Sube versiones: siguen en su lista, en revisión y sin acción suya.
    await subir(client, auto.id)
    await subir(client, decision.id)
    await subir(client, concepto.id, user=TECNICO)
    d = await _mis(client, ABOGADO)
    assert _ids(d) == {auto.id, decision.id}
    assert all(f["estado_proceso"]["codigo"] == "en_revision" and not f["requiere_mi_accion"] for f in d["documentos"])
    assert all(f["accion_pendiente"] is None for f in d["documentos"])
    assert d["conteos"] == {"total": 2, "requieren_accion": 0}

    # Devuelto: vuelve a requerir acción y va primero.
    await revisar(client, auto.id, "devuelto", JURIDICO, comentario="corregir")
    d = await _mis(client, ABOGADO)
    assert d["documentos"][0]["proceso_id"] == auto.id
    assert d["documentos"][0]["estado_proceso"]["codigo"] == "rechazado"
    assert d["documentos"][0]["requiere_mi_accion"] is True

    # Aprobado para firma: requiere cargar la versión final.
    await revisar(client, decision.id, "aprobado", JURIDICO)
    await revisar(client, decision.id, "aprobado", ASESORA)
    await revisar(client, decision.id, "aprobado_firma", PROYECTO)
    fila = _fila(await _mis(client, ABOGADO), decision.id)
    assert fila["estado_proceso"]["codigo"] == "aprobado_firma" and fila["requiere_mi_accion"] is True
    assert "versión firmada" in fila["accion_pendiente"]


async def test_revisor_solo_donde_participo_o_le_toca(client, rv_proceso, crear_expediente):
    _, _, auto = await rv_proceso("AUTO_ADMITE")
    _, _, decision = await rv_proceso("DECISION")
    _, _, concepto = await rv_proceso("CONCEPTO_ETAPA2", encargado=TECNICO)
    await subir(client, auto.id)
    await subir(client, decision.id)
    await subir(client, concepto.id, user=TECNICO)

    # Paso 1 jurídico: ambos líderes jurídicos lo tienen por revisar.
    for lider in (JURIDICO, JURIDICO2):
        d = await _mis(client, lider)
        assert _ids(d) == {auto.id, decision.id}
        fila = _fila(d, auto.id)
        assert fila["rol"] == "revisor" and fila["requiere_mi_accion"] is True
        assert fila["accion_pendiente"] == "Revisar el documento"
        assert fila["permisos_pendientes"] == [{"permiso": "recurso_lider_juridico", "etiqueta": "Líder jurídico"}]
        assert fila["paso_actual"] == 1 and fila["total_pasos"] == 2
    assert (await _mis(client, PROYECTO))["documentos"] == []  # aún no es su paso
    assert _ids(await _mis(client, SIG)) == {concepto.id}

    # JURIDICO aprueba la decisión: la sigue viendo (participó) sin acción;
    # JURIDICO2 (mismo permiso, no participó ni le toca) ya no la ve.
    await revisar(client, decision.id, "aprobado", JURIDICO)
    d = await _mis(client, JURIDICO)
    assert _ids(d) == {auto.id, decision.id}
    assert _fila(d, decision.id)["requiere_mi_accion"] is False
    assert d["documentos"][0]["proceso_id"] == auto.id  # lo que requiere acción va primero
    assert _ids(await _mis(client, JURIDICO2)) == {auto.id}
    # Paso paralelo: líder del proyecto y asesora.
    assert _ids(await _mis(client, PROYECTO)) == {decision.id}
    assert _ids(await _mis(client, ASESORA)) == {decision.id}

    # SIG revisa el concepto: sigue en su lista, sin acción; al líder técnico le toca.
    await revisar(client, concepto.id, "aprobado", SIG)
    d = await _mis(client, SIG)
    assert _ids(d) == {concepto.id} and d["documentos"][0]["requiere_mi_accion"] is False
    assert _fila(await _mis(client, LIDER_TECNICO), concepto.id)["requiere_mi_accion"] is True

    # Devuelto por JURIDICO: él lo sigue viendo (participó); JURIDICO2 no.
    await revisar(client, auto.id, "devuelto", JURIDICO, comentario="corregir")
    assert _fila(await _mis(client, JURIDICO), auto.id)["requiere_mi_accion"] is False
    assert (await _mis(client, JURIDICO2))["documentos"] == []


async def test_filtros_rol_y_solo_accion(client, rv_proceso, crear_expediente, rv_permisos):
    exp = await crear_expediente(expediente="CA 777-26")
    _, _, auto = await rv_proceso("AUTO_ADMITE", expediente=exp)
    _, _, decision = await rv_proceso("DECISION")
    await subir(client, decision.id)

    d = await _mis(client, ABOGADO, expediente="777")
    assert _ids(d) == {auto.id}
    d = await _mis(client, ABOGADO, tipo_documento="DECISION")
    assert _ids(d) == {decision.id}
    d = await _mis(client, ABOGADO, estado="en_revision")
    assert _ids(d) == {decision.id}
    d = await _mis(client, ABOGADO, solo_accion="true")
    assert _ids(d) == {auto.id}
    assert d["conteos"] == {"total": 2, "requieren_accion": 1}
    assert (await _mis(client, ABOGADO, rol="revisor"))["documentos"] == []
    assert _ids(await _mis(client, ABOGADO, rol="encargado")) == {auto.id, decision.id}

    # Encargado y revisor a la vez: una sola fila con los dos roles.
    rv_permisos.permisos.dar(ABOGADO, Permission.MANAGE, Permission.LIDER_JURIDICO)
    d = await _mis(client, ABOGADO)
    fila = _fila(d, decision.id)
    assert fila["roles"] == ["encargado", "revisor"] and fila["rol"] == "encargado"
    assert fila["requiere_mi_accion"] is True and fila["accion_pendiente"] == "Revisar el documento"
    assert len(d["documentos"]) == 2
    fila = _fila(await _mis(client, ABOGADO, rol="revisor"), decision.id)
    assert fila["roles"] == ["revisor"] and fila["requiere_mi_accion"] is True
    # Con rol=encargado la acción de revisor no cuenta.
    fila = _fila(await _mis(client, ABOGADO, rol="encargado"), decision.id)
    assert fila["roles"] == ["encargado"] and fila["requiere_mi_accion"] is False

    # Usuario sin nada a cargo: lista vacía (no 403).
    d = await _mis(client, EXTRANO)
    assert d["documentos"] == [] and d["conteos"] == {"total": 0, "requieren_accion": 0}
    assert {r["codigo"] for r in d["filtros"]["roles"]} == {"encargado", "revisor"}
    assert "finalizado" in {e["codigo"] for e in d["filtros"]["estados"]}


async def test_historico_no_vigente_y_paginacion(client, rv_proceso, crear_expediente, db_session):
    from sqlalchemy import update

    from db.models.documento_proceso import DocumentoProceso

    _, _, auto = await rv_proceso("AUTO_ADMITE")
    _, _, decision = await rv_proceso("DECISION")
    _, _, otro = await rv_proceso("AUTO_ADMITE")
    await subir(client, auto.id)
    await revisar(client, auto.id, "devuelto", JURIDICO, comentario="corregir")
    await subir(client, decision.id)
    # Cerrados/reemplazados (activo = false): siguen en el histórico, sin acción.
    await db_session.execute(
        update(DocumentoProceso).where(DocumentoProceso.id.in_([auto.id, decision.id])).values(activo=False)
    )
    await db_session.commit()

    d = await _mis(client, ABOGADO)
    assert _ids(d) == {auto.id, decision.id, otro.id}
    fila = _fila(d, auto.id)
    assert fila["estado_proceso"]["codigo"] == "rechazado" and fila["proceso_activo"] is False
    assert fila["requiere_mi_accion"] is False and fila["accion_pendiente"] is None
    assert d["conteos"] == {"total": 3, "requieren_accion": 1}
    # El revisor que participó lo conserva; el que solo tenía el turno de un no vigente, no.
    assert _ids(await _mis(client, JURIDICO)) == {auto.id}
    assert (await _mis(client, JURIDICO2))["documentos"] == []

    # Paginación como infraction: total / page / limit / total_pages; conteos de todo el conjunto.
    r = await client.get("/mis-documentos", params={"limit": 2, "page": 1}, headers=headers(ABOGADO))
    body = r.json()
    assert (body["total"], body["page"], body["limit"], body["total_pages"]) == (3, 1, 2, 2)
    assert body["data"]["documentos"][0]["proceso_id"] == otro.id  # requiere acción, primero
    assert len(body["data"]["documentos"]) == 2
    r = await client.get("/mis-documentos", params={"limit": 2, "page": 2}, headers=headers(ABOGADO))
    body = r.json()
    assert len(body["data"]["documentos"]) == 1 and body["data"]["conteos"]["total"] == 3
    assert body["data"]["documentos"][0]["expediente_codigo"].startswith("CA ")
    r = await client.get("/mis-documentos", params={"solo_accion": "true"}, headers=headers(ABOGADO))
    assert r.json()["total"] == 1 and r.json()["data"]["conteos"] == {"total": 3, "requieren_accion": 1}
