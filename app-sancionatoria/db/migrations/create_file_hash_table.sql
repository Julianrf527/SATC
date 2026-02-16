-- Migración: Crear tabla file_hash para deduplicación de archivos
-- Fecha: 2026-02-12
-- Descripción: Esta tabla almacena hashes SHA256 de archivos para evitar duplicados en MinIO

-- Crear tabla file_hash
CREATE TABLE IF NOT EXISTS file_hash (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) NOT NULL UNIQUE,  -- Hash SHA256 (64 caracteres hexadecimales)
    file_url TEXT NOT NULL,                 -- URL del archivo en MinIO (bucket/path)
    original_filename VARCHAR(255),         -- Nombre original del primer archivo con este hash
    content_type VARCHAR(100),              -- MIME type del archivo (application/pdf, image/jpeg, etc.)
    file_size INTEGER,                      -- Tamaño del archivo en bytes
    reference_count INTEGER DEFAULT 1,      -- Contador de referencias (cuántas veces se usa)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_referenced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Crear índice único para búsquedas rápidas por hash
CREATE UNIQUE INDEX IF NOT EXISTS ix_file_hash_unique ON file_hash(file_hash);

-- Crear índice para búsquedas de archivos huérfanos (sin referencias)
CREATE INDEX IF NOT EXISTS ix_file_hash_ref_count ON file_hash(reference_count);

-- Crear índice para búsquedas por fecha de creación
CREATE INDEX IF NOT EXISTS ix_file_hash_created ON file_hash(created_at);

-- Comentarios para documentación
COMMENT ON TABLE file_hash IS 'Tabla de deduplicación de archivos. Almacena hashes SHA256 para evitar duplicados en MinIO';
COMMENT ON COLUMN file_hash.file_hash IS 'Hash SHA256 del contenido del archivo (64 caracteres hexadecimales)';
COMMENT ON COLUMN file_hash.file_url IS 'URL del archivo en MinIO en formato bucket/path';
COMMENT ON COLUMN file_hash.reference_count IS 'Número de veces que este archivo está siendo referenciado. 0 = archivo huérfano que puede ser eliminado';
COMMENT ON COLUMN file_hash.last_referenced_at IS 'Última vez que se creó o reutilizó una referencia a este archivo';

-- Función para actualizar last_referenced_at y reference_count cuando se reutiliza un archivo
CREATE OR REPLACE FUNCTION update_file_hash_reference()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_referenced_at = CURRENT_TIMESTAMP;
    NEW.reference_count = COALESCE(NEW.reference_count, 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger NO SE CREA AQUÍ porque se manejará desde la aplicación
-- La aplicación incrementará reference_count manualmente cuando reutilice un archivo

GRANT SELECT, INSERT, UPDATE ON file_hash TO PUBLIC;
GRANT USAGE ON SEQUENCE file_hash_id_seq TO PUBLIC;
