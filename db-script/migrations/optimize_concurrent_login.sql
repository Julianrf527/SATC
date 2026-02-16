-- Optimización para Login Concurrente
-- Fecha: 2026-02-14
-- Objetivo: Reducir lock contention en 50+ logins simultáneos

\c user_db;

-- 1. Agregar índice compuesto para sesion_activa
-- Acelera: UPDATE sesion_activa WHERE usuario_id = X AND activo = TRUE
CREATE INDEX IF NOT EXISTS idx_sesion_usuario_activo 
ON sesion_activa (usuario_id, activo);

-- 2. Índice en token_jti (ya existe como UNIQUE, pero verificamos)
-- Acelera: SELECT/UPDATE WHERE token_jti = X
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'sesion_activa' 
        AND indexname = 'sesion_activa_token_jti_key'
    ) THEN
        CREATE UNIQUE INDEX sesion_activa_token_jti_key 
        ON sesion_activa (token_jti);
    END IF;
END $$;

-- 3. Índice en usuario.correo para login rápido
-- Acelera: SELECT ... WHERE correo = 'email@example.com'
CREATE INDEX IF NOT EXISTS idx_usuario_correo 
ON usuario (correo);

-- 4. Índice en usuario.activo para filtrar rápido
-- Acelera: SELECT ... WHERE activo = TRUE
CREATE INDEX IF NOT EXISTS idx_usuario_activo 
ON usuario (activo);

-- 5. Analizar tablas para actualizar estadísticas del query planner
ANALYZE sesion_activa;
ANALYZE usuario;
ANALYZE rol;

-- Verificar índices creados
\echo '=== Índices en sesion_activa ==='
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'sesion_activa'
ORDER BY indexname;

\echo '=== Índices en usuario ==='
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'usuario'
ORDER BY indexname;

\echo '✅ Migración completada exitosamente'
