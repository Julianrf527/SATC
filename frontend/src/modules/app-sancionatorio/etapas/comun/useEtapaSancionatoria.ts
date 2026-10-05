import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { ApiError } from "@shared/lib/api";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import {
  useCrearEtapaMutation,
  useEtapaQuery,
  type EtapaClave,
} from "../../api/etapas";
import { sancionatorioKeys } from "../../api/queryKeys";
import type { Creable, DocumentoAnexo, EtapaBase, EtapaRespuesta, SetToast } from "../../types";

const CREABLE_POR_DEFECTO: Creable = { status: true, msg: "" };

type Opciones<T> = {
  etapa: EtapaClave;
  expedienteId: number;
  nombreEtapa: string;
  /** Toast cuando falla el GET de la etapa. */
  mensajeErrorCarga: string;
  setToast: SetToast;
  onStageUpdate: (stage: string) => void;
  /**
   * Qué hacer si el backend rechaza la creación con un 4xx:
   *  - "bloquear": mostrar el panel "No es posible gestionar o crear esta etapa".
   *  - "avisar": solo un toast con el detalle.
   */
  alRechazarCreacion: "bloquear" | "avisar";
  /** Campos extra con los que se siembra la etapa recién creada. */
  semilla?: Partial<T>;
};

/**
 * Estado común de una etapa: datos (react-query), documentos, existencia del
 * acto administrativo, condición `creable` (raíz de la respuesta del GET) y
 * creación de la etapa.
 *
 * Los cambios locales (acto creado, documentos) se escriben en la caché de la
 * etapa con `actualizarDatos`, así toda la pantalla lee de una sola fuente.
 */
export function useEtapaSancionatoria<T extends EtapaBase>({
  etapa,
  expedienteId,
  nombreEtapa,
  mensajeErrorCarga,
  setToast,
  onStageUpdate,
  alRechazarCreacion,
  semilla,
}: Opciones<T>) {
  const queryClient = useQueryClient();
  const queryKey = sancionatorioKeys.etapa(expedienteId, etapa);
  const query = useEtapaQuery<T>(etapa, expedienteId);
  const crear = useCrearEtapaMutation(etapa, expedienteId);
  const [creableLocal, setCreableLocal] = useState<Creable | null>(null);

  const { error } = query;
  useEffect(() => {
    if (!error) return;
    const detalle = error instanceof ApiError ? error.data?.detail : undefined;
    setToast({
      id: Date.now(),
      message: typeof detalle === "string" && detalle ? detalle : mensajeErrorCarga,
      type: "error",
    });
  }, [error, mensajeErrorCarga, setToast]);

  const datos = query.data?.datos ?? null;

  const actualizarDatos = useCallback(
    (cambio: (actual: T) => T) =>
      queryClient.setQueryData<EtapaRespuesta<T>>(
        sancionatorioKeys.etapa(expedienteId, etapa),
        (actual) => ({
          creable: actual?.creable ?? null,
          datos: cambio((actual?.datos ?? {}) as T),
        }),
      ),
    [queryClient, etapa, expedienteId],
  );

  const setDocumentos = useCallback(
    (documentos: DocumentoAnexo[]) =>
      actualizarDatos((d) => ({ ...d, documentos_anexos: documentos })),
    [actualizarDatos],
  );

  /** Para `onActoAdminUpdate` del ActoAdmin principal de la etapa. */
  const setActo = useCallback(
    (acto: ActoAdministrativo) => actualizarDatos((d) => ({ ...d, acto_admin: { ...acto } })),
    [actualizarDatos],
  );

  const crearEtapa = () => {
    if (!expedienteId) {
      setToast({ id: Date.now(), message: "No se ha seleccionado un expediente.", type: "error" });
      return;
    }
    crear.mutate(undefined, {
      onSuccess: (etapaId) => {
        queryClient.setQueryData<EtapaRespuesta<T>>(queryKey, (actual) => ({
          creable: actual?.creable ?? null,
          datos: {
            ...semilla,
            id: etapaId,
            etapa_id: etapaId,
            acto_admin: {},
            documentos_anexos: [],
          } as unknown as T,
        }));
        // Trae los campos que calcula el backend (p. ej. creable_acto_recurso).
        void query.refetch();
        onStageUpdate(nombreEtapa);
        setToast({ id: Date.now(), message: "Etapa creada exitosamente.", type: "success" });
      },
      onError: (e) => {
        const status = e instanceof ApiError ? e.status : 0;
        const detalle = e instanceof ApiError ? e.message : "";
        if (alRechazarCreacion === "bloquear" && status > 0 && status < 500) {
          setCreableLocal({ status: false, msg: detalle || "No se puede crear esta etapa." });
        } else if (alRechazarCreacion === "bloquear" && status >= 500) {
          setToast({ id: Date.now(), message: "Error interno al crear la etapa.", type: "error" });
        } else {
          setToast({
            id: Date.now(),
            message: status > 0 && detalle ? detalle : "Error al crear la etapa.",
            type: "error",
          });
        }
      },
    });
  };

  const cargando = query.isLoading;
  const mostrarCarga = useDelayedFlag(cargando);

  return {
    datos,
    etapaId: datos?.etapa_id,
    etapaExiste: !!datos?.etapa_id,
    existeActo: !!(datos?.acto_admin && "id" in datos.acto_admin && datos.acto_admin.id),
    documentos: datos?.documentos_anexos ?? [],
    creable: creableLocal ?? query.data?.creable ?? CREABLE_POR_DEFECTO,
    cargando,
    mostrarCarga,
    creando: crear.isPending,
    crearEtapa,
    refrescar: query.refetch,
    actualizarDatos,
    setDocumentos,
    setActo,
  };
}
