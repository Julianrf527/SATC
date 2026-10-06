import { useState } from "react";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { formatDate } from "@shared/lib/format";
import { useConceptoEtapaQuery, useCrearConceptoMutation } from "../api/etapas";
import { detalleError, esErrorDeConexion } from "../api/errors";
import { useInvalidarExpediente } from "../api/invalidar";
import type { TipoAcogidaConcepto } from "../types";
import ConceptoDataCard from "./concepto/ConceptoData";
import AutoRequerimiento from "./concepto/AutoRequerimiento";
import OficioRemiteCard from "./concepto/OficioRemiteCard";
import SolicitudInformacionCard from "./concepto/SolicitudInformacionCard";
import {
  EtapaCargando,
  EtapaHueco,
  EtapaNoCreable,
  EtapaNoExiste,
  EtapaPorCrear,
  EtapaSinExpediente,
  IconoEtapa,
  IconoMas,
} from "./EtapaEstados";
import { ICONOS_ETAPA } from "./iconosEtapa";
import { useAvisoErrorCarga } from "./useAvisoErrorCarga";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "Concepto";

const TIPO_OPTIONS: { value: TipoAcogidaConcepto; label: string }[] = [
  { value: "AUTO_REQUERIMIENTO", label: "Auto de Requerimiento" },
  { value: "OFICIO", label: "Oficio remitido por competencia" },
  { value: "RESOLUCION_ARCHIVO", label: "Resolución de Archivo, se cierra el trámite" },
];

