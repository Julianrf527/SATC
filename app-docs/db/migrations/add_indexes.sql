-- Script SQL para agregar índices de optimización en app-docs
-- Ejecutar este script en la base de datos para mejorar el rendimiento

-- =========================================
-- ÍNDICES PARA TABLA documentos
-- =========================================

-- Índice para búsquedas por usuario creador (muy frecuente)
CREATE INDEX IF NOT EXISTS idx_documentos_usuario_creador 
ON documentos(usuario_creador_id);

-- Índice para búsquedas por estado (filtro común)
CREATE INDEX IF NOT EXISTS idx_documentos_estado 
ON documentos(estado);

-- Índice compuesto para búsquedas por usuario y estado
CREATE INDEX IF NOT EXISTS idx_documentos_usuario_estado 
ON documentos(usuario_creador_id, estado);

-- Índice para ordenamiento por fecha de creación
CREATE INDEX IF NOT EXISTS idx_documentos_fecha_creacion 
ON documentos(fecha_creacion DESC);

-- Índice compuesto para paginación optimizada
CREATE INDEX IF NOT EXISTS idx_documentos_estado_fecha 
ON documentos(estado, fecha_creacion DESC);

-- =========================================
-- ÍNDICES PARA TABLA versiones_documento
-- =========================================

-- Índice para relación con documentos
CREATE INDEX IF NOT EXISTS idx_versiones_documento_id 
ON versiones_documento(documento_id);

-- Índice compuesto para obtener versión actual
CREATE INDEX IF NOT EXISTS idx_versiones_documento_numero 
ON versiones_documento(documento_id, numero_version DESC);

-- =========================================
-- ÍNDICES PARA TABLA asignaciones_revisores
-- =========================================

-- Índice para búsquedas por revisor (muy frecuente)
CREATE INDEX IF NOT EXISTS idx_asignaciones_revisor 
ON asignaciones_revisores(revisor_id);

-- Índice para relación con documentos
CREATE INDEX IF NOT EXISTS idx_asignaciones_documento 
ON asignaciones_revisores(documento_id);

-- Índice compuesto para verificación de asignación específica
CREATE INDEX IF NOT EXISTS idx_asignaciones_revisor_documento 
ON asignaciones_revisores(revisor_id, documento_id);

-- =========================================
-- ÍNDICES PARA TABLA revisiones
-- =========================================

-- Índice para relación con documentos
CREATE INDEX IF NOT EXISTS idx_revisiones_documento 
ON revisiones(documento_id);

-- Índice para búsquedas por revisor
CREATE INDEX IF NOT EXISTS idx_revisiones_revisor 
ON revisiones(revisor_id);

-- Índice compuesto para obtener revisiones de un documento
CREATE INDEX IF NOT EXISTS idx_revisiones_documento_fecha 
ON revisiones(documento_id, fecha_revision DESC);

-- Índice para búsquedas por estado de revisión
CREATE INDEX IF NOT EXISTS idx_revisiones_estado 
ON revisiones(estado_revision);

-- =========================================
-- ÍNDICES PARA TABLA auditoria_documentos
-- =========================================

-- Índice para relación con documentos
CREATE INDEX IF NOT EXISTS idx_auditoria_documento 
ON auditoria_documentos(documento_id);

-- Índice compuesto para ordenamiento temporal
CREATE INDEX IF NOT EXISTS idx_auditoria_documento_fecha 
ON auditoria_documentos(documento_id, fecha_accion ASC);

-- Índice para búsquedas por tipo de acción
CREATE INDEX IF NOT EXISTS idx_auditoria_accion 
ON auditoria_documentos(accion);

-- =========================================
-- ÍNDICES PARA VISTA vista_documentos_detalle
-- =========================================
-- Nota: Si es una vista materializada, considera estos índices
-- Si es una vista regular, los índices en las tablas base son suficientes

-- Solo si vista_documentos_detalle es una MATERIALIZED VIEW:
-- CREATE INDEX IF NOT EXISTS idx_vista_docs_usuario_creador 
-- ON vista_documentos_detalle(usuario_creador_id);
-- 
-- CREATE INDEX IF NOT EXISTS idx_vista_docs_estado 
-- ON vista_documentos_detalle(estado);
-- 
-- CREATE INDEX IF NOT EXISTS idx_vista_docs_fecha 
-- ON vista_documentos_detalle(fecha_creacion DESC);

-- =========================================
-- ANÁLISIS Y ESTADÍSTICAS
-- =========================================

-- Actualizar estadísticas para el optimizador de consultas (PostgreSQL)
ANALYZE documentos;
ANALYZE versiones_documento;
ANALYZE asignaciones_revisores;
ANALYZE revisiones;
ANALYZE auditoria_documentos;

-- Para MySQL/MariaDB usa:
-- ANALYZE TABLE documentos;
-- ANALYZE TABLE versiones_documento;
-- etc.
