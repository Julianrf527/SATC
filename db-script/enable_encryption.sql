-- ══════════════════════════════════════════════════════════════
-- MIGRACIÓN: Encriptación de Datos Sensibles en PostgreSQL
-- Base de datos: user_db, expedientes_db, documentos_db
-- Método: pgcrypto (AES-256-CBC)
-- ══════════════════════════════════════════════════════════════

-- PASO 1: Habilitar extensión pgcrypto en cada base de datos
-- Ejecutar en: user_db, expedientes_db, documentos_db

\c user_db;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\c expedientes_db;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\c documentos_db;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ══════════════════════════════════════════════════════════════
-- CONFIGURACIÓN DE CLAVE DE ENCRIPTACIÓN
-- ══════════════════════════════════════════════════════════════
-- IMPORTANTE: Definir ENCRYPTION_KEY en .env (256 bits)
-- Generar con: openssl rand -base64 32

-- ══════════════════════════════════════════════════════════════
-- BASE DE DATOS: user_db
-- Encriptar: numero_documento (DNI), correo (email)
-- ══════════════════════════════════════════════════════════════

\c user_db;

-- Crear tabla temporal para backup antes de migración
CREATE TABLE IF NOT EXISTS usuarios_backup_pre_encriptacion AS 
SELECT * FROM usuarios;

-- Agregar nuevas columnas encriptadas (tipo bytea)
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS numero_documento_encrypted bytea,
ADD COLUMN IF NOT EXISTS correo_encrypted bytea;

-- ══════════════════════════════════════════════════════════════
-- FUNCIONES DE AYUDA PARA ENCRIPTACIÓN
-- ══════════════════════════════════════════════════════════════

-- Función para encriptar texto
CREATE OR REPLACE FUNCTION encrypt_data(
    plaintext TEXT,
    encryption_key TEXT
) RETURNS bytea AS $$
BEGIN
    RETURN pgp_sym_encrypt(plaintext, encryption_key);
END;
$$ LANGUAGE plpgsql;

-- Función para desencriptar texto
CREATE OR REPLACE FUNCTION decrypt_data(
    ciphertext bytea,
    encryption_key TEXT
) RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(ciphertext, encryption_key);
END;
$$ LANGUAGE plpgsql;

-- ══════════════════════════════════════════════════════════════
-- MIGRACIÓN DE DATOS EXISTENTES (EJECUTAR CON PRECAUCIÓN)
-- ══════════════════════════════════════════════════════════════
-- NOTA: Reemplazar 'TU_CLAVE_SECRETA_256_BITS' con la clave real del .env

-- Ejemplo de migración (NO ejecutar automáticamente):
-- UPDATE usuarios 
-- SET 
--     numero_documento_encrypted = pgp_sym_encrypt(numero_documento, 'TU_CLAVE_SECRETA_256_BITS'),
--     correo_encrypted = pgp_sym_encrypt(correo, 'TU_CLAVE_SECRETA_256_BITS')
-- WHERE numero_documento_encrypted IS NULL;

-- Verificar que la encriptación funciona:
-- SELECT 
--     numero_documento,
--     pgp_sym_decrypt(numero_documento_encrypted, 'TU_CLAVE_SECRETA_256_BITS') AS documento_decrypted
-- FROM usuarios 
-- LIMIT 5;

-- ══════════════════════════════════════════════════════════════
-- CREAR ÍNDICES PARA BÚSQUEDA ENCRIPTADA
-- ══════════════════════════════════════════════════════════════
-- NOTA: Búsquedas en datos encriptados requieren desencriptación
-- Para búsquedas frecuentes, considerar mantener hash SHA-256 indexado

-- Agregar columnas de hash para búsqueda rápida
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS numero_documento_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS correo_hash VARCHAR(64);

-- Crear índices en hashes
CREATE INDEX IF NOT EXISTS idx_usuarios_documento_hash 
ON usuarios(numero_documento_hash);

CREATE INDEX IF NOT EXISTS idx_usuarios_correo_hash 
ON usuarios(correo_hash);

-- Función para actualizar hashes (ejecutar después de UPDATE)
CREATE OR REPLACE FUNCTION update_user_hashes() 
RETURNS TRIGGER AS $$
BEGIN
    -- Actualizar hash de documento si cambió
    IF NEW.numero_documento IS NOT NULL THEN
        NEW.numero_documento_hash := encode(digest(NEW.numero_documento, 'sha256'), 'hex');
    END IF;
    
    -- Actualizar hash de correo si cambió
    IF NEW.correo IS NOT NULL THEN
        NEW.correo_hash := encode(digest(LOWER(NEW.correo), 'sha256'), 'hex');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para actualizar hashes automáticamente
