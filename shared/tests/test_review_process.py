import pytest

from satc_shared.review_process import (
    Accion,
    ArchivoRef,
    ErrorUsoArchivo,
    Estado,
    FlujoRevision,
    PermisoDenegado,
    ProcesoNoEncontrado,
    ProcesoRevisionService,
    TransicionInvalida,
    ValidacionError,
    VersionDuplicada,
)

from conftest import MODELS, FakeTracker, Revision

CREADOR, REVISOR, OTRO = 10, 20, 30


def archivo(file_id: int, nombre: str = "doc.pdf") -> ArchivoRef:
    return ArchivoRef(file_id=file_id, url=f"bucket/{file_id}/{nombre}", nombre=nombre, size=100)


async def nuevo(svc, db, *, con_archivo=True, nombre="doc.pdf"):
    p = await svc.crear_proceso(
        db, nombre="Informe", creador_id=CREADOR, revisores_ids=[REVISOR],
        archivo=archivo(1, nombre) if con_archivo else None,
    )
    await db.commit()
    return p


# ------------------------------------------------------------ flujo base
async def test_crear_con_archivo_queda_en_revision(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db)
    assert p.estado == "en_revision"
    assert p.version_actual == 1
    assert tracker.incrementos == [[1]]


async def test_crear_sin_archivo_queda_pendiente_y_no_se_puede_revisar(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db, con_archivo=False)
    assert p.estado == "pendiente_carga"
    with pytest.raises(TransicionInvalida):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado")
    # el creador sube la primera versión
    r = await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(5))
    assert r.inicial and r.estado_nuevo == "en_revision"


async def test_crear_exige_revisores(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    with pytest.raises(ValidacionError):
        await svc.crear_proceso(db, nombre="x", creador_id=CREADOR, revisores_ids=[])


async def test_aprobar(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db)
    r = await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado", comentario="ok")
    assert r.estado_nuevo == "aprobado" and p.estado == "aprobado"
    # estado final: ya no se puede revisar ni subir
    with pytest.raises(TransicionInvalida):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto")
    with pytest.raises(TransicionInvalida):
        await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(9))


async def test_solo_revisor_asignado_revisa(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)
    with pytest.raises(PermisoDenegado):
        await svc.revisar(db, p.id, user_id=OTRO, accion="aprobado")
    with pytest.raises(PermisoDenegado):
        await svc.subir_version(db, p.id, user_id=REVISOR, archivo=archivo(2))


async def test_accion_invalida_y_proceso_inexistente(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)
    with pytest.raises(ValidacionError):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado_firma")
    with pytest.raises(ProcesoNoEncontrado):
        await svc.revisar(db, 999, user_id=REVISOR, accion="aprobado")


async def test_devolver_y_subir_nueva_version(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db)
    # subir en en_revision no se permite
    with pytest.raises(TransicionInvalida):
        await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(2))
    r = await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="corrige")
    assert r.estado_nuevo == "rechazado" and p.numero_devoluciones == 1
    v = await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(2, "v2.docx"))
    assert v.estado_nuevo == "en_revision" and v.version.numero_version == 2 and not v.inicial


async def test_version_duplicada(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)
    await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="motivo")
    with pytest.raises(VersionDuplicada):
        await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(1))


async def test_extension_de_version(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    with pytest.raises(ValidacionError):
        await svc.crear_proceso(
            db, nombre="x", creador_id=CREADOR, revisores_ids=[REVISOR], archivo=archivo(1, "a.exe")
        )


@pytest.mark.parametrize("maximo", [1, 3])
async def test_max_devoluciones_finaliza(db, maximo):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(max_devoluciones=maximo))
    p = await nuevo(svc, db)
    for i in range(1, maximo + 1):
        r = await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="motivo")
        if i < maximo:
            assert r.estado_nuevo == "rechazado"
            await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(100 + i))
    assert r.estado_nuevo == "finalizado" and r.finalizado
    assert p.numero_devoluciones == maximo
    with pytest.raises(TransicionInvalida):
        await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(500))


