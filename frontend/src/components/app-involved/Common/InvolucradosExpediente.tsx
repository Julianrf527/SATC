import React, { useState, useCallback, useEffect, useRef } from "react";
import type { Involucrado } from "../../../types/involucradoApp";
import { apiCall, API_CONFIG, getErrorMessage } from "../../../utils/api";
import ConfirmDeleteModal from "./ConfirmDeleteModal";

interface Props {
  expedienteId: number;
  involucradosList: Involucrado[];
  endpoints: {
    vincular: string;
    desvincular: (id: number) => string;
    listar?: (expedienteId: number) => string;
  };
  onInvolucradosUpdate?: (updatedInvolucrados: Involucrado[]) => void;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable?: boolean;
}

interface InvolucradoForm {
  numero_documento: string;
  digito_verificacion: string;
  tipo_documento: string;
  nombre: string;
  celular: string;
  correo: string;
  direccion: string;
}

const initialFormData: InvolucradoForm = {
  numero_documento: "",
  digito_verificacion: "",
  tipo_documento: "CC",
  nombre: "",
  celular: "",
  correo: "",
  direccion: "",
};

const capitalizeName = (name: string): string =>
  name.trim().toLowerCase().split(" ").filter((w) => w.length > 0)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

const DOC_BADGE: Record<string, string> = {
  CC: "badge-info", NIT: "badge-success", CE: "badge-warning", PP: "badge-secondary",
};

