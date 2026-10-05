-- ============================================================================
-- SATC · app-sancionatoria · cierre de permisos (auditoría 2026-10)
-- Base: user_db (contenedor postgres-users).  Ejecutar en la VM ANTES de
-- desplegar la nueva imagen de app-sancionatoria:
--   docker exec -i satc-postgres-users psql -U postgres -d user_db < 2026-10_sancionatorio_permisos_vm.sql
--
-- El permiso sancionatorio_consultar YA existe en el catálogo sembrado por
-- app-users/db/seeds.py (menu_path /file/consult) y la pantalla /file/consult
-- ya lo exige en App.tsx. Lo nuevo es que el backend lo exige ahora. Por eso
-- este script solo (1) garantiza que exista, (2) garantiza que admin lo tenga
-- y (3) permite revisar qué roles quedan con cada acceso. Es idempotente.
-- ============================================================================

-- ── 1. ANTES: roles y permisos ──────────────────────────────────────────────
SELECT r.id, r.nombre, string_agg(p.nombre, ', ' ORDER BY p.nombre) AS permisos
FROM rol r
LEFT JOIN rol_permiso rp ON rp.rol_id = r.id
LEFT JOIN permiso p ON p.id = rp.permiso_id
GROUP BY r.id, r.nombre ORDER BY r.id;

-- ── 2. Catálogo: el permiso existe (no hace nada si ya está) ────────────────
INSERT INTO permiso (nombre, menu_path)
VALUES ('sancionatorio_consultar', '/file/consult')
ON CONFLICT (nombre) DO NOTHING;

-- ── 3. admin (rol 1) tiene todos los permisos del módulo ───────────────────
INSERT INTO rol_permiso (rol_id, permiso_id)
SELECT 1, p.id FROM permiso p
WHERE p.nombre IN ('sancionatorio_consultar', 'sancionatorio_gestionar',
                   'sancionatorio_asignar', 'sancionatorio_alertas')
  AND EXISTS (SELECT 1 FROM rol WHERE id = 1)
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- Los demás roles NO se tocan: quien hoy entra a /file/consult ya tiene
-- sancionatorio_consultar (es lo que exige el menú), y quien entra a
-- /file/manage sigue viendo sus propios expedientes con sancionatorio_gestionar.

-- ── 4. DESPUÉS: acceso de cada rol a los endpoints cerrados ─────────────────
-- consulta   = ve TODOS los expedientes (lista, detalle, etapas, PDF, involucrados)
-- gestion    = crea expedientes, ve y edita solo los que tiene a cargo
-- asignacion = lista de asignación (/expediente/get) y envío manual de alertas
SELECT r.id, r.nombre,
       bool_or(p.nombre = 'sancionatorio_consultar') AS consulta,
       bool_or(p.nombre = 'sancionatorio_gestionar') AS gestion,
       bool_or(p.nombre = 'sancionatorio_asignar')   AS asignacion,
       bool_or(p.nombre = 'involucrado_gestionar')   AS involucrados,
       (SELECT count(*) FROM usuario u WHERE u.rol_id = r.id AND u.activo) AS usuarios_activos
FROM rol r
LEFT JOIN rol_permiso rp ON rp.rol_id = r.id
LEFT JOIN permiso p ON p.id = rp.permiso_id
GROUP BY r.id, r.nombre ORDER BY r.id;

-- ── 5. Riesgo de bloqueo: usuarios encargados de expedientes sancionatorios
--      cuyo rol NO tiene sancionatorio_gestionar (dejarán de ver/editar sus
--      expedientes). Cruzar con expedientes_db:
--        SELECT DISTINCT encargado_id FROM expediente WHERE encargado_id IS NOT NULL;
SELECT u.id, u.primer_nombre, u.primer_apellido, r.nombre AS rol
FROM usuario u JOIN rol r ON r.id = u.rol_id
WHERE u.activo
  AND NOT EXISTS (
      SELECT 1 FROM rol_permiso rp JOIN permiso p ON p.id = rp.permiso_id
      WHERE rp.rol_id = u.rol_id AND p.nombre IN ('sancionatorio_gestionar', 'sancionatorio_consultar'))
ORDER BY u.id;
