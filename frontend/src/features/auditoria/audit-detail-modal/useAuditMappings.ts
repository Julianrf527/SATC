import { useMemo } from "react";
import { API_CONFIG } from "@shared/lib/api";
import type { AuditMappingSources } from "../types";
import {
  useCatalogoQuery,
  useEtapasNombresQuery,
  type CatalogoItem,
} from "../api/catalogos";
import type { AuditData } from "./auditFormatters";

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

const toNameMap = (items: CatalogoItem[] | undefined) => {
  const map: Record<number, string> = {};
  (items ?? []).forEach((it) => {
    map[it.id] = (it.nombre ?? it.name) as string;
  });
  return map;
};

const extractEtapaIds = (...objs: AuditData[]): number[] => {
  const ids = new Set<number>();
  objs.forEach((obj) => {
    if (!obj || typeof obj !== "object") return;
    const value = (obj as Record<string, unknown>).etapa_id;
    if (typeof value === "number") ids.add(value);
  });
  return Array.from(ids).sort((a, b) => a - b);
};

/**
 * Mapeos ID -> nombre para el detalle de auditoría. Cada catálogo es un query
 * cacheado por URL; solo se piden con el modal abierto.
 */
export function useAuditMappings(
  isOpen: boolean,
  sources: AuditMappingSources,
  datosAnteriores: AuditData,
  datosNuevos: AuditData,
) {
  const roles = useCatalogoQuery(API_CONFIG.ENDPOINTS.ROLES, isOpen);
  const permisos = useCatalogoQuery(API_CONFIG.ENDPOINTS.PERMISSIONS, isOpen);
  const municipios = useCatalogoQuery(sources.municipios, isOpen);
  const recursos = useCatalogoQuery(sources.recursos, isOpen);
  const causas = useCatalogoQuery(sources.causas, isOpen);
  const quejosos = useCatalogoQuery(sources.quejosos, isOpen);

  const etapaIds = useMemo(
    () => extractEtapaIds(datosAnteriores, datosNuevos),
    [datosAnteriores, datosNuevos],
  );
  const etapas = useEtapasNombresQuery(etapaIds, isOpen);

  const mappingCache = useMemo<MappingCache>(() => {
    const veredas: Record<number, string> = {};
    (municipios.data ?? []).forEach((mun) => {
      (mun.veredas || []).forEach((vereda) => {
        if (vereda?.id) veredas[vereda.id] = (vereda.nombre ?? vereda.name) as string;
      });
    });
    return {
      roles: toNameMap(roles.data),
      permisos: toNameMap(permisos.data),
      municipios: toNameMap(municipios.data),
      veredas,
      etapas: etapas.data ?? {},
      recursos: toNameMap(recursos.data),
      causas: toNameMap(causas.data),
      quejosos: toNameMap(quejosos.data),
    };
  }, [roles.data, permisos.data, municipios.data, recursos.data, causas.data, quejosos.data, etapas.data]);

  // `isLoading` (no `isPending`): un query deshabilitado no cuenta como cargando.
  const loading = [roles, permisos, municipios, recursos, causas, quejosos, etapas].some(
    (q) => q.isLoading,
  );

  return { mappingCache, loading };
}