export default function InvolucradoExpediente({
  expedienteId, involucradosList, endpoints, onInvolucradosUpdate, setToast, isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [existingInvolucrado, setExistingInvolucrado] = useState<Involucrado | null>(null);
  const [formData, setFormData] = useState<InvolucradoForm>(initialFormData);
  const [involucrados, setInvolucrados] = useState<Involucrado[]>(involucradosList || []);
  const [involucradoAEliminar, setInvolucradoAEliminar] = useState<Involucrado | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const confirmResolver = useRef<((value: boolean) => void) | null>(null);

  useEffect(() => { setInvolucrados(involucradosList || []); }, [involucradosList]);

  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const ep = endpoints.listar
          ? endpoints.listar(expedienteId)
          : API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_LIST(expedienteId);
        const res = await apiCall(ep);
        if (isMounted && res?.ok && res.data?.involucrados)
          setInvolucrados(res.data.involucrados);
      } catch { /* keep props state */ }
    })();
    return () => { isMounted = false; };
  }, [expedienteId]);

  const buscarInvolucrado = useCallback(async (num: string, tipo: string, dv?: string) => {
    if (!num.trim() || !tipo.trim() || num.length < 7) return;
    if (tipo === "NIT" && !dv?.trim()) return;
    try {
      setIsLoading(true);
      const data = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_SEARCH(tipo, num, dv));
      if (data.ok && data.data) {
        const inv = data.data;
        setFormData({
          numero_documento: inv.numero_documento != null ? inv.numero_documento.toString() : "",
          digito_verificacion: inv.digito_verificacion || "",
          tipo_documento: inv.tipo_documento,
          nombre: inv.nombre,
          celular: inv.celular != null ? inv.celular.toString() : "",
          correo: inv.correo ?? "",
          direccion: inv.direccion ?? "",
        });
        setExistingInvolucrado(inv);
      } else {
        setExistingInvolucrado(null);
      }
    } catch (error) {
      if (!getErrorMessage(error).includes("404"))
        setToast({ id: Date.now(), message: "Servicio de involucrados no disponible", type: "error" });
    } finally { setIsLoading(false); }
  }, [setToast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      let invData: Involucrado;
      if (!existingInvolucrado) {
        const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_CREATE, {
          method: "POST",
          body: JSON.stringify({
            numero_documento: formData.numero_documento.trim(),
            digito_verificacion: formData.tipo_documento === "NIT" ? formData.digito_verificacion : null,
            tipo_documento: formData.tipo_documento,
            nombre: capitalizeName(formData.nombre),
            celular: formData.celular.trim() ? parseInt(formData.celular.trim()) : null,
            correo: formData.correo.trim() ? formData.correo.trim().toLowerCase() : null,
            direccion: formData.direccion.trim() || null,
          }),
        });
        if (!res?.ok) throw new Error("Error al crear el involucrado");
        invData = {
          id: res.data.id,
          numero_documento: parseInt(formData.numero_documento.trim()),
          digito_verificacion: formData.tipo_documento === "NIT" ? formData.digito_verificacion : null,
          tipo_documento: formData.tipo_documento,
          nombre: capitalizeName(formData.nombre),
          celular: formData.celular.trim() ? parseInt(formData.celular.trim()) : null,
          correo: formData.correo.trim().toLowerCase() || null,
          direccion: formData.direccion.trim() || null,
        };
      } else {
        invData = {
          ...existingInvolucrado,
          numero_documento: parseInt(existingInvolucrado.numero_documento.toString()),
          celular: existingInvolucrado.celular != null ? parseInt(existingInvolucrado.celular.toString()) : null,
        };
      }

      const yaExiste = involucrados.some((i) => i.id === invData.id ||
        (i.numero_documento == invData.numero_documento && i.tipo_documento === invData.tipo_documento));
      if (yaExiste) {
        setToast({ id: Date.now(), message: "Este involucrado ya está vinculado al expediente", type: "error" });
        return;
      }

      const link = await apiCall(endpoints.vincular, {
        method: "POST",
        body: JSON.stringify({ expediente_id: expedienteId, involucrado_id: invData.id }),
      });
      if (!link?.ok) throw new Error(link?.detail || "Error al vincular");

      const updated = [...involucrados, invData];
      setInvolucrados(updated);
      onInvolucradosUpdate?.(updated);
      resetForm();
      setToast({ id: Date.now(), message: "Involucrado vinculado exitosamente", type: "success" });
    } catch (error) {
      setToast({ id: Date.now(), message: getErrorMessage(error), type: "error" });
    } finally { setIsLoading(false); }
  };

  const confirmarEliminacion = (inv: Involucrado): Promise<boolean> =>
    new Promise((resolve) => {
      setInvolucradoAEliminar(inv);
      setModalAbierto(true);
      confirmResolver.current = resolve;
    });

  const eliminarInvolucrado = async (idx: number) => {
    const inv = involucrados[idx];
    const ok = await confirmarEliminacion(inv);
    if (!ok) return;
    try {
      setIsLoading(true);
      const res = await apiCall(endpoints.desvincular(inv.id), { method: "DELETE" });
      if (!res?.ok) throw new Error(res?.detail || "Error al desvincular");
      const updated = involucrados.filter((_, i) => i !== idx);
      setInvolucrados(updated);
      onInvolucradosUpdate?.(updated);
      setToast({ id: Date.now(), message: "Involucrado desvinculado exitosamente", type: "success" });
    } catch (error) {
      setToast({ id: Date.now(), message: getErrorMessage(error), type: "error" });
    } finally { setIsLoading(false); }
  };

  const resetForm = () => { setFormData(initialFormData); setExistingInvolucrado(null); setShowForm(false); };

  const handleDocumentChange = (value: string) => {
    const v = value.replace(/\D/g, "");
    setFormData({ ...formData, numero_documento: v });
    if (existingInvolucrado && v !== existingInvolucrado.numero_documento.toString()) {
      setExistingInvolucrado(null);
      setFormData({ ...initialFormData, numero_documento: v, digito_verificacion: formData.digito_verificacion, tipo_documento: formData.tipo_documento });
    }
  };

  const handleTipoChange = (value: string) => {
    if (existingInvolucrado && value !== existingInvolucrado.tipo_documento) {
      setExistingInvolucrado(null);
      setFormData({ ...initialFormData, tipo_documento: value, numero_documento: formData.numero_documento });
    } else {
      setFormData({ ...formData, tipo_documento: value, digito_verificacion: value === "NIT" ? formData.digito_verificacion : "" });
    }
  };

  const triggerSearch = () => {
    if (formData.numero_documento.length >= 7 && !existingInvolucrado) {
      if (formData.tipo_documento === "NIT" && formData.digito_verificacion)
        buscarInvolucrado(formData.numero_documento, formData.tipo_documento, formData.digito_verificacion);
      else if (formData.tipo_documento !== "NIT")
        buscarInvolucrado(formData.numero_documento, formData.tipo_documento);
    }
  };

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">

        {modalAbierto && involucradoAEliminar && (
          <ConfirmDeleteModal
            involucrado={involucradoAEliminar}
            isOpen={modalAbierto}
            onClose={() => { confirmResolver.current?.(false); confirmResolver.current = null; setModalAbierto(false); }}
            onConfirm={() => { confirmResolver.current?.(true); confirmResolver.current = null; setModalAbierto(false); }}
          />
        )}

        {/* Header */}
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-warning/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Presuntos Infractores</h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {involucrados.length > 0 && (
              <div className="flex flex-col items-center px-2.5 py-1 bg-base-200 rounded-lg min-w-[3rem]">
                <span className="text-lg font-bold leading-tight text-warning">{involucrados.length}</span>
                <span className="text-[9px] text-base-content/50 uppercase">
                  {involucrados.length === 1 ? "Persona" : "Personas"}
                </span>
              </div>
            )}
            {!showForm && isEditable && (
              <button
                className="btn btn-warning btn-sm text-white gap-1.5"
                onClick={() => setShowForm(true)}
                disabled={isLoading}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Agregar
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="p-4">
          {/* Lista */}
          {!showForm && (
            <>
              {involucrados.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-base-200 rounded-full flex items-center justify-center mb-3 mx-auto">
                    <svg className="w-6 h-6 text-base-content/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-base-content/70">Sin involucrados</p>
                  <p className="text-xs text-base-content/50">No hay personas vinculadas a este expediente</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {involucrados.map((inv, idx) => (
                    <div
                      key={`${inv.tipo_documento}-${inv.numero_documento}-${idx}`}
                      className="border border-base-300 rounded-lg p-3 hover:bg-base-200/40 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {/* Avatar */}
                        <div className="w-10 h-10 rounded-full bg-warning/20 flex items-center justify-center flex-shrink-0">
                          <span className="text-sm font-bold text-warning">
                            {inv.nombre.split(" ").map((n) => n?.[0] ?? "").join("").substring(0, 2).toUpperCase()}
                          </span>
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                            <span className="text-base font-semibold truncate">{inv.nombre}</span>
                            <span className={`badge badge-sm ${DOC_BADGE[inv.tipo_documento] || "badge-ghost"}`}>
                              {inv.tipo_documento}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-sm text-base-content/60">
                            <span className="font-mono">
                              {inv.numero_documento}{inv.digito_verificacion ? `-${inv.digito_verificacion}` : ""}
                            </span>
                            <span>{inv.celular ? String(inv.celular) : <span className="italic opacity-50">Sin teléfono</span>}</span>
                            <span className="truncate">{inv.correo?.trim() ? inv.correo : <span className="italic opacity-50">Sin correo</span>}</span>
                            <span className="truncate">{inv.direccion?.trim() ? inv.direccion : <span className="italic opacity-50">Sin dirección</span>}</span>
                          </div>
                        </div>

                        {/* Delete */}
                        {isEditable && (
                          <button
                            onClick={() => eliminarInvolucrado(idx)}
                            disabled={isLoading}
                            className="btn btn-ghost btn-xs text-error hover:bg-error/10"
                            title="Desvincular"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Formulario */}
          {showForm && isEditable && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Matriz 2×3 */}
              <div className="grid grid-cols-3 gap-3">
                {/* [1.1] Tipo */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Tipo documento *</span>
                  <select
                    value={formData.tipo_documento}
                    onChange={(e) => handleTipoChange(e.target.value)}
                    className="select select-bordered w-full"
                    required disabled={isLoading}
                  >
                    <option value="CC">Cédula (CC)</option>
                    <option value="NIT">NIT</option>
                    <option value="CE">Extranjería (CE)</option>
                    <option value="PP">Pasaporte</option>
                  </select>
                </div>

                {/* [1.2 + 1.3] Número (ocupa 2 columnas) */}
                <div className="col-span-2 flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60 flex items-center gap-1">
                    Número de documento *
                    {isLoading && <span className="loading loading-spinner loading-xs" />}
                  </span>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formData.numero_documento}
                      onChange={(e) => handleDocumentChange(e.target.value)}
                      onBlur={triggerSearch}
                      className="input input-bordered flex-1 font-mono"
                      required disabled={isLoading}
                      placeholder="Ej: 1234567890"
                      minLength={7} maxLength={15}
                    />
                    {formData.tipo_documento === "NIT" && (
                      <input
                        type="text"
                        value={formData.digito_verificacion}
                        onChange={(e) => setFormData({ ...formData, digito_verificacion: e.target.value.replace(/\D/g, "").slice(0, 2) })}
                        onBlur={triggerSearch}
                        className="input input-bordered w-20 text-center font-mono"
                        required disabled={isLoading}
                        placeholder="DV"
                      />
                    )}
                  </div>
                </div>

                {/* [2.1] Nombre */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Nombre completo *</span>
                  <input
                    type="text"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    className="input input-bordered w-full"
                    required disabled={isLoading || !!existingInvolucrado}
                    placeholder="Nombre completo"
                    maxLength={100}
                  />
                </div>

                {/* [2.2] Celular */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Celular</span>
                  <input
                    type="text"
                    value={formData.celular}
                    onChange={(e) => setFormData({ ...formData, celular: e.target.value.replace(/\D/g, "") })}
                    className="input input-bordered w-full font-mono"
                    disabled={isLoading || !!existingInvolucrado}
                    placeholder="3001234567"
                    maxLength={15}
                  />
                </div>

                {/* [2.3] Correo */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Correo</span>
                  <input
                    type="email"
                    value={formData.correo}
                    onChange={(e) => setFormData({ ...formData, correo: e.target.value })}
                    className="input input-bordered w-full"
                    disabled={isLoading || !!existingInvolucrado}
                    placeholder="ejemplo@correo.com"
                    maxLength={100}
                  />
                </div>

                {/* [3.1-3.3] Dirección (ocupa toda la fila) */}
                <div className="col-span-3 flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Dirección</span>
                  <input
                    type="text"
                    value={formData.direccion}
                    onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                    className="input input-bordered w-full"
                    disabled={isLoading || !!existingInvolucrado}
                    placeholder="Dirección de residencia o notificación"
                    maxLength={200}
                  />
                </div>
              </div>

              {/* Botones */}
              <div className="flex items-center gap-2 pt-2 border-t border-base-300">
                {existingInvolucrado && (
                  <div className="flex items-center gap-1.5 text-success text-xs flex-1">
                    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Involucrado encontrado — solo se vinculará al expediente</span>
                  </div>
                )}
                <div className="flex gap-2 ml-auto">
                <button type="button" onClick={resetForm} className="btn btn-ghost btn-sm" disabled={isLoading}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-warning btn-sm text-white gap-1.5" disabled={isLoading}>
                  {isLoading ? (
                    <><span className="loading loading-spinner loading-xs" />
                      {existingInvolucrado ? "Vinculando..." : "Creando..."}</>
                  ) : (
                    <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      {existingInvolucrado ? "Vincular" : "Crear y Vincular"}</>
                  )}
                </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
