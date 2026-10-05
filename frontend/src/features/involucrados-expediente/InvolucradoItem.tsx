import type { Involucrado } from "@shared/types/involucrado";

const DOC_BADGE: Record<string, string> = {
  CC: "badge-info", NIT: "badge-success", CE: "badge-warning", PP: "badge-secondary",
};

type Props = {
  inv: Involucrado;
  isLoading: boolean;
  /** Si se omite no se muestra el botón de desvincular. */
  onDelete?: () => void;
};

/** Fila de un involucrado vinculado al expediente. */
export default function InvolucradoItem({ inv, isLoading, onDelete }: Props) {
  return (
    <div
      className="border border-base-300 rounded-lg p-3 hover:bg-base-200/40 transition-colors"
    >
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-warning/20 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-bold text-tono-warning">
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
        {onDelete && (
          <button
            onClick={onDelete}
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
  );
}
