import { Eye, FileText, X } from "lucide-react";
import { Campo } from "@shared/ui/form/Campo";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatFileSize } from "@shared/lib/format";

type Props = {
  /** PDF nuevo elegido (aún no subido). */
  archivo: File | null;
  onChange: (archivo: File | null) => void;
  /** Comprobante ya guardado (edición): se puede ver o reemplazar. */
  fileIdActual?: number | null;
  disabled?: boolean;
};

/**
 * Comprobante de pago (PDF). Se sube a app-docs al guardar el formulario,
 * igual que los archivos de infraction; aquí solo se elige el archivo.
 */
export default function ComprobantePagoField({ archivo, onChange, fileIdActual = null, disabled = false }: Props) {
  return (
    <Campo
      etiqueta="Comprobante de pago (PDF) *"
      ayuda={fileIdActual ? "Adjunta un PDF solo si quieres reemplazar el comprobante actual" : "Solo PDF"}
    >
      {fileIdActual && !archivo && (
        <button
          type="button"
          className="btn btn-ghost btn-xs gap-1 text-success self-start mb-1 -ml-2"
          onClick={() => openDocumentById(fileIdActual)}
        >
          <Eye size={14} />
          Ver comprobante actual
        </button>
      )}
      {archivo ? (
        <div className="flex items-center gap-2 border border-base-300 rounded-lg px-3 py-2 bg-base-200/40">
          <FileText size={16} className="text-error flex-shrink-0" />
          <span className="text-sm truncate flex-1" title={archivo.name}>
            {archivo.name}
          </span>
          <span className="text-xs text-base-content/60">{formatFileSize(archivo.size)}</span>
          <button
            type="button"
            className="btn btn-ghost btn-xs text-error"
            onClick={() => onChange(null)}
            disabled={disabled}
            aria-label="Quitar archivo"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <input
          type="file"
          accept="application/pdf,.pdf"
          className="file-input w-full"
          disabled={disabled}
          onChange={(e) => {
            onChange(e.target.files?.[0] ?? null);
            e.target.value = "";
          }}
        />
      )}
    </Campo>
  );
}
