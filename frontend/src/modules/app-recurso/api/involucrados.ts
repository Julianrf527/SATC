import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiRequest, INVOLVED_ENDPOINTS, jsonBody, RECURSO_ENDPOINTS } from "@shared/lib/api";
import type { PersonaInvolucrada, VinculoInvolucrado } from "../types";
import { estadoError } from "./errors";
import { PERSONA_VACIA, type PersonaForm } from "./personaForm";

export { PERSONA_VACIA, type PersonaForm };
import { invalidarExpediente } from "./invalidar";

/**
 * Personas en app-involved (igual que infraction: se buscan por documento y,
 * si no existen, se crean) y vínculos con el expediente en app-recurso (A.4).
 */

/** Busca una persona por documento. `null` si no existe (o el servicio no respondió). */
export async function buscarPersona(tipo: string, numero: string, dv?: string): Promise<PersonaInvolucrada | null> {
  const res = await apiCall(INVOLVED_ENDPOINTS.INVOLVED_SEARCH(tipo, numero, dv));
  return res.ok && res.data ? (res.data as PersonaInvolucrada) : null;
}

const capitalizar = (nombre: string) =>
  nombre
    .trim()
    .toLowerCase()
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

/** Crea la persona en app-involved y devuelve su id. */
export async function crearPersona(f: PersonaForm): Promise<number> {
  const esNit = f.tipo_documento === "NIT";
  const res = await apiCall(INVOLVED_ENDPOINTS.INVOLVED_CREATE, {
    method: "POST",
    ...jsonBody({
      numero_documento: f.numero_documento.trim(),
      digito_verificacion: esNit ? f.digito_verificacion : null,
      tipo_documento: f.tipo_documento,
      nombre: capitalizar(f.nombre),
      celular: f.celular.trim() ? parseInt(f.celular.trim(), 10) : null,
      correo: f.correo.trim() ? f.correo.trim().toLowerCase() : null,
      direccion: f.direccion.trim() || null,
    }),
  });
  const id = res.ok ? (res.data?.id as number | undefined) : undefined;
  if (!id) throw new Error(res.detail || "Error al crear la persona en el registro de involucrados");
  return id;
}

/** Id de la persona: la encontrada o una recién creada. */
export async function resolverPersona(existente: PersonaInvolucrada | null, form: PersonaForm): Promise<number> {
  return existente ? existente.id : crearPersona(form);
}

/** Tras cualquier cambio de vínculos: recargar detalle y listado (409 incluido). */
function useInvalidacion(expedienteId: number) {
  const queryClient = useQueryClient();
  return {
    onSuccess: () => invalidarExpediente(queryClient, expedienteId),
    onError: (err: unknown) => {
      if (estadoError(err) === 409) void invalidarExpediente(queryClient, expedienteId);
    },
  };
}

/** POST /involucrados/vinculos (solicitante; `representante_id` obligatorio si es NIT, V14). */
export function useVincularSolicitanteMutation(expedienteId: number) {
  return useMutation({
    mutationFn: (body: { involucrado_id: number; representante_id: number | null }) =>
      apiRequest<{ data: VinculoInvolucrado; message?: string }>(RECURSO_ENDPOINTS.RECURSO_VINCULOS, {
        method: "POST",
        ...jsonBody({
          expediente_id: expedienteId,
          involucrado_id: body.involucrado_id,
          ...(body.representante_id ? { representante_id: body.representante_id } : {}),
        }),
      }),
    ...useInvalidacion(expedienteId),
  });
}

/** PATCH representante del vínculo (con `version`). */
export function useCambiarRepresentanteMutation(expedienteId: number) {
  return useMutation({
    mutationFn: ({ vinculo, representanteId }: { vinculo: VinculoInvolucrado; representanteId: number | null }) =>
      apiRequest(RECURSO_ENDPOINTS.RECURSO_VINCULO_REPRESENTANTE(vinculo.id), {
        method: "PATCH",
        ...jsonBody({ representante_id: representanteId, version: vinculo.version }),
      }),
    ...useInvalidacion(expedienteId),
  });
}

/** DELETE del vínculo (con `version`). No borra la persona de app-involved. */
export function useDesvincularMutation(expedienteId: number) {
  return useMutation({
    mutationFn: (vinculo: VinculoInvolucrado) =>
      apiRequest(RECURSO_ENDPOINTS.RECURSO_VINCULO_DELETE(vinculo.id, vinculo.version), { method: "DELETE" }),
    ...useInvalidacion(expedienteId),
  });
}

// ─── Terceros intervinientes (C.10) ─────────────────────────────────────────

/** POST /terceros (`representante_id` obligatorio si es NIT, V14). */
export function useVincularTerceroMutation(expedienteId: number) {
  return useMutation({
    mutationFn: (body: { involucrado_id: number; representante_id: number | null }) =>
      apiRequest<{ data: VinculoInvolucrado; message?: string }>(RECURSO_ENDPOINTS.RECURSO_TERCEROS, {
        method: "POST",
        ...jsonBody({
          expediente_id: expedienteId,
          involucrado_id: body.involucrado_id,
          ...(body.representante_id ? { representante_id: body.representante_id } : {}),
        }),
      }),
    ...useInvalidacion(expedienteId),
  });
}

/** PATCH representante del tercero (con `version`). */
export function useCambiarRepresentanteTerceroMutation(expedienteId: number) {
  return useMutation({
    mutationFn: ({ vinculo, representanteId }: { vinculo: VinculoInvolucrado; representanteId: number | null }) =>
      apiRequest(RECURSO_ENDPOINTS.RECURSO_TERCERO_REPRESENTANTE(vinculo.id), {
        method: "PATCH",
        ...jsonBody({ representante_id: representanteId, version: vinculo.version }),
      }),
    ...useInvalidacion(expedienteId),
  });
}

/** DELETE del tercero (con `version`; 409 si ya tiene acto o notificaciones). */
export function useDesvincularTerceroMutation(expedienteId: number) {
  return useMutation({
    mutationFn: (vinculo: Pick<VinculoInvolucrado, "id" | "version">) =>
      apiRequest(RECURSO_ENDPOINTS.RECURSO_TERCERO_DELETE(vinculo.id, vinculo.version), { method: "DELETE" }),
    ...useInvalidacion(expedienteId),
  });
}
