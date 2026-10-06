import { useState } from "react";
import { useAuth } from "@shared/context/AuthContext";
import InformeTecnicoEtapa from "../informe-tecnico/InformeTecnicoEtapa";
import MatrizRecursosAfectadosModal from "../modal/MatrizRecursosAfectadosModal";
import type { InformeTecnico } from "../types";
import MatrizRecursosAfectadosView from "./MatrizRecursosAfectadosView";

const PERMISO_CARGUE = "infraccion_cargue";
const STAGE_NAME = "Visita Técnica";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable?: boolean;
};

/** Etapa "Visita Técnica": informe técnico VISITA + matriz de recursos afectados. */
export default function VisitStage({ expedienteId, setToast, isEditable }: Props) {
  const { user } = useAuth();
  const tieneCarguePermiso = !!isEditable && (user?.permisos ?? []).some((p) => p.name === PERMISO_CARGUE);
  const [matrizInformeId, setMatrizInformeId] = useState<number | null>(null);

  const matriz = (informe: InformeTecnico) => {
    const editableManual = tieneCarguePermiso && informe.modo === "MANUAL";
    if (informe.aceptado && informe.tiene_matriz && informe.recursos_afectados) {
      return (
        <div className="mt-4">
          <MatrizRecursosAfectadosView
            filas={informe.recursos_afectados}
            action={
              editableManual ? (
                <button onClick={() => setMatrizInformeId(informe.id)} className="btn btn-outline btn-sm">
                  Editar matriz
                </button>
              ) : undefined
            }
          />
        </div>
      );
    }
    if (informe.aceptado && editableManual) {
      return (
        <div className="mt-4 card bg-base-100 shadow-md border border-base-300">
          <div className="card-body flex-row items-center justify-between gap-3">
            <p className="text-sm text-base-content/70">Aún no se ha diligenciado la matriz de recursos afectados.</p>
            <button onClick={() => setMatrizInformeId(informe.id)} className="btn btn-success text-white btn-sm">
              Agregar matriz
            </button>
          </div>
        </div>
      );
    }
    if (!informe.aceptado && tieneCarguePermiso) {
      return (
        <div className="mt-4 card bg-base-100 shadow-md border border-base-300">
          <div className="card-body">
            <p className="text-sm text-base-content/60">
              Completa el informe para poder cargar la matriz de recursos afectados.
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <>
      <InformeTecnicoEtapa
        expedienteId={expedienteId}
        tipo="VISITA"
        etapa={STAGE_NAME}
        titulo="Datos de la Visita Técnica"
        setToast={setToast}
        isEditable={isEditable}
        extra={matriz}
      />
      {matrizInformeId !== null && (
        <MatrizRecursosAfectadosModal
          isOpen
          onClose={() => setMatrizInformeId(null)}
          informeId={matrizInformeId}
          setToast={setToast}
        />
      )}
    </>
  );
}