async def test_adjunto_solo_al_devolver(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db)
    with pytest.raises(ValidacionError):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado", adjunto=archivo(7, "obs.pdf"))
    with pytest.raises(ValidacionError):  # extensión no permitida
        await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="motivo", adjunto=archivo(7, "obs.png"))
    r = await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="motivo", adjunto=archivo(7, "obs.docx"))
    assert r.revision.adjunto_file_id == 7 and r.revision.adjunto_nombre == "obs.docx"
    assert [7] in tracker.incrementos


async def test_fallo_numero_usos_lanza_error(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), FakeTracker(falla=True))
    with pytest.raises(ErrorUsoArchivo):
        await svc.crear_proceso(
            db, nombre="x", creador_id=CREADOR, revisores_ids=[REVISOR], archivo=archivo(1)
        )
    svc2 = ProcesoRevisionService(MODELS, FlujoRevision(), FakeTracker(ok=False))
    await db.rollback()
    with pytest.raises(ErrorUsoArchivo):
        await svc2.crear_proceso(
            db, nombre="x", creador_id=CREADOR, revisores_ids=[REVISOR], archivo=archivo(1)
        )


async def test_devolver_exige_comentario(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)
    with pytest.raises(ValidacionError):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto")
    det = await svc.detalle(db, p.id, user_id=REVISOR)
    devolver = next(a for a in det.acciones_disponibles if a.codigo == "devuelto")
    assert devolver.requiere_comentario is True
    iconos = {a.codigo: a.icono for a in det.acciones_disponibles}
    assert iconos == {"aprobado": "aprobar", "devuelto": "devolver"}


async def test_comentario_requerido_por_subclase(db):
    class Flujo(FlujoRevision):
        ACCIONES_EXTRA = (
            Accion("devuelto", "Devolver", etiqueta_realizada="Devuelto", tono="warning", requiere_comentario=True,
                   adjunto_extensiones=(".pdf",), cuenta_devolucion=True, auditoria="devolver"),
        )

    svc = ProcesoRevisionService(MODELS, Flujo())
    p = await nuevo(svc, db)
    with pytest.raises(ValidacionError):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="  ")
    r = await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="falta firma")
    assert r.estado_nuevo == "rechazado"


async def test_finalizar_forzado(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)
    await svc.finalizar(db, p.id, usuario_id=None, descripcion="Cancelado por la app")
    assert p.estado == "finalizado"
    det = await svc.detalle(db, p.id, user_id=REVISOR)
    assert det.acciones_disponibles == []
    assert det.auditoria[-1].accion == "finalizar"


async def test_eliminar_decrementa_usos(db, tracker):
    svc = ProcesoRevisionService(MODELS, FlujoRevision(), tracker)
    p = await nuevo(svc, db)
    await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="motivo", adjunto=archivo(7, "o.pdf"))
    await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(2))
    await svc.eliminar_proceso(db, p.id)
    assert sorted(tracker.decrementos[0]) == [1, 2, 7]
    with pytest.raises(ProcesoNoEncontrado):
        await svc.cargar(db, p.id)


