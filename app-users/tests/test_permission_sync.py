"""Tests de db/permission_sync.py (sincronización idempotente del catálogo al arrancar)."""
import pytest
from sqlalchemy import text

from conftest import engine
from db.permission_catalog import DEPENDENCIAS, DESCRIPCIONES_ANTERIORES, INCOMPATIBLES, PERMISOS
from db.permission_sync import sincronizar_permisos

TOTAL_DEPENDENCIAS = sum(len(r) for r in DEPENDENCIAS.values())
TOTAL_INCOMPATIBLES = 2 * len(INCOMPATIBLES)  # se guardan en los dos sentidos


async def _sync() -> dict:
    async with engine.begin() as conn:
        return await sincronizar_permisos(conn)


async def _estado() -> dict:
    async with engine.connect() as conn:
        permisos = (await conn.execute(text(
            "SELECT id, nombre, menu_path, descripcion FROM permiso ORDER BY id"
        ))).all()
        deps = (await conn.execute(text(
            "SELECT permiso_id, requiere_id FROM permiso_requiere ORDER BY 1, 2"
        ))).all()
        excl = (await conn.execute(text(
            "SELECT permiso_id, excluye_id FROM permiso_excluye ORDER BY 1, 2"
        ))).all()
        roles = (await conn.execute(text(
            "SELECT rol_id, permiso_id FROM rol_permiso ORDER BY 1, 2"
        ))).all()
    return {"permisos": permisos, "deps": deps, "excl": excl, "roles": roles}


async def _ids_por_nombre() -> dict[str, int]:
    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT id, nombre FROM permiso"))).all()
    return {nombre: pid for pid, nombre in rows}


async def _permisos_de_rol(rol_id: int) -> set[str]:
    async with engine.connect() as conn:
        return set((await conn.execute(text(
            "SELECT p.nombre FROM rol_permiso rp JOIN permiso p ON p.id = rp.permiso_id "
            "WHERE rp.rol_id = :r"
        ), {"r": rol_id})).scalars().all())


@pytest.mark.asyncio
async def test_sync_base_vacia_y_segunda_corrida_identica():
    r1 = await _sync()
    assert len(r1["insertados"]) == len(PERMISOS)
    assert r1["dependencias_agregadas"] == TOTAL_DEPENDENCIAS
    assert r1["incompatibles_agregadas"] == TOTAL_INCOMPATIBLES
    estado1 = await _estado()
    assert all(p.descripcion for p in estado1["permisos"])
    assert len(estado1["deps"]) == TOTAL_DEPENDENCIAS
    assert len(estado1["excl"]) == TOTAL_INCOMPATIBLES

    r2 = await _sync()
    assert r2["insertados"] == []
    assert r2["actualizados"] == []
    assert r2["renombrados"] == []
    assert r2["dependencias_agregadas"] == 0
    assert r2["dependencias_quitadas"] == 0
    assert r2["incompatibles_agregadas"] == 0 and r2["incompatibles_quitadas"] == 0
    assert await _estado() == estado1


@pytest.mark.asyncio
async def test_sync_renombra_infraccion_cargue_y_conserva_roles(db_session, make_permiso, make_rol):
    viejo = await make_permiso("infraccion_cargue")
    gestionar = await make_permiso("infraccion_gestionar", "/infraction/manage")
    rol = await make_rol("cargue", [viejo, gestionar])
    await db_session.commit()

    r = await _sync()
    assert ("infraccion_cargue", "infraccion_super_gestion") in r["renombrados"]
    ids = await _ids_por_nombre()
    assert "infraccion_cargue" not in ids
    assert ids["infraccion_super_gestion"] == viejo.id
    assert {"infraccion_super_gestion", "infraccion_gestionar"} <= await _permisos_de_rol(rol.id)

    # Segunda corrida: nada que renombrar.
    assert (await _sync())["renombrados"] == []


