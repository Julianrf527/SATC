import type { MappingCache } from "./useAuditMappings";

/** Payload de auditoría: JSON arbitrario del backend, sin forma estable que tipar. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AuditData = any;

const FIELD_TRANSLATIONS: Record<string, string> = {
  // Usuario
  usuario_id: "ID Usuario",
  numero_documento: "Número de Documento",
  nombre_completo: "Nombre Completo",
  primer_nombre: "Primer Nombre",
  segundo_nombre: "Segundo Nombre",
  primer_apellido: "Primer Apellido",
  segundo_apellido: "Segundo Apellido",
  correo: "Correo Electrónico",
  rol_id: "Rol",
  rol: "Rol",
  activo: "Estado",
  remember: "Recordar Sesión",
  fecha_login: "Fecha de Inicio de Sesión",

  // Rol
  id: "ID",
  nombre: "Nombre",
  descripcion: "Descripción",
  permisos: "Permisos",

  // Expediente
  radicado: "Radicado",
  nombre_expediente: "Nombre del Expediente",
  fecha_creacion: "Fecha de Creación",
  municipio_id: "Municipio",
  vereda_id: "Vereda",
  vereda_nombre: "Vereda",
  direccion: "Dirección",
  archivado: "Archivado",
  ultima_etapa: "Última Etapa",
  abogado_responsable_id: "Abogado responsable",
  abogado_responsable_nombre: "Abogado responsable",
  abogado_responsable_documento: "Documento abogado responsable",
  encargado_id: "Encargado",
  encargado_nombre: "Encargado",
  encargado_documento: "Documento encargado",
  causa_id: "Causa",
  causa_nombre: "Causa",
  recursos: "Recursos",
  recursos_ids: "Recursos",
  quejosos: "Quejosos",
  quejosos_ids: "Quejosos",
  radicados_asociados: "Radicados asociados",

  // Notificación
  tipo: "Tipo",
  mensaje: "Mensaje",
  titulo: "Título",
  leido: "Leído",
  fecha: "Fecha",

  // Etapa
  etapa_id: "Etapa",
  tipo_etapa_id: "Tipo de Etapa",

  // Involucrado
  tipo_documento: "Tipo de Documento",
  digito_verificacion: "Dígito de Verificación",
  celular: "Teléfono / Celular",
};

export const translateFieldName = (key: string): string => {
  return (
    FIELD_TRANSLATIONS[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
};

export const formatObjectValue = (obj: Record<string, AuditData>): string => {
  const nombre = obj?.nombre ?? obj?.name;
  const documento = obj?.numero_documento ?? obj?.documento;
  if (nombre && documento) return `${nombre} (${documento})`;
  if (nombre) return String(nombre);
  if (obj?.radicado) return String(obj.radicado);
  if (obj?.id && documento) return `ID ${obj.id} (${documento})`;
  return JSON.stringify(obj);
};

export type ValueResolver = (key: string, value: AuditData) => string;

export const createValueResolver =
  (mappingCache: MappingCache): ValueResolver =>
  (key, value) => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "Sí" : "No";

    if (key === "rol_id" && typeof value === "number") {
      return mappingCache.roles[value] || `ID: ${value}`;
    }

    if (key === "municipio_id" && typeof value === "number") {
      return mappingCache.municipios[value] || `ID: ${value}`;
    }

    if (key === "vereda_id" && typeof value === "number") {
      return mappingCache.veredas[value] || `ID: ${value}`;
    }

    if (key === "causa_id" && typeof value === "number") {
      return mappingCache.causas[value] || `ID: ${value}`;
    }

    if (key === "etapa_id" && typeof value === "number") {
      return mappingCache.etapas[value] || `ID: ${value}`;
    }

    if (key === "permisos" && Array.isArray(value)) {
      if (value.length === 0) return "Sin permisos";
      const permisosList = value
        .map((id) => mappingCache.permisos[id] || `ID: ${id}`)
        .join(", ");
      return permisosList;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) return "Sin registros";
      const nonNull = value.filter((item) => item !== null && item !== undefined);
      if (nonNull.every((item) => typeof item === "number")) {
        if (key === "recursos" || key === "recursos_ids") {
          return nonNull
            .map((id) => mappingCache.recursos[id] || `ID: ${id}`)
            .join(", ");
        }
        if (key === "quejosos" || key === "quejosos_ids") {
          return nonNull
            .map((id) => mappingCache.quejosos[id] || `ID: ${id}`)
            .join(", ");
        }
        return nonNull.join(", ");
      }
      if (nonNull.every((item) => typeof item === "string")) {
        return nonNull.join(", ");
      }
      if (nonNull.every((item) => typeof item === "object")) {
        return nonNull.map((item) => formatObjectValue(item)).join(", ");
      }
      return JSON.stringify(value);
    }

    // Activo/Estado
    if (key === "activo") {
      return value ? "Activo" : "Inactivo";
    }

    // Fechas
    if (key.includes("fecha") && typeof value === "string") {
      try {
        const date = new Date(value);
        return date.toLocaleString("es-CO", {
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch {
        return value;
      }
    }

    if (typeof value === "object") {
      return formatObjectValue(value);
    }

    return String(value);
  };

// Filtrar campos relevantes según tipo de operación y tabla
export const getRelevantFields = (
  data: AuditData,
  tablaAfectada: string,
  tipoOperacion: string,
): string[] => {
  if (!data) return [];

  const allKeys = Object.keys(data);

  // Siempre ocultar estos campos técnicos
  const hiddenFields = ["password", "contrasena", "token", "hash", "salt"];
  const shouldHideId = (key: string) =>
    key.endsWith("_id") && allKeys.includes(key.replace(/_id$/, "_nombre"));
  const isHidden = (key: string) =>
    hiddenFields.includes(key) || shouldHideId(key);

  // Filtrado inteligente según tabla y operación
  if (tablaAfectada === "usuario") {
    if (tipoOperacion === "INSERT") {
      // Solo lo importante al crear usuario
      return allKeys.filter(
        (key) =>
          !isHidden(key) &&
          ![
            "remember",
            "fecha_login",
            "ultimo_acceso",
            "intentos_fallidos",
          ].includes(key),
      );
    } else if (tipoOperacion === "UPDATE") {
      // En inicio/cierre de sesión solo mostrar lo relevante
      if (data.fecha_login) {
        return ["usuario_id", "nombre_completo", "fecha_login"];
      }
      // Para otros updates, ocultar campos técnicos
      return allKeys.filter((key) => !isHidden(key) && key !== "remember");
    }
  }

  if (tablaAfectada === "rol") {
    return allKeys.filter((key) => !isHidden(key));
  }

  if (tablaAfectada === "notificacion") {
    return allKeys.filter(
      (key) => !isHidden(key) && !["created_at", "updated_at"].includes(key),
    );
  }

  // Por defecto, mostrar todo excepto campos ocultos
  return allKeys.filter((key) => !isHidden(key));
};

export const getChangedFields = (
  datosAnteriores: AuditData,
  datosNuevos: AuditData,
): string[] => {
  if (!datosAnteriores || !datosNuevos) return [];

  const changed: string[] = [];
  const allKeys = new Set([
    ...Object.keys(datosAnteriores),
    ...Object.keys(datosNuevos),
  ]);

  allKeys.forEach((key) => {
    const oldVal = datosAnteriores[key];
    const newVal = datosNuevos[key];

    if (Array.isArray(oldVal) && Array.isArray(newVal)) {
      if (JSON.stringify(oldVal.sort()) !== JSON.stringify(newVal.sort())) {
        changed.push(key);
      }
    } else if (oldVal !== newVal) {
      changed.push(key);
    }
  });

  return changed;
};
