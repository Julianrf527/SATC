import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, jsonBody, RECURSO_ENDPOINTS } from "@shared/lib/api";
import { downloadBlobFile } from "@shared/lib/downloadFile";
import { generateDocumentFileName, uploadFileToDocuments } from "@shared/lib/fileUpload";
import type { ExpedienteDetalle, ListaExpedientesResponse } from "../types";
import {
  construirExpedienteDatos,
  type ExpedienteFormState,
} from "../manage/expediente-form/expedienteForm";
import { estadoError } from "./errors";
import { invalidarExpediente } from "./invalidar";
import { construirQueryLista, type FiltrosListaExpedientes } from "./listaParams";
import { recursoKeys } from "./queryKeys";

/** Listado paginado con filtros en el backend (Gestionar y Consulta comparten caché). */
export function useExpedientesQuery(filtros: FiltrosListaExpedientes, enabled = true) {
  return useQuery({
    queryKey: recursoKeys.lista(filtros),
    queryFn: () =>
      apiRequest<ListaExpedientesResponse>(
        `${RECURSO_ENDPOINTS.RECURSO_EXPEDIENTES}?${construirQueryLista(filtros)}`,
      ),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 0,
  });
}

/**
 * Detalle del expediente (información base + involucrados + etapas). Es la
 * fuente de verdad del panel: cada mutación invalida esta clave.
 */
export function useExpedienteDetalleQuery(expedienteId: number | null | undefined) {
  return useQuery({
    queryKey: recursoKeys.detalle(expedienteId ?? 0),
    queryFn: async () =>
      (await apiRequest<{ data: ExpedienteDetalle }>(RECURSO_ENDPOINTS.RECURSO_EXPEDIENTE(expedienteId as number)))
        .data,
    enabled: !!expedienteId,
    staleTime: 0,
  });
}

/** Sube el comprobante a app-docs (como infraction) y devuelve su `file_id`. */
async function subirComprobante(archivo: File, radicado: string): Promise<number> {
  const hoy = new Date().toISOString().split("T")[0];
  return uploadFileToDocuments(archivo, generateDocumentFileName("COMPROBANTE_PAGO", radicado.trim(), hoy));
}

type CreadoResponse = { data: { id: number; expediente: string; version: number }; message?: string };

/** POST /recurso/expedientes: sube el comprobante y crea el expediente. */
export function useCrearExpedienteMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (form: ExpedienteFormState) => {
      if (!form.comprobante) throw new Error("Adjunte el comprobante de pago (PDF)");
      const fileId = await subirComprobante(form.comprobante, form.radicado);
      return apiRequest<CreadoResponse>(RECURSO_ENDPOINTS.RECURSO_EXPEDIENTES, {
        method: "POST",
        ...jsonBody(construirExpedienteDatos(form, fileId)),
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recursoKeys.listaExpedientes() }),
  });
}

/**
 * PUT /recurso/expedientes/{id} con la `version` leída (bloqueo optimista).
 * Si llega un PDF nuevo se sube antes; el backend ajusta los contadores de
 * uso. Ante 409 se recarga el detalle (el componente muestra el aviso).
 */
export function useActualizarExpedienteMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ form, version }: { form: ExpedienteFormState; version: number }) => {
      const fileId = form.comprobante
        ? await subirComprobante(form.comprobante, form.radicado)
        : (form.doc_comprobante_pago_id as number);
      return apiRequest<{ data: { id: number; version: number } }>(
        RECURSO_ENDPOINTS.RECURSO_EXPEDIENTE(expedienteId),
        { method: "PUT", ...jsonBody({ ...construirExpedienteDatos(form, fileId), version }) },
      );
    },
    onSuccess: () => invalidarExpediente(queryClient, expedienteId),
    onError: (err) => {
      if (estadoError(err) === 409) void invalidarExpediente(queryClient, expedienteId);
    },
  });
}

/** Índice de documentos que entran en la descarga (A.5). */
export function useDocumentosExpedienteQuery(expedienteId: number | null, enabled = true) {
  return useQuery({
    queryKey: recursoKeys.documentos(expedienteId ?? 0),
    queryFn: async () =>
      (
        await apiRequest<{ data?: { file_id: number; descripcion: string }[] }>(
          RECURSO_ENDPOINTS.RECURSO_EXPEDIENTE_DOCUMENTOS(expedienteId as number),
        )
      ).data ?? [],
    enabled: enabled && !!expedienteId,
  });
}

/** PDF unificado del expediente (descarga de blob, como infraction). */
export function descargarExpedienteCompleto(expedienteId: number, codigo: string) {
  const nombre = `concesion_${codigo.replace(/\s+/g, "_") || expedienteId}_completo.pdf`;
  return downloadBlobFile(RECURSO_ENDPOINTS.RECURSO_EXPEDIENTE_DESCARGAR(expedienteId), nombre);
}
