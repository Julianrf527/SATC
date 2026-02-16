# Sistema de Deduplicación de Archivos por Hash

## Descripción

Este sistema implementa deduplicación de archivos en MinIO basándose en el hash SHA256 del contenido de los archivos. Cuando se intenta subir un archivo que ya existe (mismo contenido), el sistema reutiliza la URL existente en lugar de duplicar el archivo físicamente.

## Beneficios

- ✅ **Ahorro de espacio**: No se duplican archivos idénticos en MinIO
- ✅ **Eficiencia**: Uploads más rápidos cuando el archivo ya existe
- ✅ **Integridad**: Los hashes SHA256 garantizan que los archivos son idénticos
- ✅ **Trazabilidad**: Se mantiene un contador de referencias para cada archivo
- ✅ **Transparente**: El sistema funciona automáticamente sin cambios en el frontend

## Arquitectura

### Tabla `file_hash`

```sql
CREATE TABLE file_hash (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,        -- Hash SHA256 del archivo
    file_url TEXT NOT NULL,                        -- URL en MinIO
    original_filename VARCHAR(255),                -- Nombre original del primer archivo
    content_type VARCHAR(100),                     -- MIME type
    file_size INTEGER,                             -- Tamaño en bytes
    reference_count INTEGER DEFAULT 1,             -- Contador de referencias
    created_at TIMESTAMP WITH TIME ZONE,           -- Fecha de creación
    last_referenced_at TIMESTAMP WITH TIME ZONE    -- Última vez referenciado
);
```

### Flujo de Funcionamiento

1. **Usuario sube archivo** → Se lee el contenido en bytes
2. **Cálculo de hash** → Se calcula SHA256 del archivo
3. **Búsqueda en BD** → Se busca si existe ese hash
4. **Si existe**:
   - Se reutiliza la URL existente
   - Se incrementa `reference_count`
   - Se actualiza `last_referenced_at`
   - ✅ No se sube archivo a MinIO (ahorro de espacio)
5. **Si NO existe**:
   - Se sube el archivo a MinIO
   - Se crea registro en `file_hash` con `reference_count = 1`
   - Se retorna la nueva URL

## Instalación

### 1. Aplicar Migración de Base de Datos

```bash
# Conectarse a PostgreSQL
psql -U postgres -d expedientes_db

# Ejecutar migración
\i app-sancionatoria/db/migrations/create_file_hash_table.sql
```

O usando script:

```bash
# Windows PowerShell
cd db-script
.\recreate_all_databases.ps1
```

### 2. Verificar Tabla Creada

```sql
-- Verificar que la tabla existe
SELECT * FROM file_hash LIMIT 1;

-- Verificar índices
\d file_hash
```

### 3. Reiniciar Servicios

```bash
# Reiniciar app-sancionatoria para cargar el nuevo modelo
# (Cerrar y volver a ejecutar el servicio)
```

## Uso

### En el Código

El sistema funciona automáticamente. Los endpoints ya están actualizados para usar `upload_file_with_deduplication`:

```python
# Antes:
result = upload_file_to_minio(file_data, object_name, content_type)

# Ahora:
result = upload_file_with_deduplication(
    db=db,
    file_data=file_data,
    object_name=object_name,
    original_filename=file.filename,
    content_type=file.content_type
)

# El resultado incluye:
# - ok: bool
# - url: str (URL del archivo, reutilizada o nueva)
# - message: str
# - deduplicated: bool (True si se reutilizó, False si es nuevo)
# - file_hash: str (SHA256 del archivo)
# - reference_count: int (número de referencias)
```

### Logs

El sistema genera logs informativos:

```
INFO - Hash calculado: a3f2b8c... para archivo: documento.pdf
INFO - Archivo duplicado detectado. Hash: a3f2b8c..., URL: satc-expedientes/...
INFO - Archivo duplicado detectado - URL reutilizada: satc-expedientes/... (Hash: a3f2b8c...)
```

```
INFO - Archivo nuevo subido y registrado. Hash: 9d8e7f6..., URL: satc-expedientes/...
INFO - Archivo nuevo guardado en MinIO: satc-expedientes/... (Hash: 9d8e7f6...)
```

## Monitoreo

### Consultas Útiles

```sql
-- Ver todos los archivos y sus referencias
SELECT
    file_hash,
    original_filename,
    reference_count,
    file_size,
    created_at
FROM file_hash
ORDER BY reference_count DESC;

-- Ver archivos más referenciados (duplicados)
SELECT
    original_filename,
    reference_count,
    file_size,
    file_size * reference_count as space_saved_bytes,
    (file_size * reference_count / 1024.0 / 1024.0) as space_saved_mb
FROM file_hash
WHERE reference_count > 1
ORDER BY space_saved_bytes DESC;

-- Calcular espacio total ahorrado
SELECT
    COUNT(*) as duplicates_count,
    SUM(file_size * (reference_count - 1)) as total_saved_bytes,
    ROUND(SUM(file_size * (reference_count - 1)) / 1024.0 / 1024.0, 2) as total_saved_mb,
    ROUND(SUM(file_size * (reference_count - 1)) / 1024.0 / 1024.0 / 1024.0, 2) as total_saved_gb
FROM file_hash
WHERE reference_count > 1;

-- Archivos huérfanos (sin referencias - candidatos para limpieza)
SELECT * FROM file_hash WHERE reference_count = 0;
```

## Mantenimiento

### Limpieza de Archivos Huérfanos

Cuando se elimina una notificación, NO se elimina automáticamente el archivo de MinIO (para evitar romper otras referencias). Se debe implementar un proceso de limpieza:

```python
# Futuro: Script de limpieza de archivos con reference_count = 0
# 1. Encontrar archivos con reference_count = 0
# 2. Verificar que no estén en uso
# 3. Eliminar de MinIO
# 4. Eliminar registro de file_hash
```

### Decrementar Referencias

Cuando se elimina un documento, se debe decrementar el contador (TODO: Implementar):

```python
def decrement_file_reference(db: Session, file_url: str):
    # Buscar por URL
    file_record = db.query(FileHash).filter(FileHash.file_url == file_url).first()
    if file_record:
        file_record.reference_count -= 1
        if file_record.reference_count < 0:
            file_record.reference_count = 0
        db.commit()
```

## Endpoints Actualizados

### Notificaciones

- ✅ `POST /notificaciones/{notificacion_id}/involucrados` - Crear notificación de involucrado

### Otros endpoints

Los demás endpoints de subida de archivos pueden actualizarse gradualmente siguiendo el mismo patrón.

## Notas Técnicas

- **Hash**: Se usa SHA256 (64 caracteres hexadecimales)
- **Colisiones**: Estadísticamente imposibles con SHA256
- **Rendimiento**: La búsqueda por hash usa índice único (muy rápida)
- **Thread-safe**: SQLAlchemy maneja la concurrencia correctamente
- **Transaccional**: Los commits de BD garantizan consistencia

## Troubleshooting

### Error: "relation file_hash does not exist"

**Solución**: Aplicar la migración SQL

### Error: ImportError con FileHash

**Solución**: Reiniciar el servicio para cargar el nuevo modelo

### Los archivos siguen duplicándose

**Solución**: Verificar que los endpoints usan `upload_file_with_deduplication` no `upload_file_to_minio`

## Roadmap

- [ ] Implementar decrementación de referencias al eliminar documentos
- [ ] Script de limpieza de archivos huérfanos
- [ ] Dashboard de estadísticas de deduplicación
- [ ] Actualizar todos los endpoints de upload
- [ ] API para consultar espacio ahorrado
