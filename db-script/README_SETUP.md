# Setup de Bases de Datos - SATC

Este directorio contiene los scripts necesarios para recrear las bases de datos del sistema SATC.

## Bases de Datos

El sistema utiliza 3 bases de datos PostgreSQL:

1. **user_db** - Gestión de usuarios, roles y autenticación
2. **expedientes_db** - Gestión de expedientes sancionatorios
3. **documentos_db** - Gestión de documentos y revisiones

## Archivos

- `setup_databases.sql` - Script SQL que elimina y crea las bases de datos vacías
- `user_db.sql` - Dump completo de la base de datos de usuarios
- `expedientes_db.sql` - Dump completo de la base de datos de expedientes
- `documentos_db.sql` - Dump completo de la base de datos de documentos
- `recreate_all_databases.ps1` - Script PowerShell para automatizar todo el proceso
- `recreate_all_databases.bat` - Script Batch alternativo para automatizar el proceso

## Uso

### Opción 1: Script PowerShell (Recomendado)

```powershell
cd db-script
.\recreate_all_databases.ps1
```

### Opción 2: Script Batch

```cmd
cd db-script
recreate_all_databases.bat
```

### Opción 3: Manual con psql

```bash
# 1. Crear las bases de datos
psql -h localhost -U postgres -d postgres -f setup_databases.sql

# 2. Restaurar cada base de datos
psql -h localhost -U postgres -d user_db -f user_db.sql
psql -h localhost -U postgres -d expedientes_db -f expedientes_db.sql
psql -h localhost -U postgres -d documentos_db -f documentos_db.sql
```

## Requisitos

- PostgreSQL 12 o superior instalado
- Usuario `postgres` con privilegios de superusuario
- Herramienta `psql` disponible en el PATH del sistema
- Contraseña del usuario postgres

## Notas Importantes

⚠️ **ADVERTENCIA**: Este proceso eliminará completamente las bases de datos existentes y todos sus datos. Asegúrate de hacer un respaldo antes de ejecutar estos scripts si tienes datos importantes.

### El proceso realiza:

1. Termina todas las conexiones activas a las bases de datos
2. Elimina las bases de datos si existen
3. Crea las bases de datos nuevas
4. Restaura todas las tablas, funciones, vistas y datos desde los archivos SQL

### Tiempo estimado

El proceso completo toma aproximadamente 1-2 minutos dependiendo del tamaño de los datos.

## Solución de Problemas

### Error: "psql no se reconoce como comando"

Asegúrate de que PostgreSQL esté instalado y que `psql` esté en tu PATH. Para agregarlo:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\15\bin"
```

### Error: "no se pudo conectar al servidor"

- Verifica que PostgreSQL esté ejecutándose
- Confirma el host y puerto en la configuración del script
- Verifica las credenciales del usuario

### Error: "permiso denegado"

Asegúrate de ejecutar el script con un usuario que tenga privilegios suficientes (típicamente el usuario `postgres`).

## Configuración

Si tu configuración de PostgreSQL es diferente, edita las variables al inicio del script:

```powershell
$PG_HOST = "localhost"     # Host de PostgreSQL
$PG_PORT = "5432"          # Puerto de PostgreSQL
$PG_USER = "postgres"      # Usuario de PostgreSQL
```