# --------------------------------------------- extensión: aprobado_firma
class FlujoFirma(FlujoRevision):
    """Ejemplo del README: aprobar para firma -> el creador sube la versión
    firmada en PDF y se auto-aprueba. Aprobar directo exige PDF."""

    ESTADOS_EXTRA = (Estado("aprobado_firma", "Aprobado para firma", "warning"),)
    ACCIONES_EXTRA = (
        Accion("aprobado_firma", "Aprobar para firma", etiqueta_realizada="Aprobado para firma", tono="success",
               estado_destino="aprobado_firma", auditoria="aprobar_firma"),
    )
    estados_subida = FlujoRevision.estados_subida | {"aprobado_firma"}

    def extensiones_subida(self, proceso):
        if proceso.estado == "aprobado_firma":
            return (".pdf",)
        return super().extensiones_subida(proceso)

    async def validar_accion(self, ctx, accion, user_id):
        motivo = await super().validar_accion(ctx, accion, user_id)
        if motivo or accion.codigo != "aprobado":
            return motivo
        version = await ctx.ultima_version()
        if not version.archivo_nombre.lower().endswith(".pdf"):
            return "Para aprobar, la versión debe estar en PDF"
        return None

    async def despues_de_subida(self, ctx, version, user_id, estado_anterior):
        if estado_anterior == "aprobado_firma":
            revisor = await ctx.ultimo_revisor("aprobado_firma")
            await ctx.registrar_revision(
                accion="aprobado", revisor_id=revisor or user_id,
                comentarios="Auto-aprobado: versión firmada",
            )
            return "aprobado"
        return await super().despues_de_subida(ctx, version, user_id, estado_anterior)


async def test_subclase_aprobado_firma(db):
    svc = ProcesoRevisionService(MODELS, FlujoFirma())
    p = await nuevo(svc, db, nombre="borrador.docx")

    # aprobar directo bloqueado por no ser PDF; aprobar para firma sí
    det = await svc.detalle(db, p.id, user_id=REVISOR)
    acciones = {a.codigo: a for a in det.acciones_disponibles}
    assert set(acciones) == {"aprobado", "devuelto", "aprobado_firma"}
    assert acciones["aprobado"].bloqueada == "Para aprobar, la versión debe estar en PDF"
    assert acciones["aprobado_firma"].bloqueada is None
    with pytest.raises(ValidacionError):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado")

    r = await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado_firma")
    assert r.estado_nuevo == "aprobado_firma"

    det = await svc.detalle(db, p.id, user_id=CREADOR)
    assert det.estado.codigo == "aprobado_firma" and det.estado.tono == "warning"
    assert det.subida_version.permitida and det.subida_version.extensiones == [".pdf"]

    # la firmada debe ser PDF
    with pytest.raises(ValidacionError):
        await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(2, "firmado.docx"))
    v = await svc.subir_version(db, p.id, user_id=CREADOR, archivo=archivo(3, "firmado.pdf"))
    assert v.estado_nuevo == "aprobado"
    await db.commit()

    det = await svc.detalle(db, p.id, user_id=CREADOR)
    assert det.estado.codigo == "aprobado"
    auto = det.revisiones[0]
    assert auto.accion == "aprobado" and auto.revisor_id == REVISOR and auto.version_revisada == 2
    assert auto.accion_etiqueta == "Aprobado" and auto.tono == "success"
    firma = det.revisiones[1]
    assert (firma.accion_etiqueta, firma.tono) == ("Aprobado para firma", "success")
    eventos = {a.accion: (a.accion_etiqueta, a.tono) for a in det.auditoria}
    assert eventos["aprobar_firma"] == ("Aprobado para firma", "success")


def test_eventos_auditoria_extra_y_fallback():
    from satc_shared.review_process import EventoAuditoria

    class Flujo(FlujoRevision):
        EVENTOS_AUDITORIA_EXTRA = (EventoAuditoria("reasignar", "Reasignado", "warning"),)

    flujo = Flujo()
    assert flujo.evento_auditoria("reasignar") == EventoAuditoria("reasignar", "Reasignado", "warning")
    assert flujo.evento_auditoria("aprobar") == EventoAuditoria("aprobar", "Aprobado", "success")
    assert flujo.evento_auditoria("codigo_raro") == EventoAuditoria("codigo_raro", "Codigo raro", "neutral")
    # Accion: tras ``etiqueta`` todo es keyword-only (no se confunde tono con etiqueta_realizada)
    with pytest.raises(TypeError):
        Accion("x", "X", "success")  # type: ignore[misc]


