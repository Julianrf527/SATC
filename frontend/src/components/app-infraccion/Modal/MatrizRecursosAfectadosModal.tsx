import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Leaf } from "lucide-react";
import { apiCall, API_CONFIG, getErrorMessage } from "../../../utils/api";
import type { FilaRecursoAfectado, RecursoMatriz } from "../../../types/infraccionApp";

const RECURSO_LABELS: Record<RecursoMatriz, string> = {
  AIRE: "Aire",
  SUELO: "Suelo",
  AGUA: "Agua",
  PAISAJE: "Paisaje",
  FLORA: "Flora",
  FAUNA: "Fauna",
  RUIDO: "Ruido",
  SOCIAL: "Social",
  OTRO: "Otro",
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  informeId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function MatrizRecursosAfectadosModal({
  isOpen,
  onClose,
  informeId,
  setToast,
}: Props) {
  const [filas, setFilas] = useState<FilaRecursoAfectado[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState("emerald");

  useEffect(() => {
    const update = () => {
      const t = document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald";
      setTheme(t);
    };
    update();
    const obs = new MutationObserver(update);
    const node = document.querySelector("[data-theme]");
    if (node) obs.observe(node, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    setError("");
    setLoading(true);
    apiCall(API_CONFIG.ENDPOINTS.INFRACTION_INFORME_RECURSOS(informeId), { method: "GET" })
      .then((res) => {
        if (res.ok) {
          setFilas(res.data);
        } else {
          setError(res.detail || "Error al cargar la matriz");
        }
      })
      .catch(() => setError("Error de conexión"))
      .finally(() => setLoading(false));
  }, [isOpen, informeId]);

  const toggleMagnitud = (recurso: RecursoMatriz, m: FilaRecursoAfectado["magnitud"]) => {
    setFilas((prev) =>
      prev.map((f) =>
        f.recurso === recurso
          ? f.magnitud === m
            ? { ...f, magnitud: null, reversibilidad: null }
            : { ...f, magnitud: m }
          : f,
      ),
    );
    setError("");
  };

  const toggleReversibilidad = (recurso: RecursoMatriz, r: FilaRecursoAfectado["reversibilidad"]) => {
    setFilas((prev) =>
      prev.map((f) =>
        f.recurso === recurso
          ? { ...f, reversibilidad: f.reversibilidad === r ? null : r }
          : f,
      ),
    );
    setError("");
  };

  const handleGuardar = async () => {
    const incompletas = filas.filter((f) => f.magnitud && !f.reversibilidad);
    if (incompletas.length > 0) {
      setError(
        `Falta la reversibilidad de: ${incompletas.map((f) => RECURSO_LABELS[f.recurso]).join(", ")}`,
      );
      return;
    }

    const filasParaEnviar = filas.map((f) => ({
      ...f,
      no_existe: !f.magnitud,
    }));

    setSaving(true);
    setError("");
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_INFORME_RECURSOS(informeId), {
        method: "PUT",
        body: JSON.stringify({ filas: filasParaEnviar }),
      });
      if (res.ok) {
        setToast({ id: Date.now(), message: "Matriz de recursos afectados guardada", type: "success" });
        onClose();
      } else {
        setError(res.detail || "Error al guardar la matriz");
      }
    } catch (e) {
      setError(getErrorMessage(e, "Error al guardar la matriz"));
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-base-100 rounded-xl w-full max-w-3xl shadow-2xl border border-base-300 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-base-300">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center">
              <Leaf className="text-success" size={18} />
            </div>
            <div>
              <h3 className="font-bold text-base text-base-content">Recursos Afectados</h3>
              <p className="text-xs text-base-content/50">
                Marca la magnitud del recurso afectado; al hacerlo se habilita su reversibilidad. Los recursos sin magnitud quedan marcados como "No existe".
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm btn-circle">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {loading ? (
            <div className="flex justify-center py-10">
              <span className="loading loading-spinner loading-md text-success" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table table-sm w-full">
                <thead>
                  <tr>
                    <th rowSpan={2} className="align-bottom">Recurso Afectado</th>
                    <th colSpan={3} className="text-center border-l border-base-300">Magnitud</th>
                    <th colSpan={2} className="text-center border-l border-base-300">Reversibilidad</th>
                    <th rowSpan={2} className="text-center align-bottom border-l border-base-300">No existe</th>
                  </tr>
                  <tr>
                    <th className="text-center border-l border-base-300">Leve</th>
                    <th className="text-center">Moderado</th>
                    <th className="text-center">Grave</th>
                    <th className="text-center border-l border-base-300">Reversible</th>
                    <th className="text-center">Irreversible</th>
                  </tr>
                </thead>
                <tbody>
                  {filas.map((f) => {
                    const noExiste = !f.magnitud;
                    return (
                      <tr key={f.recurso}>
                        <td className="font-medium">{RECURSO_LABELS[f.recurso]}</td>
                        {(["LEVE", "MODERADO", "GRAVE"] as const).map((m, i) => (
                          <td key={m} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                            <input
                              type="radio"
                              className="radio radio-success radio-sm"
                              checked={f.magnitud === m}
                              onChange={() => {}}
                              onClick={() => toggleMagnitud(f.recurso, m)}
                            />
                          </td>
                        ))}
                        {(["REVERSIBLE", "IRREVERSIBLE"] as const).map((r, i) => (
                          <td key={r} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                            <input
                              type="radio"
                              className="radio radio-success radio-sm"
                              checked={f.reversibilidad === r}
                              disabled={noExiste}
                              onChange={() => {}}
                              onClick={() => toggleReversibilidad(f.recurso, r)}
                            />
                          </td>
                        ))}
                        <td className="text-center border-l border-base-300">
                          <input
                            type="checkbox"
                            className="checkbox checkbox-sm"
                            checked={noExiste}
                            disabled
                            readOnly
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {error && (
            <div className="alert alert-error py-2">
              <span className="text-sm">{error}</span>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-base-300">
          <button onClick={onClose} className="btn btn-ghost btn-sm" disabled={saving}>
            Cancelar
          </button>
          <button onClick={handleGuardar} className="btn btn-success text-white btn-sm gap-2" disabled={saving || loading}>
            {saving ? <span className="loading loading-spinner loading-xs" /> : "Guardar"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
