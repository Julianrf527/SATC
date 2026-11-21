import { useEffect, useState } from "react";
import ActoInfraccion from "../actos/ActoInfraccion";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import { useDatosActoAdmin } from "../../api/expediente";
import { useActualizarConceptoMutation } from "../../api/etapas";
import { detalleError, esErrorDeConexion } from "../../api/errors";
import { INFRACCION_ACTO_ENDPOINTS } from "../actoAdminEndpoints";

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  actoAdmin: ActoAdministrativo | null;
  diasTermino: number | null;
  fechaTerminoCalculada: string | null;
  /** Título del recuadro del acto (el del seguimiento se distingue). */
  tituloActo?: string;
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  /** Cambios hechos dentro de ActoAdmin: el padre re-consulta la etapa. */
  onActoAdminUpdate: () => void;
};

const DIAS_OPTIONS = [10, 15, 30, 60, 120];

export default function AutoRequerimiento({
  etapaConceptoId,
  expedienteId,
  actoAdmin,
  diasTermino,
  fechaTerminoCalculada,
  tituloActo,
  isEditable,
  setToast,
  onActoAdminUpdate,
}: Props) {
  const { involucrados, tiposNotificacion } = useDatosActoAdmin(expedienteId);
  const [selectedDias, setSelectedDias] = useState<number>(diasTermino ?? 0);
  const guardarDias = useActualizarConceptoMutation(expedienteId, etapaConceptoId);
  const isSavingDias = guardarDias.isPending;

  // El acto de acoger concepto siempre se notifica (ya no se cambia a
  // comunicación). Una comunicación registrada antes se sigue mostrando.
  const tipoActo: "notificacion" | "comunicacion" = actoAdmin?.comunicacion ? "comunicacion" : "notificacion";

  useEffect(() => {
    setSelectedDias(diasTermino ?? 0);
  }, [diasTermino]);

  const notifs = actoAdmin?.notificacion?.involucrados ?? [];

  // Cada involucrado actualmente vinculado debe tener al menos una
  // notificación exitosa. Comparar solo cantidades (notifs.length ===
  // involucrados.length) es frágil: se rompe con notificaciones duplicadas,
  // o si se vincula/desvincula un involucrado después de notificar.
  const todasNotificadas =
    actoAdmin !== null &&
    involucrados.length > 0 &&
    involucrados.every((inv) =>
      notifs.some((n) => n.involucrado_id === inv.id && n.notificacion_exitosa === true),
    );

  const pendientesNotificar = involucrados.filter(
    (inv) =>
      !notifs.some((n) => n.involucrado_id === inv.id && n.notificacion_exitosa === true),
  );

  // Condición para mostrar días de término
  const puedeSeleccionarDias =
    actoAdmin !== null &&
    (tipoActo === "notificacion"
      ? todasNotificadas
      : !!(actoAdmin?.comunicacion?.documento_comunicacion_id));

  const handleSaveDias = () => {
    if (!selectedDias) {
      setToast({ id: Date.now(), message: "Seleccione los días de término", type: "error" });
      return;
    }
    guardarDias.mutate(
      { tipo_acogida_concepto: "AUTO_REQUERIMIENTO", dias_termino: selectedDias },
      {
        onSuccess: () => setToast({ id: Date.now(), message: "Días de término guardados", type: "success" }),
        onError: (err) =>
          setToast({
            id: Date.now(),
            message: esErrorDeConexion(err) ? "Error de conexión" : (detalleError(err) ?? "Error al guardar días"),
            type: "error",
          }),
      },
    );
  };

  return (
    <div className="space-y-4">
      {/* Acto Administrativo + Notificaciones o Comunicación */}
      <ActoInfraccion
        etapaTipo="etapa_concepto"
        refId={etapaConceptoId}
        titulo={tituloActo}
        expedienteId={expedienteId}
        actoAdmin={actoAdmin ?? {}}
        etapaId={0}
        tipoActo={tipoActo}
        setToast={setToast}
        isEditable={isEditable}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        onActoAdminUpdate={onActoAdminUpdate}
        endpoints={INFRACCION_ACTO_ENDPOINTS}
        stageBinding={{ type: "etapa_concepto", id: etapaConceptoId }}
        embedded
        anidada
      />

      {/* Aviso: por qué no se puede definir días de término todavía */}
      {actoAdmin !== null && !puedeSeleccionarDias && (
        <div className="alert bg-info/10 border border-info/30">
          <svg className="w-5 h-5 text-info shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-base-content">
              {tipoActo === "notificacion"
                ? "No se pueden definir los días de término todavía: aún no se notifican todos los involucrados."
                : "No se pueden definir los días de término todavía: falta adjuntar el documento de comunicación."}
            </p>
            {tipoActo === "notificacion" && pendientesNotificar.length > 0 && (
              <p className="text-xs text-base-content/60 mt-1">
                Pendientes: {pendientesNotificar.map((inv) => inv.nombre).join(", ")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Días de Término */}
      {puedeSeleccionarDias && (
        <div className="card bg-base-100 shadow-md border border-base-300">
          <div className="card-body gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <h4 className="font-bold">Días de Término</h4>
                <p className="text-xs text-base-content/60">
                  {tipoActo === "notificacion"
                    ? "Todos los involucrados notificados exitosamente"
                    : "Comunicación con documento adjunto"}
                </p>
              </div>
            </div>

            {fechaTerminoCalculada ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 p-4 bg-success/5 rounded-xl border border-success/20">
                  <div>
                    <p className="text-xs text-base-content/60 uppercase tracking-wide">Días hábiles</p>
                    <p className="text-lg font-bold text-success">{diasTermino}</p>
                  </div>
                  <div>
                    <p className="text-xs text-base-content/60 uppercase tracking-wide">Fecha límite calculada</p>
                    <p className="text-lg font-bold text-success">{fechaTerminoCalculada}</p>
                  </div>
                </div>
                {isEditable && (
                  <div>
                    <p className="text-xs text-base-content/60 mb-2">Cambiar días de término:</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {DIAS_OPTIONS.map((d) => (
                        <button key={d}
                          className={`btn btn-sm ${selectedDias === d ? "btn-success text-white" : "btn-outline"}`}
                          onClick={() => setSelectedDias(d)} disabled={isSavingDias}>
                          {d} días
                        </button>
                      ))}
                      {selectedDias !== diasTermino && selectedDias > 0 && (
                        <button className="btn btn-success btn-sm text-white"
                          onClick={handleSaveDias} disabled={isSavingDias}>
                          {isSavingDias ? <span className="loading loading-spinner loading-xs" /> : "Guardar"}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              isEditable && (
                <div>
                  <p className="text-sm text-base-content/70 mb-2">Seleccione los días hábiles de término:</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {DIAS_OPTIONS.map((d) => (
                      <button key={d}
                        className={`btn btn-sm ${selectedDias === d ? "btn-success text-white" : "btn-outline"}`}
                        onClick={() => setSelectedDias(d)} disabled={isSavingDias}>
                        {d} días
                      </button>
                    ))}
                    {selectedDias > 0 && (
                      <button className="btn btn-success btn-sm text-white ml-auto"
                        onClick={handleSaveDias} disabled={isSavingDias}>
                        {isSavingDias
                          ? <><span className="loading loading-spinner loading-xs" />Calculando...</>
                          : "Confirmar días"}
                      </button>
                    )}
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
