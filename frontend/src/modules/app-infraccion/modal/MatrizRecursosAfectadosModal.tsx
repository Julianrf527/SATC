import { useState, type FormEvent } from "react";
import { Leaf } from "lucide-react";
import { Modal } from "@shared/ui";
import { detalleError } from "../api/errors";
import { useGuardarMatrizMutation, useMatrizRecursosQuery } from "../api/informes";
import {
  MAGNITUDES,
  RECURSO_LABELS,
  REVERSIBILIDADES,
  type Magnitud,
  type Reversibilidad,
} from "../informe-tecnico/recursos";
import type { FilaRecursoAfectado, RecursoMatriz } from "../types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  informeId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

const FORM_ID = "matriz-recursos-form";

export default function MatrizRecursosAfectadosModal({ isOpen, onClose, informeId, setToast }: Props) {
  const matriz = useMatrizRecursosQuery(informeId, isOpen);
  const guardar = useGuardarMatrizMutation(informeId);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="4xl"
      icon={<Leaf size={18} />}
      title="Recursos Afectados"
      subtitle='Marca la magnitud del recurso afectado; al hacerlo se habilita su reversibilidad. Los recursos sin magnitud quedan como "No existe".'
      closeOnEsc={!guardar.isPending}
      closeOnBackdrop={!guardar.isPending}
      footer={
        <>
          <button type="button" onClick={onClose} className="btn btn-ghost btn-sm" disabled={guardar.isPending}>
            Cancelar
          </button>
          <button
            type="submit"
            form={FORM_ID}
            className="btn btn-success text-white btn-sm gap-2"
            disabled={guardar.isPending || !matriz.data}
          >
            {guardar.isPending ? <span className="loading loading-spinner loading-xs" /> : "Guardar"}
          </button>
        </>
      }
    >
      {matriz.isPending ? (
        <div className="flex justify-center items-center min-h-[26rem]">
          <span className="loading loading-spinner loading-md text-success" />
        </div>
      ) : matriz.isError ? (
        <div role="alert" className="alert alert-error py-2 text-sm">
          {detalleError(matriz.error) ?? "Error al cargar la matriz"}
        </div>
      ) : (
        <MatrizEditor
          inicial={matriz.data}
          errorServidor={guardar.isError ? (detalleError(guardar.error) ?? "Error al guardar la matriz") : null}
          onGuardar={(filas) =>
            guardar.mutate(filas, {
              onSuccess: () => {
                setToast({ id: Date.now(), message: "Matriz de recursos afectados guardada", type: "success" });
                onClose();
              },
            })
          }
        />
      )}
    </Modal>
  );
}

function MatrizEditor({
  inicial,
  errorServidor,
  onGuardar,
}: {
  inicial: FilaRecursoAfectado[];
  errorServidor: string | null;
  onGuardar: (filas: FilaRecursoAfectado[]) => void;
}) {
  const [filas, setFilas] = useState(inicial);
  const [error, setError] = useState("");

  const actualizar = (recurso: RecursoMatriz, cambio: (f: FilaRecursoAfectado) => FilaRecursoAfectado) => {
    setFilas((prev) => prev.map((f) => (f.recurso === recurso ? cambio(f) : f)));
    setError("");
  };

  const toggleMagnitud = (recurso: RecursoMatriz, m: Magnitud) =>
    actualizar(recurso, (f) => (f.magnitud === m ? { ...f, magnitud: null, reversibilidad: null } : { ...f, magnitud: m }));

  const toggleReversibilidad = (recurso: RecursoMatriz, r: Reversibilidad) =>
    actualizar(recurso, (f) => ({ ...f, reversibilidad: f.reversibilidad === r ? null : r }));

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    const incompletas = filas.filter((f) => f.magnitud && !f.reversibilidad);
    if (incompletas.length > 0) {
      setError(`Falta la reversibilidad de: ${incompletas.map((f) => RECURSO_LABELS[f.recurso]).join(", ")}`);
      return;
    }
    onGuardar(filas.map((f) => ({ ...f, no_existe: !f.magnitud })));
  };

  return (
    <form id={FORM_ID} onSubmit={enviar} className="space-y-4">
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
              const nombre = RECURSO_LABELS[f.recurso];
              return (
                <tr key={f.recurso}>
                  <td className="font-medium">{nombre}</td>
                  {MAGNITUDES.map((m, i) => (
                    <td key={m} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                      <input
                        type="radio"
                        aria-label={`${nombre}: ${m.toLowerCase()}`}
                        className="radio radio-success radio-sm"
                        checked={f.magnitud === m}
                        onChange={() => {}}
                        onClick={() => toggleMagnitud(f.recurso, m)}
                      />
                    </td>
                  ))}
                  {REVERSIBILIDADES.map((r, i) => (
                    <td key={r} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                      <input
                        type="radio"
                        aria-label={`${nombre}: ${r.toLowerCase()}`}
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
                      aria-label={`${nombre}: no existe`}
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

      {(error || errorServidor) && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          {error || errorServidor}
        </div>
      )}
    </form>
  );
}
