-- ====================================
-- involucrados_db - Init Script
-- ====================================

CREATE TABLE IF NOT EXISTS involucrado (
    id SERIAL PRIMARY KEY,
    numero_documento BIGINT,
    digito_verificacion VARCHAR(2),
    tipo_documento VARCHAR(20),
    nombre VARCHAR(100),
    celular BIGINT,
    correo VARCHAR(254)
);

CREATE TABLE IF NOT EXISTS log_auditoria (
    id SERIAL PRIMARY KEY,
    expediente_radicado VARCHAR,
    tabla_afectada VARCHAR(30) NOT NULL,
    id_registro VARCHAR(20),
    tipo_operacion VARCHAR(10) NOT NULL,
    usuario_id BIGINT,
    fecha TIMESTAMP DEFAULT NOW(),
    descripcion TEXT,
    datos_anteriores JSONB,
    datos_nuevos JSONB
);
