-- Vista: vista_documentos_detalle
-- Combina documentos con conteos agregados de revisiones y revisores asignados
-- Cada fila representa UN documento único (sin duplicados)

CREATE OR REPLACE VIEW vista_documentos_detalle AS
SELECT
    d.id,
    d.id AS documento_id,
    d.nombre,
    d.descripcion,
    d.tipo_archivo,
    d.estado,
    d.version_actual,
    d.numero_devoluciones,
    d.usuario_creador_id,
    d.fecha_creacion,
    d.fecha_ultima_actualizacion,
    COALESCE(rev_count.total_revisiones, 0) AS total_revisiones,
    COALESCE(asig_count.total_revisores, 0) AS total_revisores
FROM documentos d
LEFT JOIN (
    SELECT documento_id, COUNT(*) AS total_revisiones
    FROM revisiones
    GROUP BY documento_id
) rev_count ON rev_count.documento_id = d.id
LEFT JOIN (
    SELECT documento_id, COUNT(*) AS total_revisores
    FROM asignaciones_revisores
    GROUP BY documento_id
) asig_count ON asig_count.documento_id = d.id;
