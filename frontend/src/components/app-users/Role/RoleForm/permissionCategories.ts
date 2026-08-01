import type { Permiso } from "../../../../types/userApp";

export type PermissionCategory = {
  name: string;
  prefix: string;
  color: string;
  icon: string;
};

// Mapeo de iconos conocidos (para categorías existentes y futuras)
const iconMap: { [key: string]: string } = {
  admin_:
    "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  expediente_:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  documento_:
    "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z",
  auditoria_:
    "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01",
  infracciones_:
    "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.992-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z",
  multas_:
    "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
  usuarios_:
    "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z",
  reportes_:
    "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  // Icono genérico para categorías nuevas
  default:
    "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
};

// Colores para las categorías (se rotan si hay más categorías)
const colorPalette = [
  "badge-primary",
  "badge-success",
  "badge-warning",
  "badge-error",
  "badge-info",
  "badge-secondary",
  "badge-accent",
];

export const generateCategories = (
  permissions: Permiso[],
): PermissionCategory[] => {
  const prefixes = new Set<string>();

  permissions.forEach((perm) => {
    const prefix = perm.nombre.split("_")[0] + "_";
    if (prefix !== "_") prefixes.add(prefix);
  });

  // Mapeo de nombres especiales
  const nameMap: { [key: string]: string } = {
    admin_: "Administración",
    expediente_: "Expedientes",
    documento_: "Documentos",
    auditoria_: "Auditoría",
    infracciones_: "Infracciones",
    multas_: "Multas",
    usuarios_: "Usuarios",
    reportes_: "Reportes",
  };

  // Convertir prefijos a categorías
  return Array.from(prefixes).map((prefix, index) => {
    // Usar nameMap si existe, si no, capitalizar el prefijo de forma limpia
    const rawName = prefix.replace(/_/g, "");
    const name =
      nameMap[prefix] || rawName.charAt(0).toUpperCase() + rawName.slice(1);

    return {
      name,
      prefix,
      color: colorPalette[index % colorPalette.length],
      icon: iconMap[prefix] || iconMap.default,
    };
  });
};

export const formatPermissionName = (name: string, prefix: string) => {
  return name
    .replace(prefix, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
};
