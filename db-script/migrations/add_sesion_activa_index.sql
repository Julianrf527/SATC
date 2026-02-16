-- Migración: Agregar índice para optimizar invalidación de sesiones
-- Fecha: 2026-02-13
-- Objetivo: Resolver cuello de botella en login con 100+ usuarios concurrentes

-- Índice compuesto para la consulta: WHERE usuario_id = X AND activo = TRUE
CREATE INDEX IF NOT EXISTS idx_sesion_activa_usuario_activo 
ON sesion_activa(usuario_id, activo)
WHERE activo = TRUE;

-- Índice para búsquedas por token_jti (ya existe unique constraint, pero explícito)
CREATE INDEX IF NOT EXISTS idx_sesion_activa_token_jti 
ON sesion_activa(token_jti);

-- Índice para limpiar sesiones antiguas (mantenimiento)
CREATE INDEX IF NOT EXISTS idx_sesion_activa_fecha_login 
ON sesion_activa(fecha_login)
WHERE activo = TRUE;

-- Verificar índices creados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'sesion_activa'
ORDER BY indexname;
