-- Migración: Crear tabla file_hash para deduplicación de archivos en app-docs
-- Fecha: 2026-02-12
-- Base de datos: documentos_db

-- Crear tabla file_hash
CREATE TABLE IF NOT EXISTS file_hash (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    file_url TEXT NOT NULL,
    original_filename VARCHAR(255),
    content_type VARCHAR(100),
    file_size INTEGER,
    reference_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_referenced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Crear índice único para búsquedas rápidas por hash
CREATE UNIQUE INDEX IF NOT EXISTS ix_file_hash_unique ON file_hash(file_hash);

-- Crear índice para búsquedas de archivos huérfanos
CREATE INDEX IF NOT EXISTS ix_file_hash_ref_count ON file_hash(reference_count);

-- Crear índice por fecha de creación
CREATE INDEX IF NOT EXISTS ix_file_hash_created ON file_hash(created_at);

-- Comentarios
COMMENT ON TABLE file_hash IS 'Tabla de deduplicación de archivos en app-docs';
COMMENT ON COLUMN file_hash.file_hash IS 'Hash SHA256 del contenido del archivo';
COMMENT ON COLUMN file_hash.reference_count IS 'Número de referencias al archivo';

GRANT SELECT, INSERT, UPDATE ON file_hash TO PUBLIC;
GRANT USAGE ON SEQUENCE file_hash_id_seq TO PUBLIC;
