# Pruebas de Carga — SATC

## Requisitos

```bash
pip install -r requirements.txt
```

## Configuración

Editar `locustfile.py` y ajustar:

```python
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"
```

Con credenciales reales de un usuario del sistema que tenga permisos para consultar las tres rutas principales.

---

## Ejecución

### Interfaz web (recomendado para explorar)

```bash
locust -f locustfile.py --host http://localhost:8000
# Abrir http://localhost:8089
```

### Sin interfaz (CI/CD o terminal)

```bash
# Carga típica: 30 usuarios, rampa de 5/s, durante 2 minutos
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 30 -r 5 --run-time 2m

# Carga media: 50 usuarios
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 50 -r 10 --run-time 2m

# Carga máxima validada: 100 usuarios
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 100 -r 10 --run-time 3m

# Exportar resultados a CSV
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 100 -r 10 --run-time 3m \
  --csv results/satc_100u
```

---

## Clases de usuario

| Clase          | Peso | Comportamiento                       |
| -------------- | ---- | ------------------------------------ |
| `ReadOnlyUser` | 70%  | Solo hace GET (consultas)            |
| `WriteUser`    | 30%  | Mezcla GET + POST (crea expedientes) |

Cuando se ejecuta el archivo con `--class-picker` se puede elegir la clase manualmente.  
Sin esa opción, Locust respeta los atributos `weight` y mezcla ambas clases automáticamente.

---

## Umbrales esperados (arquitectura consolidada)

| Escenario    | Usuarios | p95 objetivo | Tasa de error |
| ------------ | -------- | ------------ | ------------- |
| Carga típica | 30       | < 300 ms     | 0%            |
| Carga media  | 50       | < 600 ms     | < 1%          |
| Carga máxima | 100      | < 1 000 ms   | < 2%          |

Si los valores medidos superan los umbrales, revisar:

1. **CPU/RAM del contenedor** → `docker stats`
2. **Cola de workers de Gunicorn** → logs del contenedor
3. **Pool de conexiones PostgreSQL** → `pg_stat_activity`
4. **Hit rate de Redis** → `redis-cli info stats`

---

## Endpoints cubiertos

### Sin autenticación

- `GET /health`

### Usuarios (`app-users-1:8001` vía Gateway)

- `GET /users/user/all`
- `GET /users/user/log`
- `GET /users/role/all`
- `GET /users/role/permissions`
- `GET /users/notification/all/:id`

### Sancionatoria (`app-sanctioning:8002` vía Gateway)

- `GET /sanctioning/document/`
- `GET /sanctioning/town/sidewalk`
- `GET /sanctioning/file/get`
- `GET /sanctioning/involved/manage`
- `POST /sanctioning/document/new`

### Documentos (`app-docs:8003` vía Gateway)

- `GET /documents/document/`
- `GET /documents/assignment/`
