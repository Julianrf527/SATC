# Playbook de refactor — aplicar a otro microservicio SATC

Prompt para repetir en `app-docs`, `app-infraction`, `app-involved`, `app-users` o `api-gateway` el mismo trabajo hecho en `app-sancionatoria`. Reemplazar `<SERVICIO>` por el nombre real (ej. `app-infraction`) antes de usar.

---

## Prompt

Quiero hacer en `<SERVICIO>` el mismo trabajo de limpieza y refactor que ya hicimos en `app-sancionatoria`. Segui este orden, verificando con tests antes de avanzar a lo siguiente — no asumas que algo funciona sin correrlo.

### Fase 0 — Diagnóstico de arquitectura
- Lee el servicio completo. Identifica el patrón real que implementa (Transaction Script / Fat Controller / capas / MVC / lo que sea) — no asumas, léelo.
- Repórtame qué patrón encontraste y en qué archivos se nota más (probablemente los routers más grandes).

### Fase 1 — Naming
- Revisa nombres de archivos, servicios y rutas Python. Convención del proyecto: rutas HTTP en inglés, vocabulario de dominio (variables, nombres de archivo Python, docstrings) en español.
- Lista inconsistencias (archivos con nombre en inglés que deberían ir en español según el dominio, o viceversa) y renómbralos. Actualiza todos los imports que dependan de esos nombres.

### Fase 2 — Duplicación y código muerto
- Busca bloques de código duplicados entre endpoints (mismo patrón repetido N veces).
- Busca imports, funciones, constantes y archivos completos sin uso real — confirma con grep en TODO el repo (no solo el servicio) antes de borrar, incluyendo el frontend si el servicio tiene endpoints consumidos por React.
- Si hay 3+ endpoints casi idénticos que solo cambian el modelo/config, evalúa construir un motor genérico config-driven (dataclass de config + funciones `_get_x`/`_post_x`/`_put_x` reutilizadas) en vez de mantener la duplicación. Antes de hacerlo, pregúntame si quiero ese approach o prefiero mantenerlo explícito — no lo asumas.

### Fase 3 — Seguridad
- Audita cada endpoint que reciba un ID de un recurso ajeno al usuario (expediente, documento, etc.): ¿la respuesta distingue "no existe" (404) de "existe pero no es tuyo" (403)? Si sí, es una fuga de información — unifica en una sola consulta combinada que siempre devuelva 403 sin revelar existencia.
- Reporta cualquier otro hallazgo de seguridad que veas de paso (igual que encontramos el scheduler fantasma y los AttributeError en `app-sancionatoria`) pero no arregles nada sin decírmelo primero si es un cambio de comportamiento no trivial.

### Fase 4 — Migraciones y índices obsoletos
- Si hay carpeta `db/migrations` con SQL suelto: revisa si el schema que referencian sigue vigente. Si no, bórrala — pero antes rescata cualquier intención real de índice (columnas que se filtran/ordenan seguido) y agrégala como `Index()`/`index=True` en los modelos SQLAlchemy actuales. Verifica en vivo contra la BD que los índices se crearon.

### Fase 5 — Endpoints legacy y capas de traducción muertas
- Si existe alguna capa de traducción frontend↔backend (mapas de nombres legacy, IDs numéricos viejos, etc.), evalúa si sigue siendo necesaria.
- Antes de borrar cualquier endpoint o mapa "legacy", grep el repo completo (backend + frontend `.tsx`/`.ts`) para confirmar cero llamadas reales. Si el frontend llama con el nombre viejo, actualiza el frontend primero, después borra el backend.

### Fase 6 — Suite de tests (si no existe)
- Si el servicio no tiene tests automatizados, construilos: pytest + pytest-asyncio + httpx `ASGITransport`, contra una base de datos Postgres real y dedicada para tests (no mocks de la sesión async — ya sabemos que sqlalchemy async + mocks da falsos positivos).
- `pytest.ini` con `asyncio_default_fixture_loop_scope = session` y `asyncio_default_test_loop_scope = session` (evita el bug de "Future attached to a different loop").
- Cubre TODOS los endpoints y ramas relevantes, no solo el happy path — casos de permisos (403 sin distinguir existencia), validación (422), y las reglas de negocio no obvias que encuentres en el camino.
- Esta suite es la red de seguridad para las fases 7 y 8. No sigas sin tests pasando.

### Fase 7 — Boilerplate de try/except
- Si hay try/except repetido en cada endpoint para rollback + log + 500 genérico, reemplázalo por una dependency de FastAPI (`get_db_managed` o similar) que envuelve `get_db` — no un decorator, no un exception handler global. Motivo: cero líneas nuevas por ruta y es imposible olvidarla en rutas nuevas.
- Ojo con `RequestValidationError`: FastAPI la lanza DENTRO de esta dependency al fallar la validación de otro parámetro — no debe caer en el `except Exception` genérico o convierte un 422 correcto en 500.
- Verifica con la suite de tests después de convertir cada router.

### Fase 8 — Partir archivos gigantes
- Si algún router pasa ~1000 líneas, divídelo en archivos por subdominio, todos montados con el mismo prefijo (`app.include_router(x.router, prefix="/mismo-prefijo")`) para no tocar ni un solo contrato de URL del frontend.
- Antes de decidir el agrupamiento, pregúntame — en `app-sancionatoria` elegimos 3 y 4 archivos por dominio según el caso, pero no asumas el mismo número acá sin mirar el archivo real.
- Verifica: el archivo viejo se borra solo después de confirmar que main.py importa limpio y los tests siguen en verde.

### Fase 9 — Limpieza de comentarios
- Pasada final sobre todo lo tocado: elimina comentarios que solo repiten la línea de abajo (WHAT), headers de sección vacíos de contenido, docstrings infladas.
- Conserva: comentarios que expliquen una regla de negocio no obvia, un workaround, una restricción oculta, o el motivo de una decisión de diseño.
- Si encontrás un comentario que afirma algo que el código NO hace (docstring desactualizada, TODO viejo, referencia a una validación que ya no existe), corregilo o bórralo — no lo dejes como está solo porque "es un comentario".

### Fase 10 — Verificación final
- Sync todo lo tocado al contenedor Docker (`docker cp`, limpiar `__pycache__`).
- `python -c "import main"` dentro del contenedor para confirmar que arranca.
- Correr la suite completa de tests, confirmar 100% verde.
- Si el rebuild fue completo (`docker compose build` + `up -d` de todo el stack), reiniciá `nginx-lb` al final (`docker compose restart nginx-lb`). Si no se recreó junto con los demás, queda con conexiones/DNS viejos hacia los contenedores que sí se recrearon y tira 502/503 transitorios (ya nos pasó en `app-sancionatoria`).
- Resumen final: qué se tocó, qué bugs reales se encontraron y arreglaron, qué quedó pendiente (si algo).

---

## Reglas fijas para toda la sesión
- Nunca borres código sin confirmar cero referencias (grep completo, backend + frontend).
- Nunca asumas un patrón de agrupamiento/refactor grande sin preguntar primero si hay más de una opción razonable.
- Tests antes que refactor de riesgo (dependency injection, split de archivos) — son la red de seguridad.
- Todo cambio de comportamiento (no solo estilo) se reporta explícitamente, aunque sea chico.
- Verificar siempre contra el contenedor real corriendo, no solo `py_compile` local.