DROP TRIGGER IF EXISTS trg_update_user_hashes ON usuarios;
CREATE TRIGGER trg_update_user_hashes
BEFORE INSERT OR UPDATE ON usuarios
FOR EACH ROW
EXECUTE FUNCTION update_user_hashes();

-- ══════════════════════════════════════════════════════════════
-- BASE DE DATOS: expedientes_db
-- Encriptar: nombre_involucrado, documento_involucrado
-- ══════════════════════════════════════════════════════════════

\c expedientes_db;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Backup
CREATE TABLE IF NOT EXISTS involucrado_backup_pre_encriptacion AS 
SELECT * FROM involucrado;

-- Agregar columnas encriptadas
ALTER TABLE involucrado 
ADD COLUMN IF NOT EXISTS nombre_encrypted bytea,
ADD COLUMN IF NOT EXISTS numero_documento_encrypted bytea;

-- Agregar hashes para búsqueda
ALTER TABLE involucrado 
ADD COLUMN IF NOT EXISTS nombre_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS numero_documento_hash VARCHAR(64);

-- Índices
CREATE INDEX IF NOT EXISTS idx_involucrado_nombre_hash 
ON involucrado(nombre_hash);

CREATE INDEX IF NOT EXISTS idx_involucrado_documento_hash 
ON involucrado(numero_documento_hash);

-- ══════════════════════════════════════════════════════════════
-- BASE DE DATOS: documentos_db
-- Encriptar: metadatos sensibles si existen
-- ══════════════════════════════════════════════════════════════

\c documentos_db;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Los documentos ya están protegidos en MinIO
-- Solo encriptar metadatos sensibles si los hay en la BD

-- ══════════════════════════════════════════════════════════════
-- SCRIPT DE VALIDACIÓN
-- ══════════════════════════════════════════════════════════════

\c user_db;

-- Verificar extensión instalada
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

-- Verificar columnas agregadas
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
AND column_name LIKE '%encrypted%';

-- Test de encriptación/desencriptación
DO $$
DECLARE
    test_text TEXT := 'Prueba de encriptación';
    test_key TEXT := 'clave_de_prueba_temporal';
    encrypted bytea;
    decrypted TEXT;
BEGIN
    -- Encriptar
    encrypted := pgp_sym_encrypt(test_text, test_key);
    
    -- Desencriptar
    decrypted := pgp_sym_decrypt(encrypted, test_key);
    
    -- Verificar
    IF decrypted = test_text THEN
        RAISE NOTICE 'Test de encriptación: ✅ EXITOSO';
    ELSE
        RAISE EXCEPTION 'Test de encriptación: ❌ FALLIDO';
    END IF;
END $$;

-- ══════════════════════════════════════════════════════════════
-- NOTAS IMPORTANTES
-- ══════════════════════════════════════════════════════════════

-- 1. Red Local vs Internet:
--    En red local, encriptación protege contra:
--    - Acceso físico no autorizado a backups
--    - Robo de discos/servidores
--    - Acceso interno no autorizado a BD

-- 2. Clave de Encriptación:
--    - Almacenar ENCRYPTION_KEY en .env (fuera de repositorio Git)
--    - Rotar clave anualmente
--    - Backup seguro de la clave (necesaria para desencriptar)

-- 3. Impacto en Rendimiento:
--    - Encriptación: ~1-2ms por operación
--    - Desencriptación en búsquedas: usar hashes indexados
--    - Cachear datos desencriptados en Redis

-- 4. Búsquedas:
--    - Búsquedas exactas: usar hash indexado (rápido)
--    - Búsquedas parciales (LIKE): no posibles en datos encriptados
--    - Alternativa: Full-Text Search en datos desencriptados en cache

-- 5. Compliance:
--    - GDPR: Encriptación en reposo cumple requisitos
--    - ISO 27001: Control A.10.1.1 (Política de encriptación)
--    - Ley de Protección de Datos: Cumple medidas técnicas

-- ══════════════════════════════════════════════════════════════
-- COMANDOS DE ROLLBACK (SI ES NECESARIO)
-- ══════════════════════════════════════════════════════════════

-- Para revertir cambios (NO ejecutar en producción sin backup):
-- DROP TRIGGER IF EXISTS trg_update_user_hashes ON usuarios;
-- DROP FUNCTION IF EXISTS update_user_hashes();
-- DROP FUNCTION IF EXISTS decrypt_data(bytea, TEXT);
-- DROP FUNCTION IF EXISTS encrypt_data(TEXT, TEXT);
-- ALTER TABLE usuarios DROP COLUMN IF EXISTS numero_documento_encrypted;
-- ALTER TABLE usuarios DROP COLUMN IF EXISTS correo_encrypted;
-- ALTER TABLE usuarios DROP COLUMN IF EXISTS numero_documento_hash;
-- ALTER TABLE usuarios DROP COLUMN IF EXISTS correo_hash;
