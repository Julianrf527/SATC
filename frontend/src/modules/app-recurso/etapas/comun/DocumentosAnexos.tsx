import { useState } from "react";
import { FileText, Paperclip, Pencil, Plus, Trash2 } from "lucide-react";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import { Modal } from "@shared/ui";
import type { AnexoEtapa, SetToast } from "../../types";
import { bodyEditarAnexo, validarAnexo } from "../formularios/anexo";
import { CampoPdf, CampoTexto } from "./campos/Campos";
import ModalFormulario from "./ModalFormulario";
import { useEscritura } from "./useEscritura";

const MAX_NOMBRE = 100;

/** Ícono de PDF relleno del botón "Documento" (el mismo de sancionatorio). */
const PDF_RELLENO =
  "M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z";

type Props = {
  expedienteId: number;
  /** `etapa_tipo` e `id` del nodo dueño de los anexos (C.11). */
  etapaTipo: string;
  etapaRefId: number;
  anexos: AnexoEtapa[];
  /** El nodo trae `gestionar_anexos`. */
  puedeGestionar: boolean;
  setToast: SetToast;
  /** Título de la tarjeta (si un nodo muestra anexos de dos filas). */
  titulo?: string;
};

/**
 * Documentos anexos de un nodo (C.11): listar, agregar, editar (nombre y/o PDF) y eliminar.
 * Los carga el abogado (gestión); en consulta solo se listan. Réplica visual
 * de la tarjeta "Documentos" de sancionatorio (un módulo no importa otro).
 */