@pytest.mark.asyncio
async def test_sync_renombra_informes_infraccion_a_tecnico_y_lider(db_session, make_permiso, make_rol):
    """infraccion_informes_subir/_revisar -> infraccion_tecnico/_lider_tecnico:
    los roles los conservan y la descripción por defecto vieja se actualiza."""
    subir = await make_permiso(
        "infraccion_informes_subir", "/infraction/my-reports",
        DESCRIPCIONES_ANTERIORES["infraccion_tecnico"][0],
    )
    revisar = await make_permiso(
        "infraccion_informes_revisar", "/infraction/my-reports",
        DESCRIPCIONES_ANTERIORES["infraccion_lider_tecnico"][0],
    )
    rol = await make_rol("informes", [subir, revisar])
    await db_session.commit()

    r = await _sync()
    assert ("infraccion_informes_subir", "infraccion_tecnico") in r["renombrados"]
    assert ("infraccion_informes_revisar", "infraccion_lider_tecnico") in r["renombrados"]
    ids = await _ids_por_nombre()
    assert ids["infraccion_tecnico"] == subir.id
    assert ids["infraccion_lider_tecnico"] == revisar.id
    assert {"infraccion_tecnico", "infraccion_lider_tecnico"} <= await _permisos_de_rol(rol.id)

    actuales = {p["nombre"]: p["descripcion"] for p in PERMISOS}
    async with engine.connect() as conn:
        desc = dict((await conn.execute(text(
            "SELECT nombre, descripcion FROM permiso WHERE nombre IN ('infraccion_tecnico', 'infraccion_lider_tecnico')"
        ))).all())
    assert desc == {n: actuales[n] for n in desc}
    assert ("infraccion_tecnico", "infraccion_gestionar") in INCOMPATIBLES


@pytest.mark.asyncio
async def test_sync_crea_lider_proyecto_infraccion_y_actualiza_mis_actuaciones(db_session, make_permiso):
    """infraccion_lider_proyecto (revisa los actos) requiere consultar; las
    descripciones por defecto de "Mis informes" pasan a "Mis actuaciones"."""
    await make_permiso(
        "infraccion_tecnico", "/infraction/my-reports", DESCRIPCIONES_ANTERIORES["infraccion_tecnico"][-1],
    )
    await make_permiso(
        "infraccion_super_gestion", "", DESCRIPCIONES_ANTERIORES["infraccion_super_gestion"][-1],
    )
    await db_session.commit()

    await _sync()
    assert DEPENDENCIAS["infraccion_lider_proyecto"] == ("infraccion_consultar",)
    actuales = {p["nombre"]: p for p in PERMISOS}
    assert actuales["infraccion_lider_proyecto"]["menu_path"] == "/infraction/my-reports"
    async with engine.connect() as conn:
        desc = dict((await conn.execute(text(
            "SELECT nombre, descripcion FROM permiso WHERE nombre IN "
            "('infraccion_lider_proyecto', 'infraccion_tecnico', 'infraccion_super_gestion')"
        ))).all())
        requiere = (await conn.execute(text(
            "SELECT r.nombre FROM permiso_requiere pr JOIN permiso p ON p.id = pr.permiso_id "
            "JOIN permiso r ON r.id = pr.requiere_id WHERE p.nombre = 'infraccion_lider_proyecto'"
        ))).scalars().all()
    assert desc == {n: actuales[n]["descripcion"] for n in desc} and len(desc) == 3
    assert "Mis actuaciones" in desc["infraccion_tecnico"]
    assert requiere == ["infraccion_consultar"]


@pytest.mark.asyncio
async def test_sync_con_ambos_nombres_no_borra_nada(db_session, make_permiso, make_rol):
    viejo = await make_permiso("infraccion_cargue")
    nuevo = await make_permiso("infraccion_super_gestion")
    await make_rol("r", [viejo, nuevo])
    await db_session.commit()

    r = await _sync()
    assert r["renombrados"] == []
    assert r["advertencias"]
    ids = await _ids_por_nombre()
    assert ids["infraccion_cargue"] == viejo.id
    assert ids["infraccion_super_gestion"] == nuevo.id


