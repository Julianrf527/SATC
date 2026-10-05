import { useCallback, useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ActoAdmin } from "@features/acto-administrativo";
import type { MedidaInfo, MedidaPreventiva } from "../../types";
import { useDatosActoAdmin } from "../../api/expediente";
import { useGuardarMedidaMutation, useTiposMedidaQuery } from "../../api/etapas";
import { esErrorDeConexion, estadoError } from "../../api/errors";
import { infraccionKeys } from "../../api/queryKeys";
import { INFRACCION_ACTO_ENDPOINTS } from "../actoAdminEndpoints";
import MedidaPreventivaForm, { type MedidaFormValues } from "./MedidaPreventivaForm";
import MedidaPreventivaView from "./MedidaPreventivaView";

type Props = {
  localMedida: MedidaPreventiva | null;
  expedienteId: number;
  etapaRespuestaId?: number;
  isEditable?: boolean;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

function parseCantidad(raw?: string) {
  if (!raw) return { valor: "", unidad: "" };
  const parts = raw.trim().split(" ");
  return parts.length >= 2
    ? { valor: parts[0], unidad: parts.slice(1).join(" ") }
    : { valor: raw, unidad: "" };
}

function valoresIniciales(info?: MedidaInfo): MedidaFormValues {
  const cantidad = parseCantidad(info?.cantidad);
  return {
    tipoMedidaId: info?.tipo_medida_id ?? 0,
    cantidadValor: cantidad.valor,
    cantidadUnidad: cantidad.unidad,
    especie: info?.especie ?? "",
    estadoMedida:
      info?.estado_medida === null ? "null" : info?.estado_medida ? "true" : "false",
  };
}

function validar(v: MedidaFormValues): string | null {
  if (!v.tipoMedidaId) return "Seleccione el tipo de medida";
  if (!v.cantidadValor.trim()) return "La cantidad es obligatoria";
  if (!v.cantidadUnidad) return "Seleccione la unidad de medida";
  if (!v.especie.trim()) return "La especie es obligatoria";
  return null;
}

export default function MedidaPreventivaData({
  localMedida,
  expedienteId,
  etapaRespuestaId,
  isEditable = true,
  setToast,
}: Props) {
  const queryClient = useQueryClient();
  const medidaInfo = localMedida?.informacion;
  const [showForm, setShowForm] = useState(!medidaInfo?.tipo_medida_id);
  const [values, setValues] = useState<MedidaFormValues>(() => valoresIniciales(medidaInfo));

  const { involucrados, tiposNotificacion } = useDatosActoAdmin(expedienteId);
  // Si la medida ya trae el catálogo no hace falta pedirlo.
  const catalogoEmbebido = medidaInfo?.tipo_medidas ?? [];
  const tiposMedidaQuery = useTiposMedidaQuery(catalogoEmbebido.length === 0);
  const tipoMedidas = catalogoEmbebido.length > 0 ? catalogoEmbebido : (tiposMedidaQuery.data ?? []);

  const guardarMedida = useGuardarMedidaMutation(expedienteId);
  const isSubmitting = guardarMedida.isPending;

  const handleActoAdminUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: infraccionKeys.respuesta(expedienteId) });
  }, [queryClient, expedienteId]);

  const handleChange = (patch: Partial<MedidaFormValues>) =>
    setValues((prev) => ({ ...prev, ...patch }));

  const handleCancel = () => {
    setShowForm(false);
    if (medidaInfo) setValues(valoresIniciales(medidaInfo));
  };

  const handleSave = (e: FormEvent) => {
    e.preventDefault();
    const error = validar(values);
    if (error) {
      setToast({ id: Date.now(), message: error, type: "error" });
      return;
    }
    if (!localMedida && !etapaRespuestaId) {
      if (import.meta.env.DEV) console.error("[MedidaPreventiva] etapaRespuestaId no disponible al crear medida");
      setToast({ id: Date.now(), message: "No se puede registrar la medida. Recarga la página e intenta de nuevo.", type: "error" });
      return;
    }

    guardarMedida.mutate(
      {
        medidaId: localMedida?.id ?? null,
        etapaRespuestaId: etapaRespuestaId ?? null,
        payload: {
          tipo_medida_id: values.tipoMedidaId,
          cantidad: `${values.cantidadValor.trim()} ${values.cantidadUnidad}`,
          especie: values.especie.trim(),
          estado_medida: values.estadoMedida === "null" ? null : values.estadoMedida === "true",
        },
      },
      {
        onSuccess: () => {
          setToast({
            id: Date.now(),
            message: localMedida ? "Medida preventiva actualizada" : "Medida preventiva registrada",
            type: "success",
          });
          setShowForm(false);
        },
        onError: (err) => {
          if (import.meta.env.DEV) console.error("[MedidaPreventiva] Error al guardar:", err);
          if (esErrorDeConexion(err)) {
            setToast({ id: Date.now(), message: "Error de conexión. Verifica tu red e intenta de nuevo.", type: "error" });
            return;
          }
          const status = estadoError(err);
          const userMsg =
            status === 409
              ? "Ya existe una medida preventiva para esta etapa"
              : status === 403
                ? "No tienes permisos para realizar esta acción"
                : "No se pudo guardar la medida. Intenta de nuevo.";
          setToast({ id: Date.now(), message: userMsg, type: "error" });
        },
      },
    );
  };

  const tieneActo = !!localMedida?.acto_admin?.id;

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body gap-6">
        {/* HEADER */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Medida Preventiva</h3>
              <p className="text-sm text-base-content/60">
                {localMedida
                  ? "Información de la medida preventiva registrada"
                  : "Aún no se ha registrado la medida preventiva"}
              </p>
            </div>
          </div>
          {!showForm && isEditable && localMedida && tieneActo && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-tono-info hover:bg-info/10"
              onClick={() => setShowForm(true)}
              disabled={isSubmitting}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Editar
            </button>
          )}
        </div>

        {/* ACTO ADMINISTRATIVO — siempre primero cuando existe medida */}
        {localMedida && (
          <ActoAdmin
            expedienteId={expedienteId}
            actoAdmin={localMedida.acto_admin ?? {}}
            etapaId={0}
            tipoActo="comunicacion"
            setToast={setToast}
            isEditable={isEditable}
            involucrados={involucrados}
            tiposNotificacion={tiposNotificacion}
            onActoAdminUpdate={handleActoAdminUpdate}
            endpoints={INFRACCION_ACTO_ENDPOINTS}
            stageBinding={{ type: "medida_preventiva", id: localMedida.id }}
            embedded
          />
        )}

        {/* BLOQUEO: sin acto no se puede registrar data */}
        {localMedida && !tieneActo && isEditable && (
          <div className="flex items-center gap-3 p-4 bg-warning/10 rounded-xl">
            <svg className="w-5 h-5 text-warning flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm font-medium">Debe registrar el acto administrativo antes de poder completar los datos de la medida.</p>
          </div>
        )}

        {/* FORMULARIO CREAR (sin medida aún) */}
        {!localMedida && showForm && isEditable && (
          <MedidaPreventivaForm
            values={values}
            onChange={handleChange}
            tipoMedidas={tipoMedidas}
            isSubmitting={isSubmitting}
            onSubmit={handleSave}
          />
        )}

        {/* FORMULARIO EDITAR (medida existe Y acto existe) */}
        {localMedida && tieneActo && showForm && isEditable && (
          <MedidaPreventivaForm
            values={values}
            onChange={handleChange}
            tipoMedidas={tipoMedidas}
            isSubmitting={isSubmitting}
            onSubmit={handleSave}
            onCancel={handleCancel}
          />
        )}

        {/* VISTA DE DATOS (medida existe Y acto existe Y no en form) */}
        {!showForm && localMedida && medidaInfo && tieneActo && (
          <MedidaPreventivaView medidaInfo={medidaInfo} tipoMedidas={tipoMedidas} />
        )}

        {/* SIN MEDIDA REGISTRADA y no editable */}
        {!localMedida && !showForm && !isEditable && (
          <div className="text-center py-8 text-base-content/60">
            <p>No hay medida preventiva registrada</p>
          </div>
        )}
      </div>
    </div>
  );
}
