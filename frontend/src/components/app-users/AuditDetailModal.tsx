import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../utils/api";

type AuditDetailModalProps = {
  isOpen: boolean;
  onClose: () => void;
  titulo: string;
  tipoOperacion: string;
  tablaAfectada: string;
  datosAnteriores: any;
  datosNuevos: any;
};

type MappingCache = {
  roles: Record<number, string>;
  permisos: Record<number, string>;
  municipios: Record<number, string>;
  veredas: Record<number, string>;
  etapas: Record<number, string>;
};

export default function AuditDetailModal({
  isOpen,
  onClose,
  tipoOperacion,
  tablaAfectada,
  datosAnteriores,
  datosNuevos,
}: AuditDetailModalProps) {
  const [mappingCache, setMappingCache] = useState<MappingCache>({
    roles: {},
    permisos: {},
    municipios: {},
    veredas: {},
    etapas: {},
  });
  const [loading, setLoading] = useState(true);

  // Cargar mapeos al montar el componente
  useEffect(() => {
    if (isOpen) {
      loadMappings();
    }
  }, [isOpen]);

  const loadMappings = async () => {
    setLoading(true);
    try {
      // Cargar roles
      const rolesRes = await apiCall(API_CONFIG.ENDPOINTS.ROLES, {
        method: "GET",
      });
      const rolesMap: Record<number, string> = {};
      if (rolesRes.ok && rolesRes.data) {
        rolesRes.data.forEach((rol: any) => {
          rolesMap[rol.id] = rol.nombre;
        });
      }

      // Cargar permisos
      const permisosRes = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
        method: "GET",
      });
      const permisosMap: Record<number, string> = {};
      if (permisosRes.ok && permisosRes.data) {
        permisosRes.data.forEach((permiso: any) => {
          permisosMap[permiso.id] = permiso.nombre;
        });
      }

      // Cargar municipios
      const municipiosRes = await apiCall(API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK, {
        method: "GET",
      });
      const municipiosMap: Record<number, string> = {};
      if (municipiosRes.ok && municipiosRes.data) {
        municipiosRes.data.forEach((mun: any) => {
          municipiosMap[mun.id] = mun.name;
        });
      }

      // Extraer IDs de etapa de los datos
      const etapaIds = new Set<number>();
      const extractEtapaIds = (obj: any) => {
        if (!obj) return;
        Object.entries(obj).forEach(([key, value]) => {
          if (key === "etapa_id" && typeof value === "number") {
            etapaIds.add(value);
          }
        });
      };
      extractEtapaIds(datosAnteriores);
      extractEtapaIds(datosNuevos);

      // Cargar etapas si hay IDs
      const etapasMap: Record<number, string> = {};
      if (etapaIds.size > 0) {
        try {
          const etapasRes = await apiCall(API_CONFIG.ENDPOINTS.AUDIT_ETAPAS_BATCH, {
            method: "POST",
            body: JSON.stringify(Array.from(etapaIds)),
          });
          if (etapasRes.ok && etapasRes.data) {
            Object.assign(etapasMap, etapasRes.data);
          }
        } catch (error) {
          console.error("Error cargando etapas:", error);
        }
      }

      setMappingCache({
        roles: rolesMap,
        permisos: permisosMap,
        municipios: municipiosMap,
        veredas: {},
        etapas: etapasMap,
      });
    } catch (error) {
      console.error("Error cargando mapeos:", error);
    } finally {
      setLoading(false);
    }
  };

  // Traducir nombres técnicos a español
  const translateFieldName = (key: string): string => {
    const translations: Record<string, string> = {
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
      direccion: "Dirección",
      archivado: "Archivado",
      ultima_etapa: "Última Etapa",

      // Notificación
      tipo: "Tipo",
      mensaje: "Mensaje",
      titulo: "Título",
      leido: "Leído",
      fecha: "Fecha",

      // Etapa
      etapa_id: "Etapa",
      tipo_etapa_id: "Tipo de Etapa",
    };

    return translations[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  // Resolver valor (convertir IDs a nombres)
  const resolveValue = (key: string, value: any): string => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "Sí" : "No";

    // Resolver rol_id
    if (key === "rol_id" && typeof value === "number") {
      return mappingCache.roles[value] || `ID: ${value}`;
    }

    // Resolver municipio_id
    if (key === "municipio_id" && typeof value === "number") {
      return mappingCache.municipios[value] || `ID: ${value}`;
    }

    // Resolver etapa_id
    if (key === "etapa_id" && typeof value === "number") {
      return mappingCache.etapas[value] || `ID: ${value}`;
    }

    // Resolver array de permisos
    if (key === "permisos" && Array.isArray(value)) {
      if (value.length === 0) return "Sin permisos";
      const permisosList = value
        .map((id) => mappingCache.permisos[id] || `ID: ${id}`)
        .join(", ");
      return permisosList;
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

    return String(value);
  };

  // Filtrar campos relevantes según tipo de operación y tabla
  const getRelevantFields = (data: any): string[] => {
    if (!data) return [];

    const allKeys = Object.keys(data);

    // Siempre ocultar estos campos técnicos
    const hiddenFields = ["password", "contrasena", "token", "hash", "salt"];

    // Filtrado inteligente según tabla y operación
    if (tablaAfectada === "usuario") {
      if (tipoOperacion === "INSERT") {
        // Solo lo importante al crear usuario
        return allKeys.filter(
          (key) =>
            !hiddenFields.includes(key) &&
            ![
              "remember",
              "fecha_login",
              "ultimo_acceso",
              "intentos_fallidos",
            ].includes(key)
        );
      } else if (tipoOperacion === "UPDATE") {
        // En inicio/cierre de sesión solo mostrar lo relevante
        if (data.fecha_login) {
          return ["usuario_id", "nombre_completo", "fecha_login"];
        }
        // Para otros updates, ocultar campos técnicos
        return allKeys.filter(
          (key) => !hiddenFields.includes(key) && key !== "remember"
        );
      }
    }

    if (tablaAfectada === "rol") {
      return allKeys.filter((key) => !hiddenFields.includes(key));
    }

    if (tablaAfectada === "notificacion") {
      return allKeys.filter(
        (key) => !hiddenFields.includes(key) && !["created_at", "updated_at"].includes(key)
      );
    }

    // Por defecto, mostrar todo excepto campos ocultos
    return allKeys.filter((key) => !hiddenFields.includes(key));
  };

  // Detectar campos que cambiaron
  const getChangedFields = (): string[] => {
    if (!datosAnteriores || !datosNuevos) return [];

    const changed: string[] = [];
    const allKeys = new Set([
      ...Object.keys(datosAnteriores),
      ...Object.keys(datosNuevos),
    ]);

    allKeys.forEach((key) => {
      const oldVal = datosAnteriores[key];
      const newVal = datosNuevos[key];

      // Comparar arrays
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

  const renderOperationIcon = () => {
    const icons = {
      INSERT: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4v16m8-8H4"
          />
        </svg>
      ),
      UPDATE: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      ),
      DELETE: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      ),
    };
    return icons[tipoOperacion as keyof typeof icons] || icons.UPDATE;
  };

  const renderInsertView = () => {
    const fields = getRelevantFields(datosNuevos);

    return (
      <div className="space-y-4">
        <div className="alert alert-success">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Nuevo registro creado en la tabla <strong>{tablaAfectada}</strong></span>
        </div>

        <div className="bg-base-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3 text-success flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Datos Creados
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {fields.map((key) => (
              <div key={key} className="flex justify-between items-start border-b border-base-300 pb-2">
                <span className="font-medium text-base-content/80">
                  {translateFieldName(key)}:
                </span>
                <span className="text-right max-w-md break-words">
                  {resolveValue(key, datosNuevos[key])}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderUpdateView = () => {
    const changedFields = getChangedFields();

    // Si es inicio/cierre de sesión, vista simplificada
    if (datosNuevos?.fecha_login) {
      return (
        <div className="space-y-4">
          <div className="alert alert-info">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>Evento de sesión de usuario</span>
          </div>

          <div className="bg-base-200 rounded-lg p-4">
            <div className="space-y-3">
              {["usuario_id", "nombre_completo", "fecha_login"].map((key) => (
                datosNuevos[key] && (
                  <div key={key} className="flex justify-between items-start">
                    <span className="font-medium text-base-content/80">
                      {translateFieldName(key)}:
                    </span>
                    <span className="text-right">{resolveValue(key, datosNuevos[key])}</span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>
      );
    }

    if (changedFields.length === 0) {
      return (
        <div className="alert alert-warning">
          <span>No se detectaron cambios en los datos</span>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="alert alert-warning">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>
            Se modificaron <strong>{changedFields.length}</strong> campo(s) en{" "}
            <strong>{tablaAfectada}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Datos Anteriores */}
          <div className="bg-error/10 rounded-lg p-4 border-2 border-error/20">
            <h4 className="font-semibold mb-3 text-error flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Valores Anteriores
            </h4>
            <div className="space-y-3">
              {changedFields.map((key) => (
                <div key={key} className="bg-base-100 rounded p-2">
                  <div className="font-medium text-sm text-base-content/70 mb-1">
                    {translateFieldName(key)}
                  </div>
                  <div className="text-error font-medium break-words">
                    {resolveValue(key, datosAnteriores[key])}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Datos Nuevos */}
          <div className="bg-success/10 rounded-lg p-4 border-2 border-success/20">
            <h4 className="font-semibold mb-3 text-success flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Valores Nuevos
            </h4>
            <div className="space-y-3">
              {changedFields.map((key) => (
                <div key={key} className="bg-base-100 rounded p-2">
                  <div className="font-medium text-sm text-base-content/70 mb-1">
                    {translateFieldName(key)}
                  </div>
                  <div className="text-success font-medium break-words">
                    {resolveValue(key, datosNuevos[key])}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderDeleteView = () => {
    const fields = getRelevantFields(datosAnteriores);

    return (
      <div className="space-y-4">
        <div className="alert alert-error">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>Registro eliminado de la tabla <strong>{tablaAfectada}</strong></span>
        </div>

        <div className="bg-base-200 rounded-lg p-4">
          <h4 className="font-semibold mb-3 text-error flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            Datos Eliminados
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {fields.map((key) => (
              <div key={key} className="flex justify-between items-start border-b border-base-300 pb-2">
                <span className="font-medium text-base-content/80">
                  {translateFieldName(key)}:
                </span>
                <span className="text-right max-w-md break-words">
                  {resolveValue(key, datosAnteriores[key])}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  const operationColors = {
    INSERT: "text-success",
    UPDATE: "text-warning",
    DELETE: "text-error",
  };

  const operationNames = {
    INSERT: "Creación",
    UPDATE: "Actualización",
    DELETE: "Eliminación",
  };

  return (
    <div className="modal modal-open">
      <div className="modal-box max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center ${
              tipoOperacion === "INSERT"
                ? "bg-success/20"
                : tipoOperacion === "UPDATE"
                ? "bg-warning/20"
                : "bg-error/20"
            } ${operationColors[tipoOperacion as keyof typeof operationColors]}`}
          >
            {renderOperationIcon()}
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-xl">
              {operationNames[tipoOperacion as keyof typeof operationNames]} -{" "}
              {tablaAfectada.charAt(0).toUpperCase() + tablaAfectada.slice(1)}
            </h3>
            <p className="text-sm text-base-content/60">
              Detalles completos de la operación realizada
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm btn-circle"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <span className="loading loading-spinner loading-lg text-success"></span>
            </div>
          ) : tipoOperacion === "INSERT" ? (
            renderInsertView()
          ) : tipoOperacion === "UPDATE" ? (
            renderUpdateView()
          ) : tipoOperacion === "DELETE" ? (
            renderDeleteView()
          ) : (
            <div className="alert alert-info">
              <span>Tipo de operación desconocido</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-action mt-4 pt-4 border-t border-base-300">
          <button className="btn btn-ghost" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
      <div className="modal-backdrop bg-black/50" onClick={onClose}></div>
    </div>
  );
}
