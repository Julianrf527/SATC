import { useCallback, useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import ActoAdmin from "../../../Common/ActoAdministrativo/ActoAdmin";
import type { TipoNotificacion } from "../../../../types/sancionatorioApp";
import type { Involucrado } from "../../../../types/involucradoApp";

type TipoMedida = { id: number; nombre: string };

type MedidaInfo = {
  tipo_medida_id: number;
  cantidad: string;
  especie: string;
  estado_medida: boolean | null;
  tipo_medidas: TipoMedida[];
};

type ActoAdmin = {
  id: number;
  tipo_acto: string;
  numerado: number;
  fecha_numerado: string | null;
  documento_acto_administrativo_id: number | null;
  fecha_creacion: string | null;
};

type LocalMedida = {
  id: number;
  etapa_respuesta_id: number;
  acto_administrativo_id: number | null;
  informacion: MedidaInfo;
  acto_admin: ActoAdmin | null;
};

type Props = {
  localMedida: LocalMedida | null;
  expedienteId: number;
  etapaRespuestaId?: number;
  isEditable?: boolean;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  handleViewFile: (id: number) => void;
  onMedidaUpdated?: () => void;
};

const ESTADO_OPTIONS = [
  { value: "true", label: "Vigente" },
  { value: "false", label: "Levantada" },
  { value: "null", label: "No aplica" },
];

function getEstadoLabel(estado: boolean | null) {
  if (estado === null) return "No Aplica";
  return estado ? "Vigente" : "Levantada";
}

function getEstadoBadgeClass(estado: boolean | null) {
  if (estado === null) return "badge-ghost";
  return estado ? "badge-success" : "badge-warning";
}

// ── Acto Administrativo de Medida Preventiva ─────────────────────────────────


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

export default function MedidaPreventivaData({
  localMedida,
  expedienteId,
  etapaRespuestaId,
  isEditable = true,
  setToast,
  handleViewFile: _handleViewFile,
  onMedidaUpdated,
}: Props) {
  const [showForm, setShowForm] = useState(!localMedida?.informacion?.tipo_medida_id);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [involucrados, setInvolucrados] = useState<Involucrado[]>([]);
  const [tiposNotificacion, setTiposNotificacion] = useState<TipoNotificacion[]>([]);

  useEffect(() => {
    if (!expedienteId) return;
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

  const handleActoAdminUpdate = useCallback(() => {
    onMedidaUpdated?.();
  }, [onMedidaUpdated]);

  const medidaInfo = localMedida?.informacion;

  const parseCantidad = (raw?: string) => {
    if (!raw) return { valor: "", unidad: "" };
    const parts = raw.trim().split(" ");
    return parts.length >= 2
      ? { valor: parts[0], unidad: parts.slice(1).join(" ") }
      : { valor: raw, unidad: "" };
  };

  const [tipoMedidaId, setTipoMedidaId] = useState<number>(
    medidaInfo?.tipo_medida_id ?? 0,
  );
  const parsed = parseCantidad(medidaInfo?.cantidad);
  const [cantidadValor, setCantidadValor] = useState(parsed.valor);
  const [cantidadUnidad, setCantidadUnidad] = useState(parsed.unidad);
  const [especie, setEspecie] = useState(medidaInfo?.especie ?? "");
  const [estadoMedida, setEstadoMedida] = useState<string>(
    medidaInfo?.estado_medida === null
      ? "null"
      : medidaInfo?.estado_medida
        ? "true"
        : "false",
  );

  const [tipoMedidas, setTipoMedidas] = useState<TipoMedida[]>(
    medidaInfo?.tipo_medidas ?? [],
  );

  useEffect(() => {
    if ((medidaInfo?.tipo_medidas ?? []).length > 0) return;
    apiCall(API_CONFIG.ENDPOINTS.INFRACTION_TIPO_MEDIDA, { method: "GET" })
      .then((res) => { if (res.ok) setTipoMedidas(res.data ?? []); })
      .catch(() => {});
  }, []);

  const handleCancel = () => {
    setShowForm(false);
    if (medidaInfo) {
      setTipoMedidaId(medidaInfo.tipo_medida_id);
      const p = parseCantidad(medidaInfo.cantidad);
      setCantidadValor(p.valor);
      setCantidadUnidad(p.unidad);
      setEspecie(medidaInfo.especie);
      setEstadoMedida(
        medidaInfo.estado_medida === null
          ? "null"
          : medidaInfo.estado_medida
            ? "true"
            : "false",
      );
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tipoMedidaId) {
      setToast({ id: Date.now(), message: "Seleccione el tipo de medida", type: "error" });
      return;
    }
    if (!cantidadValor.trim()) {
      setToast({ id: Date.now(), message: "La cantidad es obligatoria", type: "error" });
      return;
    }
    if (!cantidadUnidad) {
      setToast({ id: Date.now(), message: "Seleccione la unidad de medida", type: "error" });
      return;
    }
    if (!especie.trim()) {
      setToast({ id: Date.now(), message: "La especie es obligatoria", type: "error" });
      return;
    }

    const cantidad = `${cantidadValor.trim()} ${cantidadUnidad}`;
    const estadoBool =
      estadoMedida === "null" ? null : estadoMedida === "true";

    setIsSubmitting(true);
    try {
      let res;
      if (localMedida) {
        res = await apiCall(
          API_CONFIG.ENDPOINTS.INFRACTION_UPDATE_MEDIDA(localMedida.id),
          {
            method: "PUT",
            body: JSON.stringify({
              tipo_medida_id: tipoMedidaId,
              cantidad,
              especie: especie.trim(),
              estado_medida: estadoBool,
            }),
          },
        );
      } else {
        if (!etapaRespuestaId) {
          console.error("[MedidaPreventiva] etapaRespuestaId no disponible al crear medida");
          setToast({ id: Date.now(), message: "No se puede registrar la medida. Recarga la página e intenta de nuevo.", type: "error" });
          return;
        }
        res = await apiCall(
          API_CONFIG.ENDPOINTS.INFRACTION_CREATE_MEDIDA(etapaRespuestaId),
          {
            method: "POST",
            body: JSON.stringify({
              tipo_medida_id: tipoMedidaId,
              cantidad,
              especie: especie.trim(),
              estado_medida: estadoBool,
            }),
          },
        );
      }

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: localMedida ? "Medida preventiva actualizada" : "Medida preventiva registrada",
          type: "success",
        });
        setShowForm(false);
        onMedidaUpdated?.();
      } else {
        const userMsg = res.status === 409
          ? "Ya existe una medida preventiva para esta etapa"
          : res.status === 403
          ? "No tienes permisos para realizar esta acción"
          : "No se pudo guardar la medida. Intenta de nuevo.";
        console.error("[MedidaPreventiva] Error al guardar:", res.detail ?? res.status);
        setToast({ id: Date.now(), message: userMsg, type: "error" });
      }
    } catch (err) {
      if (import.meta.env.DEV) console.error("[MedidaPreventiva] Error de conexión:", err);
      setToast({ id: Date.now(), message: "Error de conexión. Verifica tu red e intenta de nuevo.", type: "error" });
    } finally {
      setIsSubmitting(false);
    }
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
              className="btn btn-ghost btn-sm gap-2 text-info hover:bg-info/10"
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
            tipoEtapa="infraccion_medida"
            tipoActo="comunicacion"
            setToast={setToast}
            isEditable={isEditable}
            involucrados={involucrados}
            tiposNotificacion={tiposNotificacion}
            onActoAdminUpdate={handleActoAdminUpdate}
            endpoints={INFRACTION_ENDPOINTS}
            stageBinding={{ type: "medida_preventiva", id: localMedida.id }}
            embedded
          />
        )}

        {/* BLOQUEO: sin acto no se puede registrar data */}
        {localMedida && !tieneActo && isEditable && (
          <div className="flex items-center gap-3 p-4 bg-warning/10 border border-warning/30 rounded-xl">
            <svg className="w-5 h-5 text-warning flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm font-medium">Debe registrar el acto administrativo antes de poder completar los datos de la medida.</p>
          </div>
        )}

        {/* FORMULARIO CREAR (sin medida aún) */}
        {!localMedida && showForm && isEditable && (
          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tipo de medida */}
              <div className="form-control md:col-span-2">
                <label className="label">
                  <span className="label-text font-medium">Tipo de Medida *</span>
                </label>
                <select
                  className="select select-bordered w-full"
                  value={tipoMedidaId || ""}
                  onChange={(e) => setTipoMedidaId(Number(e.target.value))}
                  disabled={isSubmitting}
                  required
                >
                  <option value="" disabled>Seleccione un tipo</option>
                  {tipoMedidas.map((t) => (
                    <option key={t.id} value={t.id}>{t.nombre}</option>
                  ))}
                </select>
              </div>

              {/* Cantidad */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Cantidad *</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    className="input input-bordered w-2/3"
                    value={cantidadValor}
                    onChange={(e) => setCantidadValor(e.target.value)}
                    disabled={isSubmitting}
                    placeholder="0"
                    step="0.01"
                    min="0"
                    required
                  />
                  <select
                    className="select select-bordered w-1/3"
                    value={cantidadUnidad}
                    onChange={(e) => setCantidadUnidad(e.target.value)}
                    disabled={isSubmitting}
                    required
                  >
                    <option value="" disabled>Unidad</option>
                    <option value="m³">m³</option>
                    <option value="L">Litros</option>
                    <option value="m²">m²</option>
                    <option value="Ha">Hectáreas</option>
                    <option value="kg">Kilogramos</option>
                    <option value="ton">Toneladas</option>
                    <option value="und">Unidades</option>
                    <option value="m">Metros</option>
                    <option value="km">Kilómetros</option>
                  </select>
                </div>
              </div>

              {/* Especie */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Especie *</span>
                </label>
                <input
                  type="text"
                  className="input input-bordered w-full"
                  value={especie}
                  onChange={(e) => setEspecie(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="Ej: Bovinos"
                  maxLength={200}
                />
              </div>

              {/* Estado */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Estado de la Medida</span>
                </label>
                <select
                  className="select select-bordered w-full"
                  value={estadoMedida}
                  onChange={(e) => setEstadoMedida(e.target.value)}
                  disabled={isSubmitting}
                >
                  {ESTADO_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 justify-end pt-2 border-t border-base-300">
              <button type="submit" className="btn btn-info text-white" disabled={isSubmitting}>
                {isSubmitting ? (
                  <><span className="loading loading-spinner loading-sm" />Guardando...</>
                ) : "Registrar medida"}
              </button>
            </div>
          </form>
        )}

        {/* FORMULARIO EDITAR (medida existe Y acto existe) */}
        {localMedida && tieneActo && showForm && isEditable && (
          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="form-control md:col-span-2">
                <label className="label"><span className="label-text font-medium">Tipo de Medida *</span></label>
                <select className="select select-bordered w-full" value={tipoMedidaId || ""} onChange={(e) => setTipoMedidaId(Number(e.target.value))} disabled={isSubmitting} required>
                  <option value="" disabled>Seleccione un tipo</option>
                  {tipoMedidas.map((t) => (<option key={t.id} value={t.id}>{t.nombre}</option>))}
                </select>
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text font-medium">Cantidad *</span></label>
                <div className="flex gap-2">
                  <input type="number" className="input input-bordered w-2/3" value={cantidadValor} onChange={(e) => setCantidadValor(e.target.value)} disabled={isSubmitting} placeholder="0" step="0.01" min="0" required />
                  <select className="select select-bordered w-1/3" value={cantidadUnidad} onChange={(e) => setCantidadUnidad(e.target.value)} disabled={isSubmitting} required>
                    <option value="" disabled>Unidad</option>
                    <option value="m³">m³</option><option value="L">Litros</option><option value="m²">m²</option>
                    <option value="Ha">Hectáreas</option><option value="kg">Kilogramos</option><option value="ton">Toneladas</option>
                    <option value="und">Unidades</option><option value="m">Metros</option><option value="km">Kilómetros</option>
                  </select>
                </div>
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text font-medium">Especie *</span></label>
                <input type="text" className="input input-bordered w-full" value={especie} onChange={(e) => setEspecie(e.target.value)} disabled={isSubmitting} placeholder="Ej: Bovinos" maxLength={200} />
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text font-medium">Estado de la Medida</span></label>
                <select className="select select-bordered w-full" value={estadoMedida} onChange={(e) => setEstadoMedida(e.target.value)} disabled={isSubmitting}>
                  {ESTADO_OPTIONS.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}
                </select>
              </div>
            </div>
            <div className="flex gap-3 justify-end pt-2 border-t border-base-300">
              <button type="button" className="btn btn-outline" onClick={handleCancel} disabled={isSubmitting}>Cancelar</button>
              <button type="submit" className="btn btn-info text-white" disabled={isSubmitting}>
                {isSubmitting ? <><span className="loading loading-spinner loading-sm" />Guardando...</> : "Actualizar medida"}
              </button>
            </div>
          </form>
        )}

        {/* VISTA DE DATOS (medida existe Y acto existe Y no en form) */}
        {!showForm && localMedida && medidaInfo && tieneActo && (
          <div className="border border-base-300 rounded-xl p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Tipo de Medida</p>
                    <p className="text-sm font-semibold">{tipoMedidas.find((t) => t.id === medidaInfo.tipo_medida_id)?.nombre ?? "—"}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Cantidad</p>
                    <p className="text-sm">{medidaInfo.cantidad}</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Especie</p>
                    <p className="text-sm">{medidaInfo.especie}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Estado</p>
                    <span className={`badge text-white ${getEstadoBadgeClass(medidaInfo.estado_medida)} badge-sm mt-1`}>
                      {getEstadoLabel(medidaInfo.estado_medida)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SIN MEDIDA REGISTRADA y no editable */}
        {!localMedida && !showForm && !isEditable && (
          <div className="text-center py-8 text-base-content/50">
            <p>No hay medida preventiva registrada</p>
          </div>
        )}

      </div>
    </div>
  );
}
