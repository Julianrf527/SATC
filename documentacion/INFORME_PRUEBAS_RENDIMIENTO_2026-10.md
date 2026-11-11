# Informe de Pruebas de Rendimiento y Consumo de Recursos — SATC

**Sistema:** SATC — Sistema de Administración de Trámites de Corpochivor
**Fecha de las pruebas:** 19 de octubre de 2026 (hora local de Colombia, UTC−5)
**Rama evaluada:** `feat/app-recurso` (commit `e46db4a`, el desplegado en producción el 16/10/2026)
**Alcance:** consumo de recursos tras la redistribución de límites de memoria del 16/10/2026, pruebas de carga y concurrencia en el entorno local, optimización del cálculo de alertas y suites automatizadas.

---

## Resumen ejecutivo

- **Producción se midió hoy en modo de solo lectura** (sección 3): 30 muestras de `docker stats` cada 30 s entre las 13:06 y las 13:21, más `free -m`, `docker inspect` y los contadores del cgroup de cada contenedor. Los **19 contenedores están *healthy*, con 0 reinicios y 0 eventos OOM** desde el despliegue del 16/10. Los servicios a los que se les bajó el límite están holgados: gateway al 40 %, `app-users` al 62 % y nginx al 14 %. `app-docs`, al que se le subió, está al 41 %. La RAM disponible es de 2,3 GB y la swap se mantiene estable en 1,47 GB, sin intercambio activo.
- **Con los límites nuevos, en local ningún servicio se reinició ni fue detenido por falta de memoria** durante la carga (de 1 a 50 usuarios simultáneos): 0 reinicios, 0 eventos OOM y todos los contenedores quedaron *healthy*.
- **Con 50 usuarios simultáneos, el 100 % de las 550 peticiones respondió bien** (0 errores). La mitad de las peticiones respondió en menos de 0,2 s y el 95 % en menos de 0,81 s. Lo más lento es la descarga del expediente completo en PDF: mediana de 0,74 s y máximo de 5,4 s.
- **Alertas mucho más rápidas.** Con 2.000 expedientes, en sancionatorio la pestaña pasó de 46,7 s a 1,06 s (de 37.698 consultas a la base de datos a 11). En infracciones pasó de 4,2 s a 0,12 s (de 6.668 consultas a 5). Con paginación, la página que se envía al navegador ocupa unos 6 KB en lugar de 4,6 MB.
- **Riesgos detectados (detalle en la sección 8):**
  1. **Bajo carga local, la base de datos de Concesiones (`postgres-recurso`) quedó prácticamente sin margen.** Con 50 usuarios llegó al 93,8 % de su límite de 200 MiB, tocó el tope 5 veces y siguió al 91 % después de terminar la prueba. La causa son las conexiones que el servicio mantiene abiertas (37 a 42). En producción, con el uso real de hoy, está en el 21,5 % (43 MiB, 5 conexiones, pico de 116 MiB desde el 16/10). Es un riesgo preventivo: aparecería si crece la concurrencia en Concesiones.
  2. **El servicio de Concesiones (`app-recurso`) llegó al 84 %** de su límite de 450 MiB y se quedó en el 81 % en reposo, después de la carga.
  3. **El servicio de documentos (`app-docs`) llega a su tope de CPU** (0,5 núcleos), y eso explica la lentitud de la descarga del PDF.
  4. **`app-involved` (límite de 256 MiB en la VM) es el servicio de producción con menos margen.** Hoy usa 169 MiB (66 %), pero su cgroup registra un pico de 256 MiB y **242 eventos de tope** desde el 16/10. Ninguno terminó en OOM: el kernel liberó caché. Conviene subirlo a 384 MiB, como en el compose local.

---

## 1. Objetivo y alcance

1. Comprobar que los límites de memoria redistribuidos el 16/10/2026 dejan margen suficiente a cada servicio, en producción (solo observación) y en local bajo carga.
2. Medir la latencia, la tasa de errores y el throughput de los endpoints más usados con concurrencia creciente (1, 10, 25 y 50 usuarios).
3. Volver a medir, antes y después, la optimización del cálculo de alertas.
4. Ejecutar las suites automatizadas de los servicios y del frontend.

Fuera de alcance: pruebas de carga contra producción (prohibidas expresamente) y cambios de configuración o de reglas de negocio.

---

## 2. Entornos y metodología

### 2.1 Entornos

| Entorno | Descripción | Uso en este informe |
| --- | --- | --- |
| Producción | VM 192.168.254.222: 4 CPU, 5.931 MiB de RAM y 4.095 MiB de swap. Compose propio en `~/satc-deploy`. Encendida hace 25 días; los servicios actualizados corren desde el despliegue del 16/10. | **Solo observación** (lecturas por SSH, 19/10 de 12:49 a 13:21). No se generó carga ni se cambió configuración. |
| Local | Docker Desktop 29.8.2 en Windows 11 Pro. 16 CPU y 15,6 GiB asignados a Docker. 19 contenedores con los límites de `docker-compose.yml`. | Carga, concurrencia y consumo de recursos. |
| BD de pruebas | PostgreSQL portable en 127.0.0.1:55432 (BD `*_test_db`). | Benchmark de alertas y suites automatizadas. |

**Datos en la BD local durante la carga:** 75 expedientes de Concesiones, 1 de sancionatorio, 0 de infracciones y 92 involucrados. Por el bajo volumen de sancionatorio e infracciones, la carga mide sobre todo el costo de la cadena nginx → gateway → servicio → BD con listados pequeños. El efecto del volumen real se mide aparte, en el benchmark de alertas con 2.000 expedientes sintéticos (sección 6).