@pytest.mark.asyncio
async def test_sync_respeta_descripcion_editada_y_llena_vacias(db_session, make_permiso):
    # La descripción editada en la pantalla de permisos NO se pisa; el catálogo
    # solo llena las vacías (igual que menu_path).
    personalizado = await make_permiso("sancionatorio_gestionar", "/ruta/propia",
                                       descripcion="Texto editado desde la pantalla.")
    vacio = await make_permiso("sancionatorio_consultar", "", descripcion="")
    await db_session.commit()

    await _sync()
    async with engine.connect() as conn:
        filas = {
            f.nombre: f for f in (await conn.execute(text(
                "SELECT nombre, menu_path, descripcion FROM permiso "
                "WHERE nombre IN ('sancionatorio_gestionar', 'sancionatorio_consultar')"
            ))).all()
        }
    catalogo = {p["nombre"]: p for p in PERMISOS}
    assert filas["sancionatorio_gestionar"].menu_path == "/ruta/propia"
    assert filas["sancionatorio_gestionar"].descripcion == "Texto editado desde la pantalla."
    assert filas["sancionatorio_consultar"].descripcion == catalogo["sancionatorio_consultar"]["descripcion"]
    assert filas["sancionatorio_consultar"].menu_path == "/file/consult"
    assert vacio.id == (await _ids_por_nombre())["sancionatorio_consultar"]


@pytest.mark.asyncio
async def test_sync_no_duplica_ni_borra_ajenos_y_quita_dependencias_sobrantes(db_session, make_permiso):
    ajeno = await make_permiso("permiso_manual_vm")
    a = await make_permiso("admin_gestionar_usuarios")
    b = await make_permiso("admin_registrar_usuarios")
    await db_session.commit()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO permiso_requiere (permiso_id, requiere_id) VALUES (:a, :b)"),
            {"a": a.id, "b": b.id},
        )

    r = await _sync()
    assert r["dependencias_quitadas"] == 1
    ids = await _ids_por_nombre()
    assert ids["permiso_manual_vm"] == ajeno.id
    assert len(ids) == len(PERMISOS) + 1  # catálogo + el ajeno, sin duplicados
    estado = await _estado()
    assert (a.id, b.id) not in estado["deps"]
    assert len(estado["deps"]) == TOTAL_DEPENDENCIAS


@pytest.mark.asyncio
async def test_sync_no_modifica_roles_que_incumplen_y_los_reporta(db_session, make_permiso, make_rol):
    # Base "existente": algunos permisos ya sembrados; admin los tiene todos.
    alertas = await make_permiso("infraccion_alertas", "/infraction/alertas")
    consultar = await make_permiso("infraccion_consultar", "/infraction/consult")
    roles_perm = await make_permiso("admin_roles_y_permisos", "/user/role")
    admin = await make_rol("admin", [alertas, consultar, roles_perm])
    incompleto = await make_rol("solo_alertas", [alertas])
    await db_session.commit()

    r = await _sync()

    # El rol que incumple no se toca y queda reportado.
    assert await _permisos_de_rol(incompleto.id) == {"infraccion_alertas"}
    reporte = {x["rol_id"]: x for x in r["roles_incumplen"]}
    assert reporte[incompleto.id]["faltantes"] == [
        {"permiso": "infraccion_alertas", "requiere": ["infraccion_consultar"]}
    ]
    # Los permisos que nacen en esta corrida se otorgan al rol que tenía todos,
    # para que alguien pueda verlos y asignarlos desde la pantalla de roles.
    assert r["otorgados_a_roles"] == [admin.id]
    assert await _permisos_de_rol(admin.id) == {p["nombre"] for p in PERMISOS}
    assert admin.id not in reporte

    # Segunda corrida: no vuelve a tocar roles.
    roles_antes = (await _estado())["roles"]
    r2 = await _sync()
    assert r2["otorgados_a_roles"] == []
    assert (await _estado())["roles"] == roles_antes