export default function DocumentosAnexos({
  expedienteId,
  etapaTipo,
  etapaRefId,
  anexos,
  puedeGestionar,
  setToast,
  titulo = "Documentos anexos",
}: Props) {
  const [agregando, setAgregando] = useState(false);
  const [editando, setEditando] = useState<AnexoEtapa | null>(null);
  const [eliminar, setEliminar] = useState<AnexoEtapa | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  if (anexos.length === 0 && !puedeGestionar) return null;

  const ordenados = [...anexos].sort(
    (a, b) => new Date(b.fecha_subida ?? 0).getTime() - new Date(a.fecha_subida ?? 0).getTime(),
  );

  const confirmarEliminar = () => {
    if (!eliminar) return;
    ejecutar(
      { peticion: () => ({ url: RECURSO_ENDPOINTS.RECURSO_ANEXO_DELETE(eliminar.id, expedienteId), method: "DELETE" }) },
      { exito: "Documento eliminado", error: "Error al eliminar el documento", onSuccess: () => setEliminar(null) },
    );
  };

  return (
    <div className="card bg-base-100 border border-base-300">
      <div className="card-body p-5">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-base font-bold">{titulo}</h3>
          {puedeGestionar && (
            <button type="button" className="btn btn-success text-white btn-sm gap-2" onClick={() => setAgregando(true)}>
              <Plus size={16} />
              Agregar Documento
            </button>
          )}
        </div>

        {ordenados.length === 0 ? (
          <div className="text-center py-6 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
            <div className="w-12 h-12 bg-base-300 rounded-full flex items-center justify-center mb-3 mx-auto">
              <FileText className="w-6 h-6 text-base-content/40" />
            </div>
            <h4 className="text-sm font-medium text-base-content/70 mb-1">Sin documentos</h4>
            <p className="text-xs text-base-content/60">No hay documentos anexos registrados</p>
          </div>
        ) : (
          <div className="space-y-2">
            {ordenados.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between p-4 bg-base-200 rounded-lg border border-base-300 hover:bg-base-300/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-base truncate" title={a.nombre}>
                    {a.nombre}
                  </p>
                  <p className="text-xs text-base-content/60 mt-1">{formatDate(a.fecha_subida, { style: "long" })}</p>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  {puedeGestionar && (
                    <>
                      <button
                        type="button"
                        onClick={() => setEditando(a)}
                        disabled={ocupado}
                        className="btn btn-ghost btn-sm btn-square"
                        title="Editar documento"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setEliminar(a)}
                        disabled={ocupado}
                        className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                        title="Eliminar documento"
                      >
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={() => openDocumentById(a.documento_anexo_id)}
                    className="btn btn-success btn-sm gap-1 px-2 tooltip"
                    data-tip="Ver documento PDF"
                  >
                    <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d={PDF_RELLENO} />
                    </svg>
                    <span className="text-xs font-medium text-white">Documento</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {agregando && (
        <AgregarAnexoModal
          expedienteId={expedienteId}
          etapaTipo={etapaTipo}
          etapaRefId={etapaRefId}
          setToast={setToast}
          onClose={() => setAgregando(false)}
        />
      )}

      {editando && (
        <EditarAnexoModal
          expedienteId={expedienteId}
          anexo={editando}
          setToast={setToast}
          onClose={() => setEditando(null)}
        />
      )}

      <Modal
        isOpen={eliminar !== null}
        onClose={() => setEliminar(null)}
        size="sm"
        icon={<Trash2 size={20} />}
        title="Eliminar documento"
        closeOnEsc={!ocupado}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEliminar(null)} disabled={ocupado}>
              Cancelar
            </button>
            <button type="button" className="btn btn-error btn-sm text-white" onClick={confirmarEliminar} disabled={ocupado}>
              {ocupado && <span className="loading loading-spinner loading-xs" />}
              Eliminar
            </button>
          </>
        }
      >
        <p className="text-sm">
          ¿Eliminar el documento <span className="font-semibold">{eliminar?.nombre}</span>?
        </p>
      </Modal>
    </div>
  );
}

type AgregarProps = Pick<Props, "expedienteId" | "etapaTipo" | "etapaRefId" | "setToast"> & { onClose: () => void };

function AgregarAnexoModal({ expedienteId, etapaTipo, etapaRefId, setToast, onClose }: AgregarProps) {
  const [nombre, setNombre] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    const invalido = validarAnexo(nombre, archivo);
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      {
        archivos: { anexo: archivo },
        peticion: (ids) => ({
          url: RECURSO_ENDPOINTS.RECURSO_ANEXOS,
          method: "POST",
          body: {
            expediente_id: expedienteId,
            etapa_tipo: etapaTipo,
            etapa_ref_id: etapaRefId,
            nombre: nombre.trim(),
            documento_anexo_id: ids.anexo,
          },
        }),
      },
      { exito: "Documento agregado", error: "Error al agregar el documento", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Agregar documento anexo"
      icono={<Paperclip size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Agregar"
      onGuardar={guardar}
      onClose={onClose}
      size="md"
    >
      <CampoTexto etiqueta="Nombre" valor={nombre} onChange={setNombre} maxLength={MAX_NOMBRE} requerido />
      <CampoPdf etiqueta="Documento (PDF)" archivo={archivo} onChange={setArchivo} requerido />
    </ModalFormulario>
  );
}

type EditarProps = Pick<Props, "expedienteId" | "setToast"> & { anexo: AnexoEtapa; onClose: () => void };

/**
 * Editar el nombre y, opcionalmente, reemplazar el PDF (C.11). El backend
 * suma un uso al nuevo archivo y descuenta el del anterior.
 */
function EditarAnexoModal({ expedienteId, anexo, setToast, onClose }: EditarProps) {
  const [nombre, setNombre] = useState(anexo.nombre);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    const invalido = validarAnexo(nombre, archivo, { editar: true });
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      {
        archivos: { anexo: archivo },
        peticion: (ids) => ({
          url: RECURSO_ENDPOINTS.RECURSO_ANEXO(anexo.id),
          method: "PUT",
          body: bodyEditarAnexo(expedienteId, nombre, ids.anexo),
        }),
      },
      { exito: "Documento actualizado", error: "Error al actualizar el documento", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Editar documento anexo"
      icono={<Pencil size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Guardar"
      onGuardar={guardar}
      onClose={onClose}
      size="md"
    >
      <CampoTexto etiqueta="Nombre" valor={nombre} onChange={setNombre} maxLength={MAX_NOMBRE} requerido />
      <CampoPdf
        etiqueta="Documento (PDF) — Opcional: solo si desea reemplazar"
        archivo={archivo}
        onChange={setArchivo}
        actualId={anexo.documento_anexo_id}
        disabled={ocupado}
      />
    </ModalFormulario>
  );
}
