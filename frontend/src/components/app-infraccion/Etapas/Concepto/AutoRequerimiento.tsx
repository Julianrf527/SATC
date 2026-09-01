import { useCallback, useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import ActoAdmin from "../../../Common/ActoAdministrativo/ActoAdmin";
import type { TipoNotificacion } from "../../../../types/sancionatorioApp";
import type { Involucrado } from "../../../../types/involucradoApp";


type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  actoAdmin: any | null;
  diasTermino: number | null;
  fechaTerminoCalculada: string | null;
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onDataUpdated: () => void;
};

const DIAS_OPTIONS = [10, 15, 30, 60, 120];

const INFRACTION_ENDPOINTS = {
  actoAdmin: {
    create: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN,
    update: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN_UPDATE,
    delete: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN_DELETE,
  },
  notificacion: {
    base: API_CONFIG.ENDPOINTS.INFRACTION_NOTIFICACION,
    delete: API_CONFIG.ENDPOINTS.INFRACTION_NOTIFICACION_DELETE,
  },
  comunicacion: {
    create: API_CONFIG.ENDPOINTS.INFRACTION_COMUNICACION,
    update: API_CONFIG.ENDPOINTS.INFRACTION_COMUNICACION_UPDATE,
    delete: API_CONFIG.ENDPOINTS.INFRACTION_COMUNICACION_DELETE,
  },
};


export default function AutoRequerimiento({
  etapaConceptoId,
  expedienteId,
  actoAdmin,
  diasTermino,
  fechaTerminoCalculada,
  isEditable,
  setToast,
  onDataUpdated,
}: Props) {
  const [involucrados, setInvolucrados] = useState<Involucrado[]>([]);
  const [tiposNotificacion, setTiposNotificacion] = useState<TipoNotificacion[]>([]);
  const [selectedDias, setSelectedDias] = useState<number>(diasTermino ?? 0);
  const [isSavingDias, setIsSavingDias] = useState(false);

  // tipoActo: si ya existe comunicacion en el actoAdmin, arranca en comunicacion
  const [tipoActo, setTipoActo] = useState<"notificacion" | "comunicacion">(
    actoAdmin?.comunicacion ? "comunicacion" : "notificacion",
  );

  useEffect(() => {
    (async () => {
      try {
        const [invRes, tiposRes] = await Promise.all([
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_LIST(expedienteId), { method: "GET" }),
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_TIPO_NOTIFICACION, { method: "GET" }),
        ]);
        if (invRes.ok) setInvolucrados(invRes.data?.involucrados ?? []);
        if (tiposRes.ok) setTiposNotificacion(tiposRes.data ?? []);
      } catch { /* silently ignore */ }
    })();
  }, [expedienteId]);

  useEffect(() => {
    setSelectedDias(diasTermino ?? 0);
  }, [diasTermino]);

  // Sync tipoActo si el actoAdmin cambia (p.ej. después de guardar comunicacion)
  useEffect(() => {
    if (actoAdmin?.comunicacion) setTipoActo("comunicacion");
  }, [actoAdmin?.comunicacion]);

  const notifs: any[] = actoAdmin?.notificacion?.involucrados ?? [];

  // Cada involucrado actualmente vinculado debe tener al menos una
  // notificación exitosa. Comparar solo cantidades (notifs.length ===
  // involucrados.length) es frágil: se rompe con notificaciones duplicadas,
  // o si se vincula/desvincula un involucrado después de notificar.
  const todasNotificadas =
    actoAdmin !== null &&
    involucrados.length > 0 &&
    involucrados.every((inv) =>
      notifs.some((n: any) => n.involucrado_id === inv.id && n.notificacion_exitosa === true),
    );

  const pendientesNotificar = involucrados.filter(
    (inv) =>
      !notifs.some((n: any) => n.involucrado_id === inv.id && n.notificacion_exitosa === true),
  );

  // Regla 15 días: alguna notif tiene fecha_constancia + no notificada + >= 15 días
  const puedeChangiarAComunicacion =
    tipoActo === "notificacion" &&
    notifs.some((n: any) => {
      if (!n.fecha_constancia_citacion || n.notificacion_exitosa === true) return false;
      const diff =
        (Date.now() - new Date(n.fecha_constancia_citacion).getTime()) /
        (1000 * 60 * 60 * 24);
      return diff >= 15;
    });

  // Condición para mostrar días de término
  const puedeSeleccionarDias =
    actoAdmin !== null &&
    (tipoActo === "notificacion"
      ? todasNotificadas
      : !!(actoAdmin?.comunicacion?.documento_comunicacion_id));

  const handleSaveDias = async () => {
    if (!selectedDias) {
      setToast({ id: Date.now(), message: "Seleccione los días de término", type: "error" });
      return;
    }
    setIsSavingDias(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_PUT_CONCEPTO(etapaConceptoId), {
        method: "PUT",
        body: JSON.stringify({ tipo_acogida_concepto: "AUTO_REQUERIMIENTO", dias_termino: selectedDias }),
      });
      if (res.ok) {
        setToast({ id: Date.now(), message: "Días de término guardados", type: "success" });
        onDataUpdated();
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al guardar días", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setIsSavingDias(false);
    }
  };

  const handleActoAdminUpdate = useCallback(() => {
    onDataUpdated();
  }, [onDataUpdated]);

  return (
    <div className="space-y-4">
      {/* Alerta: 15 días cumplidos → opción cambiar a comunicación */}
      {puedeChangiarAComunicacion && isEditable && (
        <div className="alert bg-warning/10 border border-warning/30">
          <svg className="w-5 h-5 text-warning shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-base-content">
              Han pasado más de 15 días desde la fecha de constancia y la persona no ha sido notificada.
            </p>
            <p className="text-xs text-base-content/60 mt-0.5">
              Puede continuar el proceso por comunicación.
            </p>
          </div>
          <button
            className="btn btn-warning btn-sm text-white"
            onClick={() => setTipoActo("comunicacion")}
          >
            Cambiar a Comunicación
          </button>
        </div>
      )}

      {/* Acto Administrativo + Notificaciones o Comunicación */}
      <ActoAdmin
        expedienteId={expedienteId}
        actoAdmin={actoAdmin ?? {}}
        etapaId={0}
        tipoEtapa="infraccion_concepto"
        tipoActo={tipoActo}
        setToast={setToast}
        isEditable={isEditable}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        onActoAdminUpdate={handleActoAdminUpdate}
        endpoints={INFRACTION_ENDPOINTS}
        stageBinding={{ type: "etapa_concepto", id: etapaConceptoId }}
        embedded
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
                    <p className="text-xs text-base-content/50 uppercase tracking-wide">Días hábiles</p>
                    <p className="text-lg font-bold text-success">{diasTermino}</p>
                  </div>
                  <div>
                    <p className="text-xs text-base-content/50 uppercase tracking-wide">Fecha límite calculada</p>
                    <p className="text-lg font-bold text-success">{fechaTerminoCalculada}</p>
                  </div>
                </div>
                {isEditable && (
                  <div>
                    <p className="text-xs text-base-content/50 mb-2">Cambiar días de término:</p>
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
