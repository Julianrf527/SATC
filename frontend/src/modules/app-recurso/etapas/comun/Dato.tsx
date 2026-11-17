import type { ReactNode } from "react";
import { FileText } from "lucide-react";
import { isValidDocumentId, openDocumentById } from "@shared/lib/documentViewer";

type DatoProps = { icono: ReactNode; label: string; children: ReactNode; destacado?: boolean };

/** Par etiqueta / valor con icono (mismo aspecto que los datos del informe técnico de infraction). */
export function Dato({ icono, label, children, destacado }: DatoProps) {
  return (
    <div className="flex items-start gap-2">
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
          destacado ? "bg-success/10 text-success" : "bg-base-200 text-base-content/70"
        }`}
      >
        {icono}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">{label}</p>
        <div className={`text-sm font-semibold break-words ${destacado ? "text-success" : ""}`}>{children}</div>
      </div>
    </div>
  );
}

/** Valor vacío ("Sin registrar" en cursiva). */
export const SinDato = ({ texto = "Sin registrar" }: { texto?: string }) => (
  <span className="text-base-content/60 italic font-normal">{texto}</span>
);

/** Botón para abrir un PDF de app-docs (o "Sin documento"). */
export function VerDocumento({ fileId, texto = "Ver documento" }: { fileId: number | null | undefined; texto?: string }) {
  if (!isValidDocumentId(fileId)) return <SinDato texto="Sin documento" />;
  return (
    <button
      type="button"
      onClick={() => openDocumentById(fileId)}
      className="btn btn-ghost btn-xs gap-1 text-success px-1"
      title={texto}
    >
      <FileText size={14} />
      {texto}
    </button>
  );
}
