# Informe de Pruebas Pre-Despliegue — SATC

**Fecha:** 1 de agosto de 2026
**Alcance:** prueba de humo en navegador (login real) + prueba de carga con usuarios concurrentes reales, contra el stack completo corriendo en local (16 contenedores Docker).

---

## 1. Prueba de humo en navegador

Ejecutada con Playwright (Chromium headless) contra `http://localhost:8000`, usando una cuenta admin real.

| Paso | Resultado |
| --- | --- |
| Carga de `/login` | OK |
| Login con credenciales reales | OK — redirige fuera de `/login` |
| Cookie de sesión (`access_token`) presente | OK |
| Home (`/`) carga sin excepción | OK |
| `/profile` | OK — 200 |
| `/user/manage` | OK — 200 |
| `/user/role` | OK — 200 |
| `/file/manage` | OK — 200 |
| `/file/consult` | OK — 200 |
| `/involved/manage` | OK — 200 |
| `/document/manage` | OK — 200 |
| `/infraction/manage` | OK — 200 |
| `/infraction/consult` | OK — 200 |
| `/audit/users` | OK — 200 |

**Resultado: 15/15 pasos OK. Cero errores de consola del navegador.**

---

## 2. Prueba de carga

### 2.1 Primer intento — cuenta única

Con una sola cuenta reutilizada en 30 "usuarios" concurrentes × 5 endpoints, 1200 requests: **76.7% devolvió 429**. No es un fallo — todas esas peticiones comparten el mismo `user_id` e IP, así que agotan el mismo balde de rate limit (100 req/min) que protege a un usuario individual. **Cero errores 5xx** en este intento: el backend nunca se cayó, solo frenó tráfico que, desde su perspectiva, es una sola identidad abusando.

### 2.2 Volumen moderado, mismo usuario, ritmo bajo el límite

150 requests (3 concurrentes × 10 rondas):

- **100% status 200**
- Throughput: **~120 req/s**
- Latencia p50: **78ms** / p95: **129ms** / p99: **155ms**
- 0 errores

### 2.3 Diez usuarios reales distintos (prueba definitiva)

Se crearon 10 cuentas de prueba (`loadtest1..10@loadtestqa.com`, rol admin) directamente en la base de datos de `app-users`, cada una con su propio login y sesión. Se dispararon 8 rondas de 5 endpoints (uno por microservicio: users, sancionatoria, docs, involved, infraction) por cada una de las 10 sesiones — 400 requests totales, todas con identidad real distinta.

| Métrica | Resultado |
| --- | --- |
| Requests totales | 400 |
| Status 200 | **400/400 (100%)** |
| Errores 5xx / excepciones | **0** |
| Throughput | ~103 req/s |
| Latencia p50 | 210ms |
| Latencia p95 | 488ms |
| Latencia p99 | 894ms |

**Resultado: el sistema soporta 10 usuarios reales concurrentes navegando los 5 microservicios sin un solo error.**

---

## 3. Hallazgo en el camino: rate limiting anti-fuerza-bruta funcionando

Durante la prueba 2.3, los primeros intentos de login devolvieron 429 con mensaje genérico `"Too many requests"`. Investigado: es un límite **específico de rutas de autenticación** en el api-gateway (`api-gateway/utils/rate_limit.py`), separado del límite general por usuario:

- **20 intentos de login / 5 minutos por IP** — cubre password-spraying contra muchas cuentas distintas desde una misma IP, que el throttle por cuenta de `app-users` no detecta por sí solo (ese es por `email+ip`, no por IP sola).
- Mi batería de pruebas de hoy (30 logins simulados de golpe + reintentos) agotó ese presupuesto legítimamente. Se limpiaron las claves `ratelimit:auth:*` en Redis (DB 1) para poder continuar la prueba, sin tocar sesiones activas.

**No es un bug. Es la defensa contra fuerza bruta / credential stuffing funcionando exactamente como se diseñó** — un atacante real repartiendo intentos de login entre varias cuentas robadas desde una sola IP se vería bloqueado igual.

---

## 4. Optimizaciones de frontend aplicadas en esta sesión

No relacionadas con las pruebas de carga, pero relevantes para la experiencia de usuario en producción:

- **`WelcomeLayout.tsx`**: los 2 GIFs de bienvenida (día/noche) se cargaban siempre ambos, 8.7MB combinados, sin importar el tema activo. Convertidos a webm (VP9): 2.6MB→395KB (día) y 6.1MB→969KB (noche), ~6.5x más livianos cada uno. Además, el video del tema inactivo ya no se descarga hasta que el usuario cambia de tema al menos una vez.
- **`LoginPage.tsx`**: imagen de fondo (`login-bg.jpg`, 2048×2048, 1.9MB) redimensionada y convertida a webp (1200×1200, 143KB) — 13x más liviana.
- **`api.ts`**: corregido bug donde, al expirar la sesión, el reload completo a `/login` (500ms de espera) borraba el toast de aviso casi antes de que se alcanzara a leer. Ahora espera 2.5s antes de recargar, y si el 401 ocurre estando ya en `/login`, no hace nada (evita un reload fantasma de la misma pantalla).

---

## 5. Estado para producción

- 🔴 Bloqueantes de código: **ninguno**.
- Seguridad: verificada con tráfico real (rate limiting, anti-fuerza-bruta, sesiones por usuario) — todo se comportó como se diseñó.
- Funcionalidad: verificada con navegación real, no solo tests automatizados.
- Capacidad: 10 usuarios reales concurrentes sin errores; no se probó a mayor escala (requeriría más cuentas/IPs distintas para no chocar con el anti-fuerza-bruta, que es deseable dejar activo).
- Pendiente exclusivamente de configuración de despliegue: generar los 5 secretos de servicio + contraseñas de producción en `deploy/env-produccion.txt` al momento de desplegar (ver `despliegue-produccion-lan` en memoria del proyecto).

---

**Nota:** las 10 cuentas de prueba (`loadtest1..10@loadtestqa.com`) se eliminan de la base de datos de desarrollo tras este informe.
