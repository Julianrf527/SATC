import { AlertTriangle, Trash2, UserCog } from "lucide-react";
import type { VinculoInvolucrado } from "../../types";
import { documentoPersona, nombrePersona } from "./personaForm";

const DOC_BADGE: Record<string, string> = {
  CC: "badge-info",
  NIT: "badge-success",
  CE: "badge-warning",
  PP: "badge-secondary",
};

type Props = {
  vinculo: VinculoInvolucrado;
  ocupado: boolean;
  /** Se pasan solo si el backend manda la acción (`acciones_disponibles`). */
  onEditarRepresentante?: () => void;
  onDesvincular?: () => void;
};

/** Fila de un solicitante vinculado (mismo aspecto que InvolucradoItem de la feature). */
export default function SolicitanteItem({ vinculo, ocupado, onEditarRepresentante, onDesvincular }: Props) {
  const p = vinculo.involucrado;
  const nombre = nombrePersona(p);
  const iniciales = nombre
    .split(" ")
    .map((n) => n?.[0] ?? "")
    .join("")
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="border border-base-300 rounded-lg p-3 hover:bg-base-200/40 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-warning/20 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-bold text-tono-warning">{iniciales}</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="text-base font-semibold truncate">{nombre}</span>
            {p.tipo_documento && (
              <span className={`badge badge-sm ${DOC_BADGE[p.tipo_documento] || "badge-ghost"}`}>{p.tipo_documento}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-sm text-base-content/60">
            <span className="font-mono">{documentoPersona(p) || "—"}</span>
            <span>{p.celular ? String(p.celular) : <span className="italic opacity-50">Sin teléfono</span>}</span>
            <span className="truncate">{p.correo?.trim() ? p.correo : <span className="italic opacity-50">Sin correo</span>}</span>
          </div>
          {vinculo.requiere_representante && (
            <p className="text-xs mt-1 flex items-center gap-1">
              {vinculo.representante ? (
                <>
                  <span className="text-base-content/60">Representante legal:</span>
                  <span className="font-medium">{nombrePersona(vinculo.representante)}</span>
                  <span className="font-mono text-base-content/60">{documentoPersona(vinculo.representante)}</span>
                </>
              ) : (
                <span className="text-tono-warning flex items-center gap-1">
                  <AlertTriangle size={12} /> Falta el representante legal
                </span>
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1">
          {onEditarRepresentante && (
            <button
              type="button"
              onClick={onEditarRepresentante}
              disabled={ocupado}
              className="btn btn-ghost btn-xs"
              title="Cambiar representante legal"
            >
              <UserCog size={14} />
            </button>
          )}
          {onDesvincular && (
            <button
              type="button"
              onClick={onDesvincular}
              disabled={ocupado}
              className="btn btn-ghost btn-xs text-error hover:bg-error/10"
              title="Desvincular"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
