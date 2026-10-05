# satc_shared

Paquete Python compartido por los microservicios SATC (app-users, app-docs,
app-infraction, app-sancionatoria, app-involved).

| Módulo | Qué contiene |
|---|---|
| `satc_shared.auth` | Service JWT (`x-service-token`): `generate_service_jwt`, `identify_caller`, `expected_callers_from_env`. Mismo esquema que antes (claims `service/iat/exp`, HS256, 5 min, secretos `*_SERVICE_SECRET`). |
| `satc_shared.clients` | Clientes async tipados: `UsersClient`, `FilesClient` (app-docs `/files`), `InvolvedClient`. Errores tipados (`ServiceClientError` y subclases). |
| `satc_shared.review_process` | Mixins SQLAlchemy + máquina de estados + servicio genérico del proceso de revisión de documentos y contrato Pydantic `ProcesoDetalle`. |

**Regla: el paquete no conoce flujos concretos.** Nada de "informe técnico",
"documento genérico", permisos de una app ni notificaciones: eso vive en cada app,
que extiende lo genérico por subclase o callables.

## Instalación

Docker (ya configurado): cada servicio Python declara en `docker-compose.yml`

```yaml
build:
  context: ./app-x
  additional_contexts:
    shared: ./shared
```

y su Dockerfile hace `COPY --from=shared . /shared` + `pip install /shared`.
Con `docker build` directo: `docker build --build-context shared=./shared ./app-x`.

Desarrollo / tests locales (desde la raíz del repo):

```bash
.venv/Scripts/python -m pip install -e shared
.venv/Scripts/python -m pip install pytest pytest-asyncio aiosqlite
cd shared && ../.venv/Scripts/python -m pytest -q
```

## Clientes

```python
from satc_shared.clients import UsersClient, FilesClient, ServiceClientError

users = UsersClient.from_env("infraction-service")   # USER_SERVICE_URL + SERVICE_SECRET_KEY
files = FilesClient.from_env("infraction-service")   # DOCS_SERVICE_URL + SERVICE_SECRET_KEY

await users.verify_permission(user_id, "file_manage")       # bool, lanza si falla la llamada
subido = await files.upload("informe.pdf", data, "application/pdf")
await files.increment_usage([subido.file_id])
```

Los clientes **lanzan**; la política ante fallo (fail-closed, `{}` vacío...) la
decide el wrapper de cada servicio (`services/users.py`, `services/docs.py`...).

## Proceso de revisión

1. Modelos concretos con el `Base` y tablas de la app:

```python
from satc_shared.review_process import *

class Proceso(ProcesoRevisionMixin, Base):
    __tablename__ = "informe_procesos"

class Version(VersionRevisionMixin, Base):
    __tablename__ = "informe_versiones"
    __proceso_tabla__ = "informe_procesos"      # FK -> informe_procesos.id
# idem Revision(RevisionMixin), Auditoria(AuditoriaRevisionMixin), Asignacion(AsignacionRevisorMixin)

MODELS = ReviewModels(proceso=Proceso, version=Version, revision=Revision,
                      auditoria=Auditoria, asignacion=Asignacion)
```

`__proceso_fk_columna__ = "documento_id"` cambia el nombre de la columna FK; cualquier
otra columna se renombra redefiniendo el atributo (`creador_id = mapped_column("usuario_creador_id", Integer)`).

2. Flujo base: `pendiente_carga` → (subir v1) → `en_revision` → `aprobado` |
   `devuelto` → `rechazado` (o `finalizado` al llegar a `max_devoluciones`, default 3).
   Solo `devuelto` admite adjunto (pdf/doc/docx). Solo se sube versión en
   `pendiente_carga` o `rechazado`.

3. Extensión mínima (ejemplo `aprobado_firma`):

```python
class FlujoInformeTecnico(FlujoRevision):
    ESTADOS_EXTRA = (Estado("aprobado_firma", "Aprobado para firma", "warning"),)
    ACCIONES_EXTRA = (Accion("aprobado_firma", "Aprobar para firma",
                             etiqueta_realizada="Aprobado para firma", tono="success",
                             estado_destino="aprobado_firma", auditoria="aprobar_firma"),)
    estados_subida = FlujoRevision.estados_subida | {"aprobado_firma"}

    def extensiones_subida(self, proceso):                 # la firmada debe ser PDF
        return (".pdf",) if proceso.estado == "aprobado_firma" else super().extensiones_subida(proceso)

    async def validar_accion(self, ctx, accion, user_id):  # "aprobar exige PDF"
        motivo = await super().validar_accion(ctx, accion, user_id)
        if not motivo and accion.codigo == "aprobado":
            v = await ctx.ultima_version()
            if not v.archivo_nombre.lower().endswith(".pdf"):
                return "Para aprobar, la versión debe estar en PDF"
        return motivo

    async def despues_de_subida(self, ctx, version, user_id, estado_anterior):
        if estado_anterior == "aprobado_firma":           # la firmada se auto-aprueba
            revisor = await ctx.ultimo_revisor("aprobado_firma")
            await ctx.registrar_revision(accion="aprobado", revisor_id=revisor or user_id,
                                         comentarios="Auto-aprobado: versión firmada")
            return "aprobado"
        return await super().despues_de_subida(ctx, version, user_id, estado_anterior)
```

Permisos: sobrescribir `puede_ver/puede_revisar/puede_subir_version` o pasarlos
como callables `async (ctx, user_id) -> bool` al constructor del flujo.

4. Uso en una ruta:

```python
svc = ProcesoRevisionService(MODELS, FlujoInformeTecnico(), files=FilesClient.from_env("infraction-service"))
try:
    res = await svc.revisar(db, proceso_id, user_id=uid, accion="devuelto", comentario=c, adjunto=ref)
    await db.commit()          # el servicio solo hace flush: el commit es de la app
except ReviewError as e:
    await db.rollback()
    raise HTTPException(e.status_code, e.detail)
detalle = await svc.detalle(db, proceso_id, user_id=uid, nombres_usuarios=nombres)  # -> ProcesoDetalle
```

`ProcesoDetalle.acciones_disponibles` se calcula por usuario y es la fuente de
verdad para la UI (incluye `bloqueada` con el motivo cuando la acción aplica pero
no se puede ejecutar todavía).
