import { useState, type FormEvent } from "react";
import { Leaf } from "lucide-react";
import { Modal } from "@shared/ui";
import { detalleError } from "../api/errors";
import { useGuardarMatrizMutation, useMatrizRecursosQuery } from "../api/informes";
import MatrizRecursosEditor from "../informe-tecnico/MatrizRecursosEditor";
import { errorMatriz, matrizInicial, normalizarMatriz } from "../informe-tecnico/recursos";
import type { FilaRecursoAfectado } from "../types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  informeId: number;
  /** Matriz ya cargada (p. ej. la de la etapa): evita volver a pedirla. */
  filasIniciales?: FilaRecursoAfectado[] | null;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

const FORM_ID = "matriz-recursos-form";

/**
 * Editar la matriz de un informe de VISITA ya aceptado (PUT /informes/{id}/recursos).
 * Solo la matriz: el informe no se toca. Puede el técnico asignado hasta
 * Acoger concepto, y super gestión en informes MANUAL (lo decide el backend).
 */
export default function MatrizRecursosAfectadosModal({ isOpen, onClose, informeId, filasIniciales, setToast }: Props) {
  const matriz = useMatrizRecursosQuery(informeId, isOpen && !filasIniciales);
  const guardar = useGuardarMatrizMutation(informeId);
  const inicial = filasIniciales ?? matriz.data;

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
            disabled={guardar.isPending || !inicial}
          >
            {guardar.isPending ? <span className="loading loading-spinner loading-xs" /> : "Guardar"}
          </button>
        </>
      }
    >
      {inicial ? (
        <FormularioMatriz
          inicial={inicial}
          ocupado={guardar.isPending}
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
      ) : matriz.isError ? (
        <div role="alert" className="alert alert-error py-2 text-sm">
          {detalleError(matriz.error) ?? "Error al cargar la matriz"}
        </div>
      ) : (
        <div className="flex justify-center items-center min-h-[26rem]">
          <span className="loading loading-spinner loading-md text-success" />
        </div>
      )}
    </Modal>
  );
}

function FormularioMatriz({
  inicial,
  ocupado,
  errorServidor,
  onGuardar,
}: {
  inicial: FilaRecursoAfectado[];
  ocupado: boolean;
  errorServidor: string | null;
  onGuardar: (filas: FilaRecursoAfectado[]) => void;
}) {
  const [filas, setFilas] = useState(() => matrizInicial(inicial));
  const [error, setError] = useState<string | null>(null);

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    const invalido = errorMatriz(filas);
    if (invalido) return setError(invalido);
    onGuardar(normalizarMatriz(filas));
  };

  return (
    <form id={FORM_ID} onSubmit={enviar} className="space-y-4">
      <MatrizRecursosEditor
        filas={filas}
        disabled={ocupado}
        onChange={(nuevas) => {
          setFilas(nuevas);
          setError(null);
        }}
      />
      {(error || errorServidor) && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          {error || errorServidor}
        </div>
      )}
    </form>
  );
}