@pytest.mark.asyncio
async def test_sync_admin_siempre_queda_con_todos_los_permisos(db_session, make_permiso, make_rol):
    # Base existente donde a admin le faltan permisos (no los tenía todos, así
    # que el paso de "superadministrador" no lo alcanza).
    consultar = await make_permiso("infraccion_consultar", "/infraction/consult")
    await make_permiso("infraccion_lider_proyecto", "/infraction/my-reports")
    ajeno = await make_permiso("permiso_manual_vm")
    admin = await make_rol("admin", [consultar])
    otro = await make_rol("consulta", [consultar])
    await db_session.commit()

    r = await _sync()
    todos = {p["nombre"] for p in PERMISOS} | {ajeno.nombre}
    assert await _permisos_de_rol(admin.id) == todos
    assert r["otorgados_a_admin"] == len(todos) - 1
    # Los demás roles no se tocan.
    assert await _permisos_de_rol(otro.id) == {"infraccion_consultar"}

    # Idempotente.
    assert (await _sync())["otorgados_a_admin"] == 0


@pytest.mark.asyncio
async def test_sync_incompatibles_en_los_dos_sentidos_y_quita_sobrantes(db_session, make_permiso):
    a = await make_permiso("admin_gestionar_usuarios")
    b = await make_permiso("admin_registrar_usuarios")
    await db_session.commit()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO permiso_excluye (permiso_id, excluye_id) VALUES (:a, :b)"),
            {"a": a.id, "b": b.id},
        )

    r = await _sync()
    assert r["incompatibles_quitadas"] == 1
    ids = await _ids_por_nombre()
    excl = set((await _estado())["excl"])
    assert (a.id, b.id) not in excl
    for x, y in INCOMPATIBLES:
        assert (ids[x], ids[y]) in excl and (ids[y], ids[x]) in excl


@pytest.mark.asyncio
async def test_sync_reemplaza_descripcion_anterior_solo_si_nadie_la_edito(db_session, make_permiso):
    anterior = DESCRIPCIONES_ANTERIORES["recurso_tecnico"][0]
    await make_permiso("recurso_tecnico", "/recurso/my-reports", descripcion=anterior)
    await make_permiso("recurso_sig", "/recurso/my-reports", descripcion="Texto propio del área.")
    await db_session.commit()

    r = await _sync()
    catalogo = {p["nombre"]: p for p in PERMISOS}
    async with engine.connect() as conn:
        filas = dict((await conn.execute(text(
            "SELECT nombre, descripcion FROM permiso WHERE nombre IN ('recurso_tecnico', 'recurso_sig')"
        ))).all())
    assert filas["recurso_tecnico"] == catalogo["recurso_tecnico"]["descripcion"]
    assert "Mis actuaciones" in filas["recurso_tecnico"]
    assert filas["recurso_sig"] == "Texto propio del área."
    assert "recurso_tecnico" in r["actualizados"]
    assert (await _sync())["actualizados"] == []  # idempotente


@pytest.mark.asyncio
async def test_sync_reporta_rol_con_incompatibles_y_no_lo_modifica(db_session, make_permiso, make_rol):
    tecnico = await make_permiso("recurso_tecnico", "/recurso/my-reports")
    gestionar = await make_permiso("recurso_gestionar", "/recurso/manage")
    consultar = await make_permiso("recurso_consultar", "/recurso/consult")
    # Un permiso que el rol no tiene: si tuviera todos, el sync lo trataría como
    # superadministrador (le daría admin_roles_y_permisos y quedaría exento).
    await make_permiso("recurso_sig", "/recurso/my-reports")
    mezcla = await make_rol("mezcla", [tecnico, gestionar, consultar])
    await db_session.commit()

    r = await _sync()
    reporte = {x["rol_id"]: x for x in r["roles_incumplen"]}
    assert reporte[mezcla.id]["incompatibles"] == [{"permiso": "recurso_gestionar", "con": "recurso_tecnico"}]
    assert await _permisos_de_rol(mezcla.id) == {"recurso_tecnico", "recurso_gestionar", "recurso_consultar"}
