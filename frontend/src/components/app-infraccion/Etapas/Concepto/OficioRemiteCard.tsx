import { useRef, useState, useMemo } from "react";

const RADICADO_REGEX = /^\d{4}EE\d{4,5}$/;
import { apiCall, API_CONFIG } from "../../../../utils/api";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../../utils/fileUpload";
import { openDocumentById } from "../../../../utils/documentViewer";

type OficioRemite = {
  id: number;
  radicado: string;
  fecha_radicado: string;
  fecha_remitido: string;
  archivo_remite_id: number;
};

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  oficio: OficioRemite | null;
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onSaved: () => void;
};

export default function OficioRemiteCard({
  etapaConceptoId,
  expedienteId: _expedienteId,
  oficio,
  isEditable,
  setToast,
  onSaved,
}: Props) {
  const [showForm, setShowForm] = useState(!oficio);
  const [radicado, setRadicado] = useState(oficio?.radicado ?? "");
  const [fechaRadicado, setFechaRadicado] = useState(oficio?.fecha_radicado ?? "");
  const [fechaRemitido, setFechaRemitido] = useState(oficio?.fecha_remitido ?? "");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const radicadoValido = useMemo(() => radicado === "" || RADICADO_REGEX.test(radicado), [radicado]);
  const hoy = new Date().toISOString().split("T")[0];

  const handleCancel = () => {
    setShowForm(false);
    if (oficio) {
      setRadicado(oficio.radicado);
      setFechaRadicado(oficio.fecha_radicado);
      setFechaRemitido(oficio.fecha_remitido);
    }
    setSelectedFile(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      let archivoId = oficio?.archivo_remite_id;

      if (selectedFile) {
        setIsUploading(true);
        archivoId = await uploadFileToDocuments(
          selectedFile,
          generateDocumentFileName("OFICIO", radicado, fechaRemitido),
        );
        setIsUploading(false);
      }

      if (!RADICADO_REGEX.test(radicado.trim())) {
        setToast({ id: Date.now(), message: "El radicado no cumple el formato requerido (ej: 2024EE0001)", type: "error" });
        return;
      }

      if (!archivoId) {
        setToast({ id: Date.now(), message: "Debe adjuntar el documento del oficio", type: "error" });
        return;
      }

      const body = {
        radicado,
        fecha_radicado: fechaRadicado,
        fecha_remitido: fechaRemitido,
        archivo_remite_id: archivoId,
      };

      const endpoint = oficio
        ? API_CONFIG.ENDPOINTS.INFRACTION_PUT_OFICIO_REMITE(oficio.id)
        : API_CONFIG.ENDPOINTS.INFRACTION_CREATE_OFICIO_REMITE(etapaConceptoId);
      const method = oficio ? "PUT" : "POST";

      const res = await apiCall(endpoint, {
        method,
        body: JSON.stringify(body),
      });

      if (res.ok) {
        setToast({ id: Date.now(), message: oficio ? "Oficio actualizado" : "Oficio registrado", type: "success" });
        setShowForm(false);
        onSaved();
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al guardar oficio", type: "error" });
      }
    } catch (err) {
      setToast({ id: Date.now(), message: err instanceof Error ? err.message : "Error", type: "error" });
    } finally {
      setIsSubmitting(false);
      setIsUploading(false);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-accent/10 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
              </svg>
            </div>
            <div>
              <h4 className="font-bold">Oficio Remite</h4>
              <p className="text-xs text-base-content/60">
                {oficio ? "Información del oficio registrado" : "Remisión por competencia / solicitud de información"}
              </p>
            </div>
          </div>
          {!showForm && isEditable && oficio && (
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

        {/* Vista datos */}
        {!showForm && oficio && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 p-4 bg-base-200/40 rounded-xl">
            <div>
              <p className="text-xs font-medium text-base-content/50 uppercase tracking-wide">Radicado</p>
              <p className="text-sm font-semibold mt-1">{oficio.radicado}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/50 uppercase tracking-wide">Fecha Radicado</p>
              <p className="text-sm font-semibold mt-1">{oficio.fecha_radicado || "—"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/50 uppercase tracking-wide">Fecha Remitido</p>
              <p className="text-sm font-semibold mt-1">{oficio.fecha_remitido}</p>
            </div>
            <div className="flex items-end">
              <button
                className="btn btn-success btn-sm gap-1"
                onClick={() => openDocumentById(oficio.archivo_remite_id)}
              >
                <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M13,3.5L17.5,8H13V3.5Z" />
                </svg>
                <span className="text-xs text-white">Ver documento</span>
              </button>
            </div>
          </div>
        )}

        {/* Formulario */}
        {showForm && isEditable && (
          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Radicado *</span>
                  <span className="label-text-alt text-base-content/40">ej: 2024EE0001</span>
                </label>
                <input
                  type="text"
                  className={`input input-bordered w-full ${radicado && !radicadoValido ? "input-error" : radicado && radicadoValido ? "input-success" : ""}`}
                  value={radicado}
                  onChange={(e) => setRadicado(e.target.value.toUpperCase())}
                  disabled={isSubmitting}
                  maxLength={11}
                  placeholder="2024EE0001"
                  required
                />
                {radicado && !radicadoValido && (
                  <label className="label">
                    <span className="label-text-alt text-error">Formato inválido. Use: 4 dígitos + EE + 4 o 5 dígitos</span>
                  </label>
                )}
              </div>
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Fecha Radicado *</span>
                </label>
                <input
                  type="date"
                  className="input input-bordered w-full"
                  value={fechaRadicado}
                  onChange={(e) => setFechaRadicado(e.target.value)}
                  max={hoy}
                  disabled={isSubmitting}
                  required
                />
              </div>
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Fecha Remitido *</span>
                </label>
                <input
                  type="date"
                  className="input input-bordered w-full"
                  value={fechaRemitido}
                  onChange={(e) => setFechaRemitido(e.target.value)}
                  max={hoy}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Documento PDF{!oficio && <span className="text-error"> *</span>}
                  {oficio && <span className="text-xs text-base-content/40 ml-2">(opcional: reemplazar)</span>}
                </span>
              </label>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                className="file-input file-input-bordered w-full"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                disabled={isSubmitting}
                required={!oficio}
              />
              {selectedFile && (
                <div className="mt-2 flex items-center gap-2 text-sm text-success">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {selectedFile.name}
                </div>
              )}
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {oficio && (
                <button type="button" className="btn btn-outline" onClick={handleCancel} disabled={isSubmitting}>
                  Cancelar
                </button>
              )}
              <button type="submit" className="btn btn-accent text-white gap-2" disabled={isSubmitting || !radicadoValido || !radicado}>
                {isUploading ? (
                  <><span className="loading loading-spinner loading-sm" />Subiendo...</>
                ) : isSubmitting ? (
                  <><span className="loading loading-spinner loading-sm" />Guardando...</>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {oficio ? "Actualizar Oficio" : "Registrar Oficio"}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