### 2.2 Herramientas (scripts en la carpeta temporal de la sesión)

Carpeta: `C:\Users\julia\AppData\Local\Temp\claude\c--Users-julia-Escritorio-SATC\55e567c5-80ff-45c2-9776-85db605c9193\scratchpad\pruebas-rendimiento\`

| Script | Función |
| --- | --- |
| `carga.py` | Generador de carga (Python 3, `httpx` + `asyncio`) contra `http://localhost:8000`. |
| `muestreo_stats.py` | Muestra `docker stats --no-stream` en bucle (cada 2 s en la práctica, local o por SSH) y lo guarda en CSV. |
| `analizar_stats.py` | Calcula promedio y máximo por contenedor y por ventana de tiempo. |
| `..\bench_alertas.py` | Benchmark de alertas (ya existía; mediciones del 15/10). |
| `setup.sql` / `cleanup.sql` | Crean y borran los usuarios temporales de la prueba. |
| `resultados\` | Datos crudos: CSV de `docker stats`, JSON de la carga y salidas del benchmark y de las suites. |

### 2.3 Cómo se hizo la carga

- **Usuarios de prueba:** se crearon 50 cuentas temporales (`carga01..carga50.temporal@prueba.example.com`) con un rol temporal de **solo lectura**: consultar y ver alertas de sancionatorio e infracciones, y consultar Concesiones. Usan la misma contraseña de las cuentas de prueba de Concesiones. **Al terminar se eliminaron** junto con sus 132 registros de auditoría de login y sus sesiones en Redis. Los conteos de las tablas de auditoría, usuarios y notificaciones quedaron **idénticos a los iniciales** (verificado a las 11:25). La carga solo hizo lecturas.
- **Se respetaron los límites anti-abuso tal como están configurados.** No se limpiaron contadores ni se simularon otras IP. Como todas las peticiones salen de una sola IP, aplican:
  - gateway: 600 peticiones/min por IP, 300/min por usuario y 20 logins cada 5 min por IP;
  - `app-users`: 10 logins/min por IP y una sola sesión vigente por usuario.

  Por eso los niveles de concurrencia se hicieron en **rondas**: los N usuarios piden a la vez (N peticiones simultáneas en curso) y entre ronda y ronda se espera lo necesario para no pasar de unas 9 peticiones/s en promedio. **Así se mide la concurrencia, no el throughput máximo.** El throughput que se reporta está limitado a propósito por el rate limit.
- **Transparencia:** hubo un primer intento (11:06–11:10) en el que un script borraba los contadores de rate limit del Redis **local** para medir la capacidad sin el limitador. La política de seguridad del entorno bloqueó ese método, así que se detuvo, se descartaron sus resultados y no se usan en este informe.
- **Mezcla de endpoints** (cada usuario va rotando):

| Clave | Endpoint |
| --- | --- |
| `lista_sancionatorio` | `GET /sanctioning/expediente/get/all` |
| `lista_infracciones` | `GET /infraction/expedientes/todos` |
| `lista_concesiones` | `GET /recurso/expedientes?page=1&limit=10` |
| `detalle_concesion` | `GET /recurso/expedientes/{id}` (id al azar entre los 75) |
| `alertas_sancionatorio` | `GET /sanctioning/expediente/alerts/all?alcance=todos&page=1&limit=10` |
| `alertas_infracciones` | `GET /infraction/expedientes/alertas/todas?alcance=todos&page=1&limit=10` |
| `mis_informes_concesiones` | `GET /recurso/mis-documentos?page=1&limit=20` |
| `descarga_expediente_pdf` | `GET /recurso/expedientes/{id}/descargar`: une los PDF en `app-docs`. Usa 15 expedientes con 1 a 16 documentos; el más grande pesa 464.683 bytes. |

- **Login:** se midió aparte: 3 logins secuenciales, una ráfaga de 10 usuarios distintos y una ráfaga de 25 usuarios distintos (esta última para documentar el límite por IP).
- **Consumo:** `docker stats` se muestreó durante toda la prueba (11:11:34–11:23:59, 357 muestras). Además, se leyeron `memory.peak` y `memory.events` del cgroup de cada contenedor y `docker inspect` (reinicios, OOMKilled, salud) antes y después.

---

## 3. Consumo de recursos en producción (19/10/2026, solo lectura)

### 3.1 Cómo se midió

- **Entre las 12:49 y las 13:21 se hicieron solo lecturas por SSH** (`administrador@192.168.254.222`, sin contraseña, con `BatchMode`). No se generó carga, no se reinició nada y no se cambió configuración.
- **`docker stats --no-stream` cada 30 s durante 15 minutos.** Son 30 muestras, de 13:06:14 a 13:20:44, de los 19 contenedores (`resultados\prod_19-10.csv`).
- **Estado del sistema al inicio (12:49) y al final (13:21).** Se tomaron `free -m`, `uptime` y `vmstat`, más `docker inspect` (límite y reserva efectivos, reinicios, OOMKilled y salud).
- **Contadores del cgroup de cada contenedor.** `memory.peak` es el pico desde que arrancó el contenedor, `memory.events` cuenta las veces que tocó el tope y las muertes por OOM, y `memory.stat` separa la memoria de procesos (anónima) de la caché de archivos. Para los servicios actualizados, el período cubierto va del 16/10 al 19/10.
- **Conexiones activas de `postgres-recurso`,** leídas de `pg_stat_activity`.
- **Un primer intento de muestreo (12:49–13:04) salió vacío y se descartó.** En Windows, las comillas del formato de `docker stats` se perdían al pasar el comando por `ssh`. Se corrigió `muestreo_stats.py` para enviar el comando remoto como una sola cadena y se repitieron los 15 minutos completos.
- **Uso del sistema durante la medición:** fue horario laboral, con uso normal de los funcionarios. Hubo picos de CPU de ~45 % en los servicios de negocio, que corresponden a peticiones reales.

### 3.2 Estado general de la VM

| Indicador | 12:49 | 13:21 | Lectura |
| --- | --- | --- | --- |
| RAM usada / total | 3.665 / 5.931 MiB | 3.642 / 5.931 MiB | Estable |
| RAM disponible (incluye caché liberable) | 2.266 MiB | 2.289 MiB | ~38 % de la RAM libre para crecer |
| Swap usada | 1.470 / 4.095 MiB | 1.470 / 4.095 MiB | Igual que el 16/10 (~1,4 GB) y sin cambios en la medición |
| Intercambio activo (`vmstat` si/so) | 0–56 KB/s / 0 | — | Son páginas antiguas: la VM no está paginando |
| Carga media (1/5/15 min, 4 CPU) | 0,76 / 0,85 / 0,95 | 2,10 / 1,66 / 1,38 | Entre el 20 % y el 50 % de la capacidad |
| Contenedores *healthy* | 19 / 19 | 19 / 19 | — |
| Reinicios / OOMKilled | 0 / 0 | 0 / 0 | En todos los contenedores |
| `oom_kill` en el cgroup | 0 | — | En todos los contenedores, desde que arrancaron |

La suma de memoria de los 19 contenedores fue de **2.364 MiB en promedio y 2.401 MiB como máximo**. En el entorno local en reposo, con los mismos límites, la suma fue de 2.852 MiB.

### 3.3 Consumo por servicio frente a su límite

`docker inspect` confirma los límites aplicados el 16/10. La suma de límites es de **5.784 MiB** y la de reservas de 2.867 MiB.

| Servicio | Límite | Uso prom. | Uso máx. | % máx. del límite | Pico del cgroup desde el arranque | Topes alcanzados (`max`) | CPU prom. / máx. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| api-gateway | 384 MiB | 154,8 | 155,2 | **40,4 %** | 206 MiB | 0 | 1,7 % / 7,0 % |
| app-users | 450 MiB | 279,6 | 280,1 | **62,2 %** | 316 MiB | 0 | 1,7 % / 6,7 % |
| nginx-lb | 64 MiB | 8,4 | 9,0 | **14,0 %** | 12 MiB | 0 | 0,7 % / 4,9 % |
| app-docs | 256 MiB | 93,3 | 105,3 | **41,1 %** | 162 MiB | 0 | 4,7 % / 46,8 % |
| minio | 256 MiB | 105,4 | 105,9 | **41,4 %** | 163 MiB | 0 | 0,1 % / 0,4 % |
| app-recurso | 450 MiB | 276,3 | 288,7 | 64,2 % | 344 MiB | 0 | 6,1 % / 43,7 % |
| app-sanctioning | 450 MiB | 270,7 | 283,4 | 63,0 % | 340 MiB | 0 | 5,9 % / 41,4 % |
| app-infraction | 450 MiB | 273,1 | 286,2 | 63,6 % | 353 MiB | 0 | 6,3 % / 43,3 % |
| **app-involved** | **256 MiB** | 168,4 | 169,0 | 66,0 % | **256 MiB (tope)** | **242** | 6,5 % / 44,4 % |
| postgres-recurso | 200 MiB | 42,9 | 43,1 | 21,5 % | 116 MiB | 0 | 0,0 % / 0,1 % |
| postgres-users | 200 MiB | 31,8 | 32,2 | 16,1 % | 59 MiB | 0 | 1,3 % / 7,4 % |
| postgres-infraction | 200 MiB | 32,9 | 33,4 | 16,7 % | 61 MiB | 0 | 0,7 % / 5,4 % |
| postgres-sanctioning | 128 MiB | 35,5 | 35,9 | 28,0 % | 59 MiB | 0 | 0,5 % / 5,1 % |
| postgres-docs | 96 MiB | 24,6 | 26,0 | 27,1 % | 39 MiB | 0 | 0,6 % / 5,6 % |
| postgres-involved | 96 MiB | 25,6 | 27,5 | 28,6 % | 40 MiB | 0 | 0,5 % / 5,5 % |
| redis | 256 MiB | 14,4 | 14,9 | 5,8 % | 37 MiB | 0 | 2,0 % / 6,0 % |
| clamav | 1.400 MiB | 514,0 | 516,3 | 36,9 % | 1.400 MiB | 83.047 | 1,4 % / 4,8 % |
| frontend | 64 MiB | 6,6 | 6,6 | 10,2 % | 11 MiB | 0 | 0,0 % |
| backup-service | 128 MiB | 6,2 | 6,2 | 4,8 % | 128 MiB | 344.619 | 0,0 % |

Las filas en negrilla del % son los cinco servicios cuyos límites se redistribuyeron el 16/10.

**Cómo leer los topes (`max`):** el contador registra las veces que el contenedor llegó a su límite y el kernel tuvo que recuperar memoria. Ningún tope terminó en OOM (`oom_kill = 0` en todos los contenedores).

- **ClamAV y backup-service** llegan al tope por la caché de disco, que el kernel libera sin afectar al servicio. En backup-service la memoria de procesos es de 0,1 MiB y el resto es caché de los volcados de BD. En ClamAV son 447 MiB de procesos frente a un tope de 1.400 MiB. Las dos cosas son normales.
- **`app-involved` es distinto.** Su memoria de procesos actual es de 141 MiB, pero el servicio llegó a su tope de 256 MiB 242 veces desde el 16/10. Es el único servicio de negocio que lo hizo, y coincide con lo medido en local (256–272 MiB en reposo y con carga). Es el servicio de producción con menos margen.

**`postgres-recurso`:** está en 43 MiB, con 5 conexiones (1 activa y 4 en espera). Su pico desde el 16/10 es de 116 MiB, el 58 % del límite, sin topes. Con el uso real de hoy no hay riesgo. El 93,8 % de la sección 5.5 aparece solo con 50 usuarios simultáneos en Concesiones, porque el *pool* abre muchas más conexiones.

### 3.4 Comparación con el 16/10 (antes de la redistribución)

| Servicio | Límite antes | Uso 16/10 | % con el límite anterior | Límite ahora | Uso 19/10 (máx.) | % con el límite nuevo |
| --- | --- | --- | --- | --- | --- | --- |
| api-gateway | 900 MB | ~192 MB | ~21 % | 384 MiB | 155,2 MiB | 40,4 % |
| app-users | 600 MB | ~302 MB | ~50 % | 450 MiB | 280,1 MiB | 62,2 % |
| nginx-lb | 128 MB | ~7 MB | ~5 % | 64 MiB | 9,0 MiB | 14,0 % |
| app-docs | 128 MB | ~98 MB | **~76 %** | 256 MiB | 105,3 MiB | 41,1 % |
| minio | 192 MB | ~97 MB | ~51 % | 256 MiB | 105,9 MiB | 41,4 % |

**Suma de límites de memoria frente a la RAM física:**

| Configuración | Suma de límites | Suma de reservas | Comparación con 5.931 MiB de RAM |
| --- | --- | --- | --- |
| Compose de la VM antes del 16/10 (17 servicios) | 5.672 MB | 2.736 MB | Por debajo, pero sin Concesiones |
| Lo anterior + `app-recurso` (450) + `postgres-recurso` (200), sin redistribuir | 6.322 MB | — | **Superaba la RAM física** |
| Compose de la VM desde el 16/10 (19 servicios, confirmado hoy con `docker inspect`) | 5.784 MiB | 2.867 MiB | Por debajo de la RAM |

**Resultado:** con la redistribución, Concesiones entró en la VM con dos contenedores más, y la suma de límites quedó por debajo de la RAM física. El consumo real es de ~2,4 GB y quedan 2,3 GB disponibles. La swap no creció después del despliegue.

---

## 4. Análisis de la redistribución de recursos (16/10/2026)

| Servicio | Antes | Ahora | Justificación (dato del 16/10) | Producción 19/10 (máx. en 15 min) | Local con 50 usuarios (máx. `docker stats`) |
| --- | --- | --- | --- | --- | --- |
| api-gateway | 900 MB (reserva 450) | 384 MB (reserva 256) | Usaba ~192 MB (21 % del límite anterior) | 155,2 MiB (40,4 %) | 249,0 MiB (64,9 %). Margen mínimo de 135 MiB. Correcto. |
| app-users | 600 MB | 450 MB | Usaba ~302 MB | 280,1 MiB (62,2 %) | 264,3 MiB (58,7 %), con ráfagas de login incluidas. Correcto. |
| nginx-lb | 128 MB | 64 MB | Usaba ~7 MB | 9,0 MiB (14,0 %) | 27,1 MiB (42,3 %). Correcto. |
| app-docs | 128 MB | 256 MB | Usaba ~98 MB = 76 % del límite anterior. Sube y une PDF. | 105,3 MiB (41,1 %) | 144,9 MiB (56,6 %) con 50 usuarios descargando PDF. Con el límite anterior de 128 MB **se habría pasado del tope**. La subida era necesaria. |
| minio | 192 MB | 256 MB | Usaba ~97 MB | 105,9 MiB (41,4 %) | 76,1 MiB (29,7 %). Correcto. |
| clamav | 1400 MB | 1400 MB | Necesita el pico de recarga de firmas | 516,3 MiB (36,9 %); cgroup en el tope por caché, 0 OOM | 1.052,7 MiB en `docker stats`. El cgroup llegó a 1.400 MiB y tocó el tope 1.918 veces (recupera caché de disco) sin ningún OOM. Confirma que no se debe bajar. |
| app-recurso (nuevo) | — | 450 MB | Servicio nuevo | 288,7 MiB (64,2 %) | 377,9 MiB (84,0 %). **Margen de 72 MiB** (sección 8). |
| postgres-recurso (nuevo) | — | 200 MB | Servicio nuevo | 43,1 MiB (21,5 %); pico de 116 MiB desde el 16/10 | 187,6 MiB (93,8 %). **Margen de 12 MiB** (sección 8). |

**Conclusión de la redistribución:** lo medido respalda las reducciones (gateway, users y nginx) y la subida de app-docs. En producción, ninguno de esos servicios pasa del 62,2 % de su nuevo límite, y en local, con 50 usuarios, ninguno pasó del 65 %. Los dos contenedores nuevos de Concesiones están holgados en producción (64 % y 21,5 %), pero son los que quedan con menos margen bajo carga alta.

---

## 5. Resultados de carga y estrés en local (19/10/2026)

### 5.1 Línea base en reposo (11:00:12–11:03:08, 36 muestras)

Suma de memoria de los 19 contenedores: promedio de 2.852,0 MiB y máximo de 2.914,2 MiB. Algunos valores locales en reposo son distintos de los de producción (por ejemplo, nginx-lb usa 22 MiB en local frente a ~7 MB en la VM; app-docs, 115,7 MiB frente a ~98 MB), así que **los valores locales sirven para ver tendencias y no se pueden trasladar tal cual a producción**.

### 5.2 Login (concurrencia)

| Prueba | Inicio | Peticiones | Éxitos (200) | Rechazos 429 | p50 | p95 | Máx. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 usuario, 3 logins secuenciales | 11:11:35 | 3 | 3 | 0 | 101,7 ms | 119,0 ms | 120,9 ms |
| Ráfaga de 10 usuarios distintos a la vez | 11:12:46 | 10 | 10 | 0 | 233,9 ms | 327,6 ms | 334,9 ms |
| Ráfaga de 25 usuarios distintos a la vez | 11:13:57 | 25 | 7 | 18 | 80,4 ms | 256,2 ms | 264,9 ms |

El 429 de la ráfaga de 25 **es la protección anti fuerza bruta, no un fallo**: desde la misma IP ya se habían hecho 13 logins en esos 5 minutos, y el gateway admite 20 por IP cada 5 minutos (13 + 7 = 20). En producción (LAN) cada funcionario entra desde su propio equipo, con su propia IP. Ese límite solo afectaría si muchos usuarios salieran por una misma IP (NAT o proxy).

### 5.3 Navegación: resultados globales por nivel

| Usuarios simultáneos | Ventana | Peticiones | Errores | Peticiones/s | p50 | p95 | p99 | Máx. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 11:15:06–11:16:06 | 363 | 63 (17,36 %, todos 429) | 6,05 | 14,4 ms | 99,6 ms | 2.288,2 ms | 2.630,8 ms |
| 10 | 11:17:11–11:18:12 | 470 | **0** | 7,78 | 50,9 ms | 227,7 ms | 1.415,4 ms | 4.960,3 ms |
| 25 | 11:19:17–11:20:19 | 550 | **0** | 8,85 | 78,3 ms | 289,2 ms | 1.247,7 ms | 3.279,7 ms |
| 50 | 11:21:24–11:22:25 | 550 | **0** | 8,98 | 198,5 ms | 810,3 ms | 3.130,3 ms | 5.391,3 ms |

- Con **1 usuario** el script pidió sin pausa (363 peticiones en un minuto). El gateway cortó en exactamente **300 respuestas correctas**, que es el límite de 300 peticiones/min por usuario. Los 63 rechazos son ese límite, no errores del sistema. Un usuario real no se acerca a ese ritmo.
- Entre 10 y 50 usuarios no hubo ningún error 5xx, *timeout* ni 429.
- Los percentiles altos (p99 y máximo) los marca casi por completo la descarga del PDF (sección 5.4).

### 5.4 Latencia por endpoint con 50 usuarios simultáneos (11:21:24–11:22:25)

| Endpoint | Peticiones | Errores | p50 | p95 | p99 | Máx. | Tamaño medio de la respuesta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lista sancionatorio | 69 | 0 | 153,8 ms | 225,8 ms | 255,0 ms | 268,7 ms | 329 B |
| Lista infracciones | 70 | 0 | 161,2 ms | 224,2 ms | 237,1 ms | 238,9 ms | 21 B |
| Lista concesiones (10/página) | 70 | 0 | 257,7 ms | 401,7 ms | 411,7 ms | 417,5 ms | 5.679 B |
| Detalle de concesión | 69 | 0 | 310,3 ms | 432,1 ms | 495,3 ms | 530,0 ms | 12.935 B |
| Alertas sancionatorio (todos, paginado) | 68 | 0 | 154,8 ms | 221,6 ms | 237,5 ms | 244,7 ms | 781 B |
| Alertas infracciones (todos, paginado) | 68 | 0 | 161,9 ms | 218,4 ms | 227,5 ms | 239,8 ms | 231 B |
| Mis informes (Concesiones) | 68 | 0 | 202,2 ms | 361,6 ms | 406,8 ms | 410,9 ms | 1.569 B |
| Descarga del expediente completo (PDF) | 68 | 0 | 736,6 ms | 3.460,0 ms | 5.359,6 ms | 5.391,3 ms | 57.382 B |

**Descarga del PDF (p95) según el nivel:** 2.415,7 ms con 1 usuario, 2.435,4 ms con 10, 2.189,5 ms con 25 y 3.460,0 ms con 50. Ya es lenta con un solo usuario. Coincide con que `app-docs` (1 worker, límite de 0,5 CPU) marcó un máximo de CPU de 51,7–52,0 % en todos los niveles, es decir, **trabaja pegado a su cuota de CPU** cuando une PDF. Su memoria, en cambio, sobra (máximo del 56,6 %).

### 5.5 Consumo de los contenedores durante la carga (`docker stats`)

Memoria máxima muestreada por nivel (MiB) y % del límite en el nivel de 50 usuarios:

| Contenedor | Límite | Reposo (prom.) | 1 usuario | 10 | 25 | 50 | % máx. con 50 | Margen mínimo con 50 | CPU máx. con 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api-gateway | 384 | 158,6 | 186,8 | 214,1 | 223,0 | 239,8 | 62,5 % | 144,2 | 29,1 % |
| app-users | 450 | 206,6 | 238,6 | 260,9 | 251,0 | 264,3 | 58,7 % | 185,7 | 21,2 % |
| app-sancionatoria | 450 | 226,9 | 244,4 | 267,4 | 293,6 | 311,6 | 69,2 % | 138,4 | 31,9 % |
| app-infraction | 450 | 228,3 | 257,6 | 284,7 | 297,3 | 306,5 | 68,1 % | 143,5 | 28,4 % |
| **app-recurso** | 450 | 234,4 | 247,2 | 315,3 | 355,3 | 374,1 | **83,1 %** | **75,9** | 86,2 % |
| app-docs | 256 | 115,7 | 125,5 | 128,0 | 144,0 | 144,9 | 56,6 % | 111,1 | 51,7 % (cuota de 50 %) |
| app-involved | 384 (VM: 256) | 256,4 | 266,7 | 266,5 | 259,5 | 272,4 | 70,9 % (106 % sobre 256) | 111,6 | 23,0 % |
| nginx-lb | 64 | 22,0 | 24,4 | 24,1 | 24,2 | 24,1 | 37,7 % | 39,9 | 6,0 % |
| minio | 256 | 72,2 | 76,1 | 73,8 | 74,8 | 73,4 | 28,7 % | 182,6 | 6,7 % |
| redis | 256 | 9,2 | 14,4 | 14,4 | 10,7 | 11,2 | 4,4 % | 244,8 | 4,5 % |
| clamav | 1400 | 1.050,8 | 1.051,6 | 1.050,6 | 1.050,6 | 1.052,7 | 75,2 % | 347,1 | 2,1 % |
| **postgres-recurso** | 200 | 42,8 | 43,7 | 77,2 | 120,1 | 187,6 | **93,8 %** | **12,4** | 15,0 % |
| postgres-infraction | 200 | 40,8 | 41,1 | 47,0 | 49,0 | 76,5 | 38,3 % | 123,5 | 4,0 % |
| postgres-sanctioning | 128 | 42,0 | 42,6 | 49,9 | 56,0 | 66,6 | 52,0 % | 61,4 | 4,1 % |
| postgres-users | 200 | 59,0 | 78,3 | 84,1 | 89,4 | 90,8 | 45,4 % | 109,2 | 4,1 % |
| postgres-docs | 96 | 33,4 | 33,8 | 36,4 | 39,9 | 42,9 | 44,7 % | 53,1 | 3,8 % |
| postgres-involved | 96 | 32,1 | 33,6 | 36,9 | 37,5 | 42,3 | 44,1 % | 53,7 | 4,2 % |
| frontend | 64 | 15,0 | — | — | — | — | 26,3 % (máx. en toda la prueba) | 47,2 | 3,2 % |
| backup-service | 128 | 5,9 | — | — | — | — | 8,1 % (máx. en toda la prueba) | 117,7 | 27,9 % |

En `docker stats`, el % de CPU es sobre un núcleo. La suma de memoria de todos los contenedores fue de 3.474,9 MiB de promedio y 3.535,6 MiB de máximo con 50 usuarios, frente a 2.852,0 MiB en reposo.

**Datos del cgroup (11:24:12):**

- `restarts=0` y `OOMKilled=false` en los 19 contenedores; todos *healthy*.
- `memory.events`: `oom_kill 0` en todos los contenedores.
- `postgres-recurso`: `max 5`, es decir, **tocó su tope de 200 MiB cinco veces** y el kernel tuvo que liberar memoria. `memory.peak` = 200 MiB. Desglose: 150,2 MiB de memoria anónima (de procesos, no liberable) y 31,8 MiB de caché de archivos.
- `clamav`: `max 1918` (vive en su tope liberando caché de disco), sin OOM.
- `memory.peak` (incluye caché y abarca desde el arranque a las 10:50): app-recurso 448 MiB, app-sancionatoria 405, app-infraction 387, app-involved 353, app-users 341, api-gateway 296 y app-docs 236. Ninguno registró eventos `max`.

**Después de la carga (11:26:18–11:27:12, en reposo):** la memoria no vuelve a la línea base. `app-recurso` se queda en 363,6 MiB (80,8 %) y `postgres-recurso` en 182,3 MiB (91,1 %) con **37 conexiones abiertas en reposo** que mantiene el *pool* de `app-recurso`.

---

## 6. Optimización de alertas (antes / después)

**Medición del 19/10/2026, de 10:59:38 a 11:04:43.** Script `bench_alertas.py` sobre las BD de pruebas `sancionatoria_test_db` e `infraction_test_db`, con datos sintéticos (siembra fija por N). Llama al endpoint completo en proceso (sin red), `alcance=todos`, y simula una latencia de LAN de 5 ms por llamada a `app-involved`. "Antes" es el commit `bccdef5` (anterior a la optimización), ejecutado en un *worktree* temporal que ya se eliminó; "después" es el commit actual `e46db4a`. Se reporta el mínimo de 3 ejecuciones y, entre paréntesis, la mediana.

### Sancionatorio

| Expedientes | Antes: tiempo | Antes: consultas SQL | Antes: llamadas a involved | Después: tiempo | Después: consultas | Después: llamadas | Después paginado (10/página) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 2,263 s (2,369) | 1.883 | 100 | 0,059 s (0,062) | 11 | 1 | 0,060 s |
| 500 | 10,954 s (11,833) | 9.423 | 500 | 0,264 s (0,296) | 11 | 1 | 0,270 s |
| 2.000 | **46,731 s** (46,827) | **37.698** | 2.000 | **1,059 s** (1,083) | **11** | 1 | **1,045 s** |

### Infracciones

| Expedientes | Antes: tiempo | Antes: consultas | Después: tiempo | Después: consultas | Después paginado |
| --- | --- | --- | --- | --- | --- |
| 100 | 0,177 s (0,178) | 335 | 0,009 s (0,009) | 5 | 0,007 s |
| 500 | 0,962 s (0,993) | 1.668 | 0,025 s (0,026) | 5 | 0,024 s |
| 2.000 | **4,215 s** (4,355) | **6.668** | **0,120 s** (0,120) | **5** | **0,082 s** |

- **El resultado es idéntico antes y después:** con N = 2.000 se calcularon 8.215 alertas en sancionatorio y 3.334 en infracciones, con respuestas de exactamente el mismo tamaño (4.579.673 y 1.975.260 bytes).
- **La paginación reduce lo que se envía al navegador** de 4.579.673 bytes a 6.263 bytes por página en sancionatorio, y de 1.975.260 a 6.439 bytes en infracciones.
- **Consistencia con la medición anterior** (15/10, misma herramienta): sancionatorio pasó de ~42 s a ~0,8 s e infracciones de ~3,5 s a ~0,09 s. Hoy los tiempos absolutos salieron algo mayores (46,7 s → 1,06 s y 4,2 s → 0,12 s), pero la mejora es del mismo orden: unas 44 veces en sancionatorio y unas 35 veces en infracciones. El número de consultas coincide exactamente (37.698 → 11).

---

## 7. Suites automatizadas (19/10/2026, de 11:25:21 a 11:31:55)

| Suite | Resultado | Duración |
| --- | --- | --- |
| app-infraction (`infraction_test_db`) | **240 pasan** | 144,9 s |
| app-sancionatoria (`sancionatoria_test_db`) | **166 pasan** | 78,6 s |
| shared | **45 pasan** | 1,0 s |
| frontend (vitest, configuración unitaria) | **122 pruebas pasan, en 17 archivos** | 1,6 s |
| app-recurso (`recurso_test_db`) | 76 pasan, 72 fallan — **no válida: falló el entorno** | 102,0 s |
| app-users (`users_test_db`) | 77 pasan, 14 fallan, 8 con error — **no válida: falló el entorno** | 25,6 s |

Las suites de app-recurso y app-users **no indican defectos del código**. Al repetir app-recurso con `-x`, el primer fallo fue un error 500 producido por la base de datos de pruebas: `could not open file "base/16388/6104": No such file or directory`. La consulta directa al catálogo del PostgreSQL portable también falló (`could not open file "base/5/2686"` y `global/6100`). **Al clúster PostgreSQL portable le faltan archivos de datos**, probablemente porque se borraron de la carpeta temporal de Windows (`AppData\Local\Temp`), donde está guardado. Las BD de infracciones y sancionatorio sí funcionaron porque el benchmark acababa de reescribir sus tablas.

Se intentó crear un clúster nuevo para repetir estas dos suites, pero la política de seguridad del entorno bloqueó la operación y no se insistió. El clúster quedó **detenido limpiamente** (11:34:18) y sin modificar. **Pendiente:** recrear la BD de pruebas (de preferencia fuera de `AppData\Local\Temp`) y volver a ejecutar las suites de app-recurso y app-users.

---

## 8. Hallazgos y riesgos

| # | Hallazgo | Severidad | Evidencia |
| --- | --- | --- | --- |
| 1 | **Bajo carga alta, `postgres-recurso` (límite 200 MiB) queda casi sin margen.** En producción hoy está en el 21,5 % (pico de 116 MiB desde el 16/10). En local llegó al 93,8 % con 50 usuarios, tocó el tope 5 veces y siguió al 91 % en reposo después. Lo que ocupa es memoria de procesos (150 MiB anónimos), no caché. Si suben las conexiones, el kernel puede matar un proceso de PostgreSQL por falta de memoria (OOM), y entonces PostgreSQL reinicia todas las conexiones del servicio de Concesiones. | **Alta en carga alta / baja con el uso actual** (preventivo) | Secciones 3.3 y 5.5 |
| 2 | **La causa probable del hallazgo 1 es el *pool* de conexiones de `app-recurso`**: `pool_size=10` y `max_overflow=30` por worker, con 4 workers, es decir, hasta 40 conexiones fijas y 160 en picos. En PostgreSQL, `max_connections=250`. Hubo entre 37 y 42 conexiones abiertas en reposo después de la carga, frente a 21 en `postgres-infraction`, que usa el mismo *pool*. Que Concesiones abra más conexiones podría deberse a que mantiene la sesión de BD abierta mientras llama a otros servicios (`app-docs` o `app-involved`). Esto no se verificó en el código. | Alta (es la causa del 1) | `app-recurso/db/database.py`, `pg_stat_activity` |
| 3 | **`app-recurso` llegó al 84 % de 450 MiB** y se quedó en el 81 % en reposo. El pico del cgroup desde el arranque fue de 448 MiB, aunque incluye caché y no hubo eventos `max`. | Media | Sección 5.5 |
| 4 | **Confirmado en producción: `app-involved` (256 MiB en la VM, 384 MiB en local) trabaja en su tope.** Hoy usa 169 MiB (66 %), pero su cgroup registra un pico de 256 MiB y 242 eventos de tope desde el 16/10, sin OOM. Es el único servicio de negocio que llegó a su límite. | **Media-alta** | Sección 3.3, `memory.events` |
| 5 | **`app-docs` llega a su tope de CPU (0,5 núcleos)** al unir PDF. La descarga del expediente completo tarda 2,4 s en p95 con un solo usuario y 3,5 s con 50. La memoria va bien (56,6 %). | Media (afecta la experiencia, no la estabilidad) | Sección 5.4 |
| 6 | **La suma de límites (5.784 MiB) está cerca de la RAM de la VM (5.931 MiB).** El consumo real es de ~2,4 GB, quedan 2,3 GB disponibles y la swap sigue en 1,47 GB, igual que el 16/10 y sin paginación activa. | Baja (vigilar) | Sección 3.2 |
| 7 | ClamAV trabaja siempre en su tope (1.918 eventos `max`) liberando caché, sin OOM. Es lo esperado y confirma que no se debe bajar de 1.400 MB. | Informativo | Sección 5.5 |
| 8 | Los límites anti-abuso funcionan: 300 peticiones/min por usuario y 20 logins/5 min por IP. Solo serían un problema si muchos usuarios salieran por una misma IP. | Informativo | Secciones 5.2 y 5.3 |
| 9 | La BD de pruebas portable está dañada (le faltan archivos). Por eso no se pudieron validar las suites de app-recurso y app-users. | Media (para el proceso de pruebas) | Sección 7 |

**Servicios por encima del 80 % de su límite bajo carga: `postgres-recurso` (93,8 %) y `app-recurso` (83,1 %).** Ningún otro superó el 71 %.

---

## 9. Recomendaciones

Todas son técnicas (capacidad e infraestructura). Ninguna cambia reglas de negocio.

1. **Subir el límite de `app-involved` en la VM de 256 a 384 MiB**, igual que en el compose local, que ya dice "pico real de 226M (88%) con 50 usuarios". Es el único servicio de negocio que llegó a su tope en producción (242 veces desde el 16/10). Hay RAM disponible para hacerlo, 2,3 GB, y la suma de límites quedaría en 5.912 MiB. Si se quiere mantener la suma, se pueden tomar 128 MiB del gateway, que usa el 40 %.
2. **Dar margen a `postgres-recurso`.** Hay dos caminos, no excluyentes:
   - (a) Reducir el *pool* de `app-recurso` (por ejemplo, `pool_size` de 3 a 5 y `max_overflow` de 5 a 10 por worker) y revisar si las rutas que llaman a `app-docs`/`app-involved` liberan la sesión de BD antes de esa llamada.
   - (b) Subir el límite de `postgres-recurso` (por ejemplo, a 256–320 MB), compensando con margen de otros servicios: el gateway usó como máximo el 65 % y `app-users` el 59 %.

   Después de cualquiera de los dos, repetir la carga con `carga.py`.
3. **Repetir la medición de producción de la sección 3.1 una vez al mes** con `muestreo_stats.py` (ya corregido para SSH desde Windows), y revisar `memory.events` (`max` y `oom_kill`) de cada contenedor.
4. **Si la lentitud de la descarga del PDF molesta a los usuarios**, evaluar subir la CPU de `app-docs` de 0,5 a 1,0. La memoria no hace falta tocarla.
5. **Vigilar la swap de la VM.** Hoy está estable (1,47 GB, sin paginación activa). Si empieza a crecer, la VM necesitará más RAM: con 5.784 MiB de topes en 5.931 MiB, el sistema operativo y Docker quedan con poco margen garantizado.
6. **Recrear la BD de pruebas portable fuera de `AppData\Local\Temp`** y volver a ejecutar las suites de app-recurso y app-users.
7. Repetir esta prueba con un volumen de datos parecido al de producción en sancionatorio e infracciones (en local había 1 y 0 expedientes).

---

## 10. Conclusión

La redistribución de memoria del 16/10/2026 se comportó como se esperaba, y hoy se verificó también en producción. En la VM, los 19 contenedores están *healthy*, con 0 reinicios y 0 eventos OOM desde el despliegue. Los servicios que se ajustaron quedaron holgados: el gateway al 40 %, `app-users` al 62 %, nginx al 14 %, y `app-docs` y MinIO al 41 %. La RAM disponible es de 2,3 GB y la swap no creció. Con la redistribución, el nuevo módulo de Concesiones cupo en la VM sin que la suma de límites superara la RAM física.

En local, con los mismos límites, el sistema atendió **50 usuarios simultáneos sin errores, sin reinicios y sin eventos OOM**. La subida de `app-docs` era necesaria: con el límite anterior de 128 MB se habría pasado del tope bajo carga. La optimización de alertas se confirmó: alrededor de 44 veces más rápida en sancionatorio y alrededor de 35 veces en infracciones, con resultados idénticos.

Quedan dos puntos por atender, los dos técnicos y sin efecto en las reglas de negocio:

1. **`app-involved` trabaja en su tope de 256 MiB en producción** (242 eventos de tope desde el 16/10, sin OOM). Se recomienda subirlo a 384 MiB.
2. **El módulo de Concesiones tiene poco margen bajo carga alta.** En producción está holgado (`postgres-recurso` al 21,5 % y `app-recurso` al 64 %), pero en local, con 50 usuarios, `postgres-recurso` llegó al 93,8 % por el tamaño del *pool* de conexiones. Se recomienda, de forma preventiva, ajustar ese *pool*.