async def test_permisos_por_callable(db):
    async def solo_jefe(ctx, user_id):
        return user_id == OTRO

    svc = ProcesoRevisionService(MODELS, FlujoRevision(puede_revisar=solo_jefe))
    p = await nuevo(svc, db)
    with pytest.raises(PermisoDenegado):
        await svc.revisar(db, p.id, user_id=REVISOR, accion="aprobado")
    r = await svc.revisar(db, p.id, user_id=OTRO, accion="aprobado")
    assert r.estado_nuevo == "aprobado"


# ---------------------------------------------------- detalle / contrato
async def test_detalle_acciones_por_usuario(db):
    svc = ProcesoRevisionService(MODELS, FlujoRevision())
    p = await nuevo(svc, db)

    det_rev = await svc.detalle(db, p.id, user_id=REVISOR, nombres_usuarios={REVISOR: "Ana"})
    assert [a.codigo for a in det_rev.acciones_disponibles] == ["aprobado", "devuelto"]
    devolver = det_rev.acciones_disponibles[1]
    assert devolver.adjunto.permitido and devolver.adjunto.extensiones == [".pdf", ".doc", ".docx"]
    assert det_rev.acciones_disponibles[0].adjunto.permitido is False
    assert det_rev.subida_version is None  # el revisor no sube versiones
    assert det_rev.revisores[0].nombre == "Ana"
    assert det_rev.max_devoluciones == 3
    assert det_rev.estado.model_dump() == {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"}

    det_cre = await svc.detalle(db, p.id, user_id=CREADOR)
    assert det_cre.acciones_disponibles == []
    assert det_cre.subida_version.permitida is False and det_cre.subida_version.motivo

    with pytest.raises(PermisoDenegado):
        await svc.detalle(db, p.id, user_id=OTRO)

    await svc.revisar(db, p.id, user_id=REVISOR, accion="devuelto", comentario="x", adjunto=archivo(8, "o.pdf"))
    det = await svc.detalle(db, p.id, user_id=CREADOR, nombres_usuarios={REVISOR: "Ana"})
    assert det.subida_version.permitida is True
    rev = det.revisiones[0]
    assert rev.revisor_nombre == "Ana" and rev.accion_etiqueta == "Devuelto" and rev.adjunto.file_id == 8
    assert [a.accion for a in det.auditoria] == ["crear", "subir_version_inicial", "devolver"]
    assert [(a.accion_etiqueta, a.tono) for a in det.auditoria] == [
        ("Proceso creado", "info"), ("Versión inicial cargada", "info"), ("Devuelto", "warning"),
    ]
    assert det.versiones[0].archivo.file_id == 1
    # serializable a JSON para el frontend
    assert det.model_dump(mode="json")["estado"]["codigo"] == "rechazado"


async def test_fk_requiere_tabla_proceso():
    from sqlalchemy.orm import DeclarativeBase

    from satc_shared.review_process import VersionRevisionMixin

    class B(DeclarativeBase):
        pass

    with pytest.raises(TypeError):
        class SinTabla(VersionRevisionMixin, B):
            __tablename__ = "sin_tabla"


async def test_fk_columna_personalizada():
    from sqlalchemy.orm import DeclarativeBase

    from satc_shared.review_process import ProcesoRevisionMixin, RevisionMixin

    class B(DeclarativeBase):
        pass

    class Doc(ProcesoRevisionMixin, B):
        __tablename__ = "documentos"

    class Rev(RevisionMixin, B):
        __tablename__ = "revisiones"
        __proceso_tabla__ = "documentos"
        __proceso_fk_columna__ = "documento_id"

    col = Rev.__table__.c["documento_id"]
    assert list(col.foreign_keys)[0].target_fullname == "documentos.id"
    assert Rev.proceso_id.property.columns[0] is col
    assert Revision.__table__.c["proceso_id"] is not None
