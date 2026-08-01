import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import type { AuditData } from "./auditFormatters";

export type AuditScope = "sanctioning" | "infraction" | "involved";

export type MappingCache = {
  roles: Record<number, string>;
  permisos: Record<number, string>;
  municipios: Record<number, string>;
  veredas: Record<number, string>;
  etapas: Record<number, string>;
  recursos: Record<number, string>;
  causas: Record<number, string>;
  quejosos: Record<number, string>;
};

const EMPTY_CACHE: MappingCache = {
  roles: {},
  permisos: {},
  municipios: {},
  veredas: {},
  etapas: {},
  recursos: {},
  causas: {},
  quejosos: {},
};

/**
 * Carga los mapeos ID -> nombre necesarios para renderizar el detalle de auditoría.
 * Se dispara al abrir el modal o al cambiar el ámbito de auditoría.
 */
export function useAuditMappings(
  isOpen: boolean,
  auditScope: AuditScope,
  datosAnteriores: AuditData,
  datosNuevos: AuditData,
) {
  const [mappingCache, setMappingCache] = useState<MappingCache>(EMPTY_CACHE);
  const [loading, setLoading] = useState(true);

  const isInfraction = auditScope === "infraction";
  const isInvolved = auditScope === "involved";

  useEffect(() => {
    if (isOpen) {
      loadMappings();
    }
  }, [isOpen, auditScope]);

  const loadMappings = async () => {
    setLoading(true);
    try {
      const rolesRes = await apiCall(API_CONFIG.ENDPOINTS.ROLES, {
        method: "GET",
      });
      const rolesMap: Record<number, string> = {};
      if (rolesRes.ok && rolesRes.data) {
        rolesRes.data.forEach((rol: any) => {
          rolesMap[rol.id] = rol.nombre;
        });
      }

      const permisosRes = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
        method: "GET",
      });
      const permisosMap: Record<number, string> = {};
      if (permisosRes.ok && permisosRes.data) {
        permisosRes.data.forEach((permiso: any) => {
          permisosMap[permiso.id] = permiso.nombre;
        });
      }

      const municipiosMap: Record<number, string> = {};
      const veredasMap: Record<number, string> = {};
      const recursosMap: Record<number, string> = {};

      if (!isInvolved) {
        const townsEndpoint = isInfraction
          ? API_CONFIG.ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT
          : API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK;
        const resourcesEndpoint = isInfraction
          ? API_CONFIG.ENDPOINTS.INFRACTION_AFFECTED_RESOURCE
          : API_CONFIG.ENDPOINTS.FILE_AFFECTED_RESOURCE;

        const municipiosRes = await apiCall(townsEndpoint, { method: "GET" });
        if (municipiosRes.ok && municipiosRes.data) {
          municipiosRes.data.forEach((mun: any) => {
            municipiosMap[mun.id] = mun.nombre ?? mun.name;
            (mun.veredas || []).forEach((vereda: any) => {
              if (vereda?.id)
                veredasMap[vereda.id] = vereda.nombre ?? vereda.name;
            });
          });
        }

        const recursosRes = await apiCall(resourcesEndpoint, { method: "GET" });
        if (recursosRes.ok && recursosRes.data) {
          recursosRes.data.forEach((rec: any) => {
            recursosMap[rec.id] = rec.nombre ?? rec.name;
          });
        }
      }

      // Cargar causas y quejosos (solo infracciones)
      const causasMap: Record<number, string> = {};
      const quejososMap: Record<number, string> = {};
      if (isInfraction) {
        const causasRes = await apiCall(
          API_CONFIG.ENDPOINTS.INFRACTION_TIPOS_AFECTACION,
          {
            method: "GET",
          },
        );
        if (causasRes.ok && causasRes.data) {
          causasRes.data.forEach((causa: any) => {
            causasMap[causa.id] = causa.nombre ?? causa.name;
          });
        }

        const quejososRes = await apiCall(
          API_CONFIG.ENDPOINTS.INFRACTION_COMPLAINER,
          {
            method: "GET",
          },
        );
        if (quejososRes.ok && quejososRes.data) {
          quejososRes.data.forEach((quejoso: any) => {
            quejososMap[quejoso.id] = quejoso.nombre ?? quejoso.name;
          });
        }
      }

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

      const etapasMap: Record<number, string> = {};
      if (etapaIds.size > 0) {
        try {
          const etapasRes = await apiCall(
            API_CONFIG.ENDPOINTS.AUDIT_ETAPAS_BATCH,
            {
              method: "POST",
              body: JSON.stringify(Array.from(etapaIds)),
            },
          );
          if (etapasRes.ok && etapasRes.data) {
            Object.assign(etapasMap, etapasRes.data);
          }
        } catch (error) {
          // Silencioso: las etapas son un enriquecimiento opcional
        }
      }

      setMappingCache({
        roles: rolesMap,
        permisos: permisosMap,
        municipios: municipiosMap,
        veredas: veredasMap,
        etapas: etapasMap,
        recursos: recursosMap,
        causas: causasMap,
        quejosos: quejososMap,
      });
    } catch (error) {
      // Silencioso: sin mapeos el modal degrada a mostrar los IDs crudos.
    } finally {
      setLoading(false);
    }
  };

  return { mappingCache, loading };
}
