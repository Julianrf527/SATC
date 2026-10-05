import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiRequest, API_CONFIG } from "@shared/lib/api";
import type { Involucrado } from "@shared/types/involucrado";
import type { VincularInvolucradoInput } from "../types";
import { involucradosExpedienteKeys } from "./queryKeys";

const capitalizeName = (name: string): string =>
  name
    .trim()
    .toLowerCase()
    .split(" ")
    .filter((w) => w.length > 0)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

/**
 * Involucrados vinculados al expediente según el servicio. Devuelve `null` si
 * la respuesta no trae lista (el componente cae a la lista recibida por props).
 */
export function useInvolucradosExpedienteQuery(listarUrl: string) {
  return useQuery({
    queryKey: involucradosExpedienteKeys.list(listarUrl),
    queryFn: async () => {
      const res = await apiRequest<{ data?: { involucrados?: Involucrado[] } }>(
        listarUrl,
      );
      return res.data?.involucrados ?? null;
    },
  });
}

/**
 * Busca un involucrado en app-involved por documento. `null` si no existe.
 * Es una consulta imperativa (al salir del campo), no un query cacheado.
 */
export async function buscarInvolucrado(
  tipo: string,
  numero: string,
  dv?: string,
): Promise<Involucrado | null> {
  const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_SEARCH(tipo, numero, dv));
  return res.ok && res.data ? (res.data as Involucrado) : null;
}

export class InvolucradoYaVinculadoError extends Error {
  constructor() {
    super("Este involucrado ya está vinculado al expediente");
    this.name = "InvolucradoYaVinculadoError";
  }
}

/**
 * Crea el involucrado en app-involved (si no existía) y lo vincula al
 * expediente. Devuelve el involucrado vinculado.
 */
export function useVincularInvolucradoMutation(
  vincularUrl: string,
  expedienteId: number,
  listarUrl: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      formData,
      existingInvolucrado,
      actuales,
    }: VincularInvolucradoInput): Promise<Involucrado> => {
      let invData: Involucrado;
      const esNit = formData.tipo_documento === "NIT";
      const celular = formData.celular.trim()
        ? parseInt(formData.celular.trim())
        : null;

      if (!existingInvolucrado) {
        const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_CREATE, {
          method: "POST",
          body: JSON.stringify({
            numero_documento: formData.numero_documento.trim(),
            digito_verificacion: esNit ? formData.digito_verificacion : null,
            tipo_documento: formData.tipo_documento,
            nombre: capitalizeName(formData.nombre),
            celular,
            correo: formData.correo.trim()
              ? formData.correo.trim().toLowerCase()
              : null,
            direccion: formData.direccion.trim() || null,
          }),
        });
        if (!res?.ok) throw new Error("Error al crear el involucrado");
        invData = {
          id: res.data.id,
          numero_documento: parseInt(formData.numero_documento.trim()),
          digito_verificacion: esNit ? formData.digito_verificacion : null,
          tipo_documento: formData.tipo_documento,
          nombre: capitalizeName(formData.nombre),
          celular,
          correo: formData.correo.trim().toLowerCase() || null,
          direccion: formData.direccion.trim() || null,
        };
      } else {
        invData = {
          ...existingInvolucrado,
          numero_documento: parseInt(
            existingInvolucrado.numero_documento.toString(),
          ),
          celular:
            existingInvolucrado.celular != null
              ? parseInt(existingInvolucrado.celular.toString())
              : null,
        };
      }

      const yaExiste = actuales.some(
        (i) =>
          i.id === invData.id ||
          (i.numero_documento == invData.numero_documento &&
            i.tipo_documento === invData.tipo_documento),
      );
      if (yaExiste) throw new InvolucradoYaVinculadoError();

      const link = await apiCall(vincularUrl, {
        method: "POST",
        body: JSON.stringify({
          expediente_id: expedienteId,
          involucrado_id: invData.id,
        }),
      });
      if (!link?.ok) throw new Error(link?.detail || "Error al vincular");
      return invData;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: involucradosExpedienteKeys.list(listarUrl),
      }),
  });
}

/** Desvincula un involucrado del expediente (no lo borra de app-involved). */
export function useDesvincularInvolucradoMutation(
  desvincular: (id: number) => string,
  listarUrl: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (involucradoId: number) =>
      apiRequest(desvincular(involucradoId), { method: "DELETE" }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: involucradosExpedienteKeys.list(listarUrl),
      }),
  });
}
