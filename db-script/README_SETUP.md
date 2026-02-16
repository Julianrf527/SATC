# Setup de Bases de Datos - SATC

Este directorio contiene los scripts necesarios para configurar y migrar las bases de datos del sistema SATC usando Docker.

## Bases de Datos

El sistema utiliza 3 bases de datos PostgreSQL:

1. **user_db** - Gestión de usuarios, roles y autenticación
2. **expedientes_db** - Gestión de expedientes sancionatorios
3. **documentos_db** - Gestión de documentos y revisiones

## Archivos

### Scripts SQL

- `user_db.sql` - Dump completo de la base de datos de usuarios
- `expedientes_db.sql` - Dump completo de la base de datos de expedientes
- `documentos_db.sql` - Dump completo de la base de datos de documentos

### Migraciones

- `create_sesiones_activas.sql` - Migración para tabla de sesiones activas
- `add_url_doc_citacion_column.sql` - Migración para agregar columna url_doc_citacion

### Scripts de Automatización

- `apply_all_migrations.ps1` - Script principal para aplicar todas las migraciones en contenedores Docker

## Uso

### 🐳 Aplicar Migraciones con Docker

**Prerrequisitos:**

- Docker Desktop debe estar ejecutándose
- Los contenedores PostgreSQL deben estar activos

```powershell
cd db-script
.\apply_all_migrations.ps1
```

### Qué hace el script:

1. ✅ Verifica que Docker esté corriendo
2. ✅ Verifica que los contenedores de PostgreSQL estén activos:
   - `satc-postgres-users`
   - `satc-postgres-sanctioning`
   - `satc-postgres-docs`
3. ✅ Aplica los dumps de las 3 bases de datos
4. ✅ Aplica todas las migraciones adicionales
5. ✅ Verifica que las tablas se crearon correctamente

**Tiempo estimado**: 30-60 segundos

## Requisitos

- Docker Desktop instalado y ejecutándose
- PowerShell 5.1 o superior
- Contenedores de PostgreSQL activos:
  - `satc-postgres-users` (puerto 5433)
  - `satc-postgres-sanctioning` (puerto 5434)
  - `satc-postgres-docs` (puerto 5435)

## Notas Importantes

⚠️ **ADVERTENCIA**: Este proceso eliminará completamente las bases de datos existentes y todos sus datos. Asegúrate de hacer un respaldo antes de ejecutar estos scripts si tienes datos importantes.

### El proceso realiza:

1. Aplica los dumps completos de las 3 bases de datos
2. Crea la tabla `sesion_activa` para control de sesiones únicas
3. Agrega la columna `url_doc_citacion` para documentos de citación
4. Verifica que todas las tablas se crearon correctamente

## Solución de Problemas

### Error: "Docker no está ejecutándose"

Asegúrate de que Docker Desktop esté abierto y corriendo:

```powershell
# Verificar estado de Docker
docker ps
```

### Error: "Contenedor no encontrado"

Verifica que los contenedores de PostgreSQL estén activos:

```powershell
# Listar contenedores activos
docker ps | Select-String "postgres"
```

Si los contenedores no están activos, inícilaos con:

```powershell
docker-compose up -d
```

### Error al aplicar migraciones

Si una migración falla, puedes aplicarla manualmente:

```powershell
# Ejemplo para crear la tabla de sesiones activas
Get-Content create_sesiones_activas.sql | docker exec -i satc-postgres-users psql -U admin -d user_db
```

## Estructura del Directorio

```
db-script/
├── apply_all_migrations.ps1          # Script principal
├── user_db.sql                        # Dump: Base de datos de usuarios
├── expedientes_db.sql                 # Dump: Base de datos de expedientes
├── documentos_db.sql                  # Dump: Base de datos de documentos
├── create_sesiones_activas.sql        # Migración: Tabla sesiones
├── add_url_doc_citacion_column.sql    # Migración: Columna citación
└── README_SETUP.md                    # Este archivo
```
