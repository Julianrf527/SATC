import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiCall, API_CONFIG } from "../../../utils/api";
import type { InformeTecnico } from "../../../types/infraccionApp";
import AsignarProfesionalModal from "../Modal/AsignarProfesionalModal";
import DocumentoDetalleModal from "../../app-documentos/layout/DocumentoDetalleModal";
import { FileText } from "lucide-react";
import { useInformesTecnicos } from "./AsignarInformes/useInformesTecnicos";
import InformesFiltros from "./AsignarInformes/InformesFiltros";
import InformesTable from "./AsignarInformes/InformesTable";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function AsignarInformes({ setToast }: Props) {
  const navigate = useNavigate();

  const state = useInformesTecnicos(setToast);
  const { loading, totalCount, page, totalPages, profesionales, loadInformes } =
    state;

  // ── Modales ──────────────────────────────────────────────────────────────
  const [asignarModal, setAsignarModal] = useState<{
    open: boolean;
    informe: InformeTecnico | null;
    isReassign: boolean;
  }>({ open: false, informe: null, isReassign: false });

  const [docsModal, setDocsModal] = useState<{
    open: boolean;
    docsDocumentoId: number | null;
    informeId: number | null;
  }>({ open: false, docsDocumentoId: null, informeId: null });

  // ── Asignar / Reasignar profesional ──────────────────────────────────────
  const handleAsignarSubmit = async (
    profesionalId: number,
    fechaProgramacion: string,
  ) => {
    if (!asignarModal.informe) return;

    const informe = asignarModal.informe;
    const isReassign = asignarModal.isReassign;
    const method = isReassign ? "PUT" : "POST";

    const res = await apiCall(
      API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_ASSIGN(informe.id),
      {
        method,
        body: JSON.stringify({
          profesional_id: profesionalId,
          ...(fechaProgramacion
            ? { fecha_programacion_visita: fechaProgramacion }
            : {}),
        }),
      },
    );

    if (res.ok) {
      setToast({
        id: Date.now(),
        message: isReassign
          ? "Profesional reasignado exitosamente"
          : "Profesional asignado exitosamente",
        type: "success",
      });
      loadInformes(page);
    } else {
      throw new Error(res.detail || "Error al asignar profesional");
    }
  };

  // ── Sync luego de aprobar en app-docs ─────────────────────────────────────
  const handleDocAprobado = async (informeId: number) => {
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_SYNC(informeId),
        { method: "PUT" },
      );
      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Informe técnico actualizado como aceptado",
          type: "success",
        });
        loadInformes(page);
      } else {
        // No es error crítico: el documento puede no estar aprobado todavía.
        if (res.ok === false && res.message) {
          setToast({ id: Date.now(), message: res.message, type: "error" });
        }
      }
    } catch {
      // Igual que arriba: el fallo de sync no debe interrumpir el flujo.
    }
    setDocsModal({ open: false, docsDocumentoId: null, informeId: null });
  };

  // ── Ir al expediente ──────────────────────────────────────────────────────
  const goToExpediente = (informe: InformeTecnico) => {
    navigate("/infraction/consult", {
      state: {
        radicadoToSelect: informe.expediente_radicado,
        timestamp: Date.now(),
      },
    });
  };


  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <FileText className="text-success" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  Módulo de Infracciones
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Informes Técnicos
                </h1>
              </div>
            </div>
            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                    Total informes
                  </p>
                  <p className="text-lg font-bold text-success leading-tight">
                    {totalCount}
                    <span className="text-xs font-normal text-base-content/50 ml-1">
                      pág. {page}/{totalPages}
                    </span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">
          <InformesFiltros state={state} />

          <InformesTable
            state={state}
            onGoToExpediente={goToExpediente}
            onVerProceso={(inf) =>
              setDocsModal({
                open: true,
                docsDocumentoId: inf.docs_documento_id!,
                informeId: inf.id,
              })
            }
            onAsignar={(inf) =>
              setAsignarModal({
                open: true,
                informe: inf,
                isReassign: inf.proceso_activo || !!inf.profesional_asignado_id,
              })
            }
          />
        </div>
      </div>

      {/* Modal asignar/reasignar profesional */}
      <AsignarProfesionalModal
        isOpen={asignarModal.open}
        onClose={() =>
          setAsignarModal({ open: false, informe: null, isReassign: false })
        }
        onSubmit={handleAsignarSubmit}
        profesionales={profesionales}
        profesionalActualId={asignarModal.informe?.profesional_asignado_id}
        fechaProgramacionActual={
          asignarModal.informe?.fecha_programacion_visita
        }
        isReassign={asignarModal.isReassign}
      />

      {/* Modal proceso de documentos (reutiliza app-docs) */}
      {docsModal.open && docsModal.docsDocumentoId && (
        <DocumentoDetalleModal
          isOpen={docsModal.open}
          onClose={() =>
            setDocsModal({
              open: false,
              docsDocumentoId: null,
              informeId: null,
            })
          }
          documentoId={docsModal.docsDocumentoId}
          setToast={setToast}
          onUpdate={() => {
            // Cuando hay una actualización (aprobación/devolución), sincronizar con app-infraction
            if (docsModal.informeId) {
              handleDocAprobado(docsModal.informeId);
            } else {
              loadInformes(page);
              setDocsModal({
                open: false,
                docsDocumentoId: null,
                informeId: null,
              });
            }
          }}
        />
      )}
    </>
  );
}