export default function Concepto({
  expedienteId,
  setToast,
  isEditable = true,
}: Props) {
  const query = useConceptoEtapaQuery(expedienteId);
  const crearConcepto = useCrearConceptoMutation(expedienteId);
  const showLoading = useDelayedFlag(query.isPending && !!expedienteId, 300);
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [selectedTipoCrear, setSelectedTipoCrear] = useState<TipoAcogidaConcepto | "">("");
  const isSubmittingCreate = crearConcepto.isPending;

  useAvisoErrorCarga(query.error, setToast, {
    http: "Error al cargar la etapa concepto",
    conexion: "Error de conexión al cargar el concepto",
  });

  const conceptoData = query.data?.data ?? null;
  // Con error de carga (no 404) se comportaba como "no creable" sin motivo.
  const creable = query.data?.creable ?? false;
  const creableMsg = query.data?.creableMsg ?? null;

  const handleCreateStage = () => {
    if (!selectedTipoCrear) {
      setToast({ id: Date.now(), message: "Seleccione el tipo de acogida", type: "error" });
      return;
    }
    crearConcepto.mutate(selectedTipoCrear, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Etapa concepto creada correctamente", type: "success" });
        setIsCreatingStage(false);
        setSelectedTipoCrear("");
      },
      onError: (err) => {
        setToast({
          id: Date.now(),
          message: esErrorDeConexion(err) ? "Error de conexión" : (detalleError(err) ?? "Error al crear la etapa"),
          type: "error",
        });
      },
    });
  };

  // Las tarjetas hijas ya invalidaron el expediente con su mutación; solo
  // queda hacerlo tras cambios hechos dentro de ActoAdmin.
  const handleDataUpdated = useInvalidarExpediente(expedienteId);

  if (showLoading) return <EtapaCargando etapa="concepto" />;
  if (!expedienteId) return <EtapaSinExpediente isEditable={isEditable} />;
  if (query.isPending) return <EtapaHueco />;

  if (!conceptoData && !isEditable) return <EtapaNoExiste etapa={STAGE_NAME} />;

  if (!conceptoData && !creable && !isCreatingStage) {
    return (
      <EtapaNoCreable motivo={creableMsg}>
        <p className="text-sm opacity-70 max-w-md mx-auto mt-4">
          Por favor, complete los requisitos necesarios antes de crear esta etapa.
        </p>
      </EtapaNoCreable>
    );
  }

  if (!conceptoData && !isCreatingStage) {
    return (
      <EtapaPorCrear
        etapa={STAGE_NAME}
        icono={ICONOS_ETAPA.portapapeles}
        etapaClassName="text-tono-info"
        descripcion="Para continuar, debe crear esta etapa indicando cómo se acoge el concepto técnico."
      >
        <button
          className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
          onClick={() => setIsCreatingStage(true)}
        >
          <IconoMas />
          Crear Etapa
        </button>
      </EtapaPorCrear>
    );
  }

  // ── Selección del tipo de acogida al crear ──
  if (!conceptoData) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-info/30">
        <div className="card-body">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
              <IconoEtapa d={ICONOS_ETAPA.portapapeles} className="w-5 h-5 text-warning" />
            </div>
            <div>
              <h3 className="text-xl font-bold">Nueva Etapa — {STAGE_NAME}</h3>
              <p className="text-sm text-base-content/60">¿Cómo desea acoger el concepto técnico?</p>
            </div>
          </div>

          <div className="space-y-3 mb-6">
            {TIPO_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  selectedTipoCrear === opt.value
                    ? "border-warning bg-warning/5"
                    : "border-base-300 hover:border-warning/40"
                }`}
              >
                <input
                  type="radio"
                  name="tipo_acogida_crear"
                  value={opt.value}
                  checked={selectedTipoCrear === opt.value}
                  onChange={() => setSelectedTipoCrear(opt.value)}
                  className="radio radio-warning mt-0.5"
                  disabled={isSubmittingCreate}
                />
                <span className="text-sm font-medium">{opt.label}</span>
              </label>
            ))}
          </div>

          <div className="flex gap-3 justify-end border-t border-base-300 pt-4">
            <button
              className="btn btn-outline"
              onClick={() => { setIsCreatingStage(false); setSelectedTipoCrear(""); }}
              disabled={isSubmittingCreate}
            >
              Cancelar
            </button>
            <button
              className="btn btn-success text-white gap-2"
              onClick={handleCreateStage}
              disabled={!selectedTipoCrear || isSubmittingCreate}
            >
              {isSubmittingCreate ? (
                <><span className="loading loading-spinner loading-sm" />Creando...</>
              ) : (
                <>
                  <IconoEtapa d={ICONOS_ETAPA.check} className="w-4 h-4" />
                  Crear Etapa
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Solicitud de información — independiente del tipo de acogida, se puede agregar en cualquier momento */}
      <SolicitudInformacionCard
        etapaConceptoId={conceptoData.id}
        expedienteId={expedienteId}
        solicitud={conceptoData.solicitud_informacion}
        isEditable={isEditable}
        setToast={setToast}
      />

      {/* Tipo de acogida */}
      <ConceptoDataCard
        etapaConceptoId={conceptoData.id}
        expedienteId={expedienteId}
        tipoActual={conceptoData.tipo_acogida_concepto}
        isEditable={isEditable}
        setToast={setToast}
      />

      {/* Sub-flujo según tipo */}
      {conceptoData.tipo_acogida_concepto === "AUTO_REQUERIMIENTO" && (
        <AutoRequerimiento
          etapaConceptoId={conceptoData.id}
          expedienteId={expedienteId}
          actoAdmin={conceptoData.acto_admin}
          diasTermino={conceptoData.dias_termino}
          fechaTerminoCalculada={conceptoData.fecha_termino_calculada}
          isEditable={isEditable}
          setToast={setToast}
          onActoAdminUpdate={handleDataUpdated}
        />
      )}

      {conceptoData.tipo_acogida_concepto === "OFICIO" && (
        <OficioRemiteCard
          etapaConceptoId={conceptoData.id}
          expedienteId={expedienteId}
          oficio={conceptoData.oficio_remite}
          isEditable={isEditable}
          setToast={setToast}
        />
      )}

      {conceptoData.tipo_acogida_concepto === "RESOLUCION_ARCHIVO" && (
        <div className="card bg-base-100 shadow-md border border-base-300">
          <div className="card-body">
            <div className="flex items-center gap-4 py-4">
              <div className="w-12 h-12 bg-error/10 rounded-full flex items-center justify-center flex-shrink-0">
                <IconoEtapa d={ICONOS_ETAPA.archivo} className="w-6 h-6 text-error" />
              </div>
              <div>
                <h4 className="font-bold text-base">Trámite Archivado</h4>
                <p className="text-sm text-base-content/60 mt-1">
                  El concepto técnico fue acogido mediante{" "}
                  <span className="font-semibold text-error">Resolución de Archivo</span>.
                </p>
                <p className="text-xs text-base-content/60 mt-2">
                  Creado: {formatDate(conceptoData.fecha_creacion)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
