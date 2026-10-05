export type HeaderPermission = { name: string; path: string };

export type FormattedPermission = {
  original: string;
  action: string;
  module: string;
  path: string;
};

const ACTION_MAP: Record<string, string> = {
  agregar: "Agregar",
  gestionar: "Gestionar",
  roles: "Roles",
  permisos: "Permisos",
  asignar: "Asignar",
  encargados: "Encargados",
};

const MODULE_MAP: Record<string, string> = {
  usuarios: "Usuarios",
  expediente: "Expediente",
  file: "Archivo",
  user: "Usuario",
};

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** `"modulo_accion_x"` → `{ module: "Modulo", action: "Accion X" }`. */
export function formatPermission(perm: HeaderPermission): FormattedPermission {
  const parts = perm.name.split("_");
  let action: string;
  let module: string;

  if (parts.length >= 2) {
    const modulePart = parts[0];
    const actionPart = parts.slice(1).join(" ");
    module = MODULE_MAP[modulePart] || capitalize(modulePart);
    action = ACTION_MAP[actionPart] || actionPart.split(" ").map(capitalize).join(" ");
  } else {
    action = ACTION_MAP[parts[0]] || capitalize(parts[0]);
    module = "Sistema";
  }

  return { original: perm.name, action, module, path: perm.path };
}

/** Accesos cuyo nombre, acción o módulo contienen el texto (sin distinguir mayúsculas). */
export function filterPermissions(
  permissions: HeaderPermission[],
  search: string,
): FormattedPermission[] {
  if (search.trim() === "") return [];
  const q = search.toLowerCase();
  return permissions
    .map(formatPermission)
    .filter(
      (p) =>
        p.action.toLowerCase().includes(q) ||
        p.module.toLowerCase().includes(q) ||
        p.original.toLowerCase().includes(q),
    );
}
