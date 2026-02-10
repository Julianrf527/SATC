-- Script SQL para agregar índices de optimización en app-sancionatoria
-- Ejecutar este script en la base de datos para mejorar el rendimiento

-- =========================================
-- ÍNDICES PARA TABLA expediente
-- =========================================

-- Índice para búsquedas por radicado (búsqueda exacta y LIKE)
CREATE INDEX IF NOT EXISTS idx_expediente_radicado 
ON expediente(radicado);

-- Índice para búsquedas por encargado (muy frecuente)
CREATE INDEX IF NOT EXISTS idx_expediente_encargado 
ON expediente(encargado_id);

-- Índice para búsquedas por nombre de expediente
CREATE INDEX IF NOT EXISTS idx_expediente_nombre 
ON expediente(nombre_expediente);

-- Índice para ordenamiento por fecha de creación
CREATE INDEX IF NOT EXISTS idx_expediente_fecha_creacion 
ON expediente(fecha_creacion DESC);

-- Índice compuesto para filtros comunes
CREATE INDEX IF NOT EXISTS idx_expediente_encargado_fecha 
ON expediente(encargado_id, fecha_creacion DESC);

-- Índice para búsquedas por vereda
CREATE INDEX IF NOT EXISTS idx_expediente_vereda 
ON expediente(vereda_id);

-- =========================================
-- ÍNDICES PARA TABLA expediente_recurso
-- =========================================

-- Índice para relación con expediente
CREATE INDEX IF NOT EXISTS idx_expediente_recurso_radicado 
ON expediente_recurso(expediente_radicado);

-- Índice para búsquedas por recurso
CREATE INDEX IF NOT EXISTS idx_expediente_recurso_recurso 
ON expediente_recurso(recurso_id);

-- Índice compuesto para filtros de recursos
CREATE INDEX IF NOT EXISTS idx_expediente_recurso_compound 
ON expediente_recurso(expediente_radicado, recurso_id);

-- =========================================
-- ÍNDICES PARA TABLA involucrado_expediente
-- =========================================

-- Índice para relación con expediente
CREATE INDEX IF NOT EXISTS idx_involucrado_expediente_radicado 
ON involucrado_expediente(expediente_radicado);

-- Índice para relación con involucrado
CREATE INDEX IF NOT EXISTS idx_involucrado_expediente_involucrado 
ON involucrado_expediente(involucrado_id);

-- Índice compuesto
CREATE INDEX IF NOT EXISTS idx_involucrado_expediente_compound 
ON involucrado_expediente(expediente_radicado, involucrado_id);

-- =========================================
-- ÍNDICES PARA TABLA involucrado
-- =========================================

-- Índice para búsquedas por número de documento
CREATE INDEX IF NOT EXISTS idx_involucrado_numero_documento 
ON involucrado(numero_documento);

-- Índice para búsquedas por tipo de documento
CREATE INDEX IF NOT EXISTS idx_involucrado_tipo_documento 
ON involucrado(tipo_documento);

-- Índice para búsquedas por nombre
CREATE INDEX IF NOT EXISTS idx_involucrado_nombre 
ON involucrado(nombre);

-- Índice compuesto para búsquedas de persona
CREATE INDEX IF NOT EXISTS idx_involucrado_documento_tipo 
ON involucrado(numero_documento, tipo_documento);

-- =========================================
-- ÍNDICES PARA TABLA etapa
-- =========================================

-- Índice para relación con expediente
CREATE INDEX IF NOT EXISTS idx_etapa_expediente 
ON etapa(expediente_radicado);

-- Índice para búsquedas por tipo de etapa
CREATE INDEX IF NOT EXISTS idx_etapa_tipo 
ON etapa(tipo_etapa_id);

-- Índice para ordenamiento por fecha
CREATE INDEX IF NOT EXISTS idx_etapa_fecha_inicio 
ON etapa(fecha_inicio DESC);

-- Índice compuesto para obtener última etapa (CRÍTICO para performance)
CREATE INDEX IF NOT EXISTS idx_etapa_radicado_fecha 
ON etapa(expediente_radicado, fecha_inicio DESC);

-- =========================================
-- ÍNDICES PARA TABLA notificacion
-- =========================================

-- Índice para relación con acto administrativo
CREATE INDEX IF NOT EXISTS idx_notificacion_acto_admin 
ON notificacion(acto_admin_id);

-- Índice para ordenamiento por fecha
CREATE INDEX IF NOT EXISTS idx_notificacion_fecha_creacion 
ON notificacion(fecha_creacion DESC);

-- =========================================
-- ÍNDICES PARA TABLA involucrado_notificacion
-- =========================================

-- Índice para relación con notificación
CREATE INDEX IF NOT EXISTS idx_involucrado_notif_notificacion 
ON involucrado_notificacion(notificacion_id);

-- Índice para relación con involucrado
CREATE INDEX IF NOT EXISTS idx_involucrado_notif_involucrado 
ON involucrado_notificacion(involucrado_id);

-- Índice para búsquedas por tipo de notificación
CREATE INDEX IF NOT EXISTS idx_involucrado_notif_tipo 
ON involucrado_notificacion(tipo_notificacion_id);

-- Índice para ordenamiento por fecha
CREATE INDEX IF NOT EXISTS idx_involucrado_notif_fecha 
ON involucrado_notificacion(fecha_notificacion DESC);

