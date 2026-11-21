import { useState } from "react";
import { AlertCircle, FileSignature } from "lucide-react";
import { toastService } from "@shared/lib/toastService";
import { validateFile } from "@shared/lib/fileUpload";
import { detalleError } from "../api/errors";
import { useVersionFinalInformeMutation } from "../api/informes";
import MatrizRecursosEditor from "./MatrizRecursosEditor";
import { errorMatriz, matrizInicial, normalizarMatriz } from "./recursos";

type Props = {
  procesoId: number;
  /** La matriz de recursos solo aplica (y es obligatoria) en informes de VISITA. */
  conMatriz: boolean;
  onCargado: () => void;
};

/**
 * Con el informe "Aprobado para firma", el técnico carga aquí la versión
 * firmada (PDF) y, si es de VISITA, la matriz de recursos afectados. Al
 * cargarla el informe queda aceptado (POST /revision-informes/{id}/version-final).
 */
export default function CargarVersionFinal({ procesoId, conMatriz, onCargado }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [filas, setFilas] = useState(() => matrizInicial());
  const [error, setError] = useState<string | null>(null);
  const cargar = useVersionFinalInformeMutation(procesoId);

  const guardar = () => {
    if (!archivo) return setError("Selecciona el informe firmado (PDF)");
    const validacion = validateFile(archivo, ["application/pdf"]);
    if (!validacion.isValid) return setError(validacion.error ?? "El informe firmado debe ser PDF");
    if (conMatriz) {
      const invalido = errorMatriz(filas);
      if (invalido) return setError(invalido);
    }
    setError(null);
    cargar.mutate(
      { archivo, ...(conMatriz ? { recursosAfectados: normalizarMatriz(filas) } : {}) },
      {
        onSuccess: (res) => {
          toastService.showToast({ id: Date.now(), message: res?.message || "Informe aceptado", type: "success" });
          onCargado();
        },
        onError: (err) => setError(detalleError(err) ?? "Error al cargar la versión final"),
      },
    );
  };

  return (
    <div className="border border-success/40 bg-success/5 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2">
        <FileSignature size={18} className="text-success" />
        <div>
          <p className="font-semibold text-sm">Cargar versión final del informe</p>
          <p className="text-xs text-base-content/60">
            {conMatriz
              ? "PDF firmado y matriz de recursos afectados. Al cargarla el informe queda aceptado."
              : "PDF firmado. Al cargarlo el informe queda aceptado."}
          </p>
        </div>
      </div>

      <fieldset disabled={cargar.isPending} className="space-y-4">
        <div className="flex flex-col">
          <label htmlFor={`version-final-${procesoId}`} className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Informe firmado (PDF) <span className="text-error">*</span>
            </span>
          </label>
          <input
            id={`version-final-${procesoId}`}
            type="file"
            accept=".pdf,application/pdf"
            className="file-input file-input-sm w-full"
            onChange={(e) => {
              setArchivo(e.target.files?.[0] ?? null);
              setError(null);
            }}
          />
        </div>

        {conMatriz && (
          <div className="space-y-1">
            <p className="text-sm font-medium">
              Recursos afectados <span className="text-error">*</span>
            </p>
            <p className="text-xs text-base-content/60">
              Marca la magnitud del recurso afectado y su reversibilidad. Los recursos sin magnitud quedan como "No existe".
            </p>
            <MatrizRecursosEditor
              filas={filas}
              disabled={cargar.isPending}
              onChange={(nuevas) => {
                setFilas(nuevas);
                setError(null);
              }}
            />
          </div>
        )}
      </fieldset>

      {error && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      <div className="flex justify-end">
        <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={guardar} disabled={cargar.isPending}>
          {cargar.isPending ? <span className="loading loading-spinner loading-xs" /> : <FileSignature size={14} />}
          Cargar versión final
        </button>
      </div>
    </div>
  );
}