-- =========================================
-- ÍNDICES PARA TABLA acto_admin
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_acto_admin_etapa 
ON acto_admin(etapa_id);

-- Índice para búsquedas por tipo
CREATE INDEX IF NOT EXISTS idx_acto_admin_tipo 
ON acto_admin(tipo_acto);

-- Índice para ordenamiento por fecha
CREATE INDEX IF NOT EXISTS idx_acto_admin_fecha_creacion 
ON acto_admin(fecha_creacion DESC);

-- Índice para búsquedas por numerado
CREATE INDEX IF NOT EXISTS idx_acto_admin_numerado 
ON acto_admin(numerado);

-- =========================================
-- ÍNDICES PARA TABLA medida_preventiva
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_medida_preventiva_etapa 
ON medida_preventiva(etapa_id);

-- Índice para búsquedas por tipo de medida
CREATE INDEX IF NOT EXISTS idx_medida_preventiva_tipo 
ON medida_preventiva(tipo_medida_id);

-- Índice para búsquedas por estado
CREATE INDEX IF NOT EXISTS idx_medida_preventiva_estado 
ON medida_preventiva(estado_medida);

-- =========================================
-- ÍNDICES PARA TABLA cesacion
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_cesacion_etapa 
ON cesacion(etapa_id);

-- Índice para relación con tipo de cesación
CREATE INDEX IF NOT EXISTS idx_cesacion_tipo 
ON cesacion(tipo_cesacion_id);

-- =========================================
-- ÍNDICES PARA TABLA formulacion_cargos
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_formulacion_cargos_etapa 
ON formulacion_cargos(etapa_id);

-- Índice para búsquedas por descargos
CREATE INDEX IF NOT EXISTS idx_formulacion_cargos_descargos 
ON formulacion_cargos(descargos);

-- =========================================
-- ÍNDICES PARA TABLA decision_fondo
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_decision_fondo_etapa 
ON decision_fondo(etapa_id);

-- Índice para búsquedas por tipo de sanción
CREATE INDEX IF NOT EXISTS idx_decision_fondo_tipo_sancion 
ON decision_fondo(tipo_sancion_id);

-- =========================================
-- ÍNDICES PARA TABLA ejecucion_sancion
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_ejecucion_sancion_etapa 
ON ejecucion_sancion(etapa_id);

-- Índice para ordenamiento por fecha de auto
CREATE INDEX IF NOT EXISTS idx_ejecucion_sancion_fecha_auto 
ON ejecucion_sancion(fecha_auto DESC);

-- Índice para búsquedas por cobro coactivo
CREATE INDEX IF NOT EXISTS idx_ejecucion_sancion_cobro 
ON ejecucion_sancion(cobro_coactivo);

-- =========================================
-- ÍNDICES PARA TABLA documento
-- =========================================

-- Índice para relación con etapa
CREATE INDEX IF NOT EXISTS idx_documento_etapa 
ON documento(etapa_id);

-- Índice para ordenamiento por fecha de subida
CREATE INDEX IF NOT EXISTS idx_documento_fecha_subida 
ON documento(fecha_subida DESC);

-- Índice para búsquedas por nombre
CREATE INDEX IF NOT EXISTS idx_documento_nombre 
ON documento(nombre);

-- =========================================
-- ÍNDICES PARA TABLA log_auditoria
-- =========================================

-- Índice para relación con expediente
CREATE INDEX IF NOT EXISTS idx_log_auditoria_radicado 
ON log_auditoria(expediente_radicado);

-- Índice para búsquedas por usuario
CREATE INDEX IF NOT EXISTS idx_log_auditoria_usuario 
ON log_auditoria(usuario_id);

-- Índice para ordenamiento por fecha
CREATE INDEX IF NOT EXISTS idx_log_auditoria_fecha 
ON log_auditoria(fecha DESC);

-- Índice para búsquedas por tipo de operación
CREATE INDEX IF NOT EXISTS idx_log_auditoria_tipo_operacion 
ON log_auditoria(tipo_operacion);

-- Índice para búsquedas por tabla afectada
CREATE INDEX IF NOT EXISTS idx_log_auditoria_tabla 
ON log_auditoria(tabla_afectada);

-- =========================================
-- ÍNDICES PARA TABLA vereda
-- =========================================

-- Índice para relación con municipio
CREATE INDEX IF NOT EXISTS idx_vereda_municipio 
ON vereda(municipio_id);

-- Índice para búsquedas por nombre
CREATE INDEX IF NOT EXISTS idx_vereda_nombre 
ON vereda(nombre);

-- =========================================
-- ANÁLISIS Y ESTADÍSTICAS
-- =========================================

-- Actualizar estadísticas para el optimizador de consultas (PostgreSQL)
ANALYZE expediente;
ANALYZE expediente_recurso;
ANALYZE involucrado_expediente;
ANALYZE involucrado;
ANALYZE etapa;
ANALYZE notificacion;
ANALYZE involucrado_notificacion;
ANALYZE acto_admin;
ANALYZE medida_preventiva;
ANALYZE cesacion;
ANALYZE formulacion_cargos;
ANALYZE decision_fondo;
ANALYZE ejecucion_sancion;
ANALYZE documento;
ANALYZE log_auditoria;
ANALYZE vereda;

-- Para MySQL/MariaDB usa:
-- ANALYZE TABLE expediente;
-- ANALYZE TABLE expediente_recurso;
-- etc.
