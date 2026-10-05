import { useState, type FormEvent } from "react";
import { CheckCircle, FileText, Upload } from "lucide-react";
import { ApiError } from "@shared/lib/api";
import { Modal } from "@shared/ui";
import { useCrearDocumentoMutation } from "../api/documentos";
import type { RevisorDisponible, SetToast, TipoArchivo } from "../types";
import RevisoresSelector from "./RevisoresSelector";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  revisores: RevisorDisponible[];
  setToast: SetToast;
};

const MAX_BYTES = 10 * 1024 * 1024;
const FORM_ID = "crear-documento-form";

/** `/docs/create` aún exige `tipo_archivo`; se deduce de la extensión/MIME. */
function tipoDe(file: File): TipoArchivo | null {
  const nombre = file.name.toLowerCase();
  if (file.type === "application/pdf" || nombre.endsWith(".pdf")) return "pdf";
  if (
    file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    nombre.endsWith(".docx")
  )
    return "docx";
  if (file.type === "application/msword" || nombre.endsWith(".doc")) return "doc";
  return null;
}

export default function CrearDocumentoModal({ isOpen, onClose, revisores, setToast }: Props) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [archivo, setArchivo] = useState<{ file: File; tipo: TipoArchivo } | null>(null);
  const [revisoresIds, setRevisoresIds] = useState<number[]>([]);
  const crear = useCrearDocumentoMutation();

  const error = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const elegirArchivo = (input: HTMLInputElement) => {
    const file = input.files?.[0];
    if (!file) return;
    const tipo = tipoDe(file);
    if (file.size > MAX_BYTES || !tipo) {
      error(!tipo ? "Tipo de archivo no válido. Solo se aceptan PDF, DOC o DOCX" : "El archivo no debe superar los 10MB");
      input.value = "";
      setArchivo(null);
      return;
    }
    setArchivo({ file, tipo });
  };

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (!archivo) return error("Debe seleccionar un archivo válido");
    if (revisoresIds.length === 0) return error("Debe seleccionar al menos un revisor");
    crear.mutate(
      { nombre, descripcion, tipo_archivo: archivo.tipo, revisores_ids: revisoresIds, archivo: archivo.file },
      {
        onSuccess: () => {
          setToast({ id: Date.now(), message: "Documento creado exitosamente", type: "success" });
          onClose();
        },
        onError: (e) =>
          error(e instanceof ApiError ? e.message : "Error de conexión al crear el documento"),
      },
    );
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="2xl"
      icon={<FileText size={20} />}
      title="Crear Nuevo Documento"
      subtitle="Complete la información del documento"
      closeOnEsc={!crear.isPending}
      closeOnBackdrop={!crear.isPending}
      footer={
        <>
          <button type="button" onClick={onClose} className="btn btn-ghost" disabled={crear.isPending}>
            Cancelar
          </button>
          <button type="submit" form={FORM_ID} className="btn btn-success text-white gap-2" disabled={crear.isPending}>
            {crear.isPending ? <span className="loading loading-spinner loading-sm" /> : <Upload size={18} />}
            {crear.isPending ? "Creando..." : "Crear Documento"}
          </button>
        </>
      }
    >
      <form id={FORM_ID} onSubmit={enviar}>
        <fieldset disabled={crear.isPending} className="space-y-5">
          <div>
            <label htmlFor="doc-nombre" className="block text-sm font-medium text-base-content/70 mb-1">
              Nombre del Documento <span className="text-error">*</span>
            </label>
            <input
              id="doc-nombre"
              type="text"
              className="input w-full"
              placeholder="Ej: Contrato de Servicios 2026"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
          </div>

          <div>
            <label htmlFor="doc-descripcion" className="block text-sm font-medium text-base-content/70 mb-1">
              Descripción <span className="text-base-content/60 text-xs">(Opcional)</span>
            </label>
            <textarea
              id="doc-descripcion"
              className="textarea w-full h-20"
              placeholder="Descripción breve del documento..."
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="doc-archivo" className="block text-sm font-medium text-base-content/70 mb-1">
              Archivo <span className="text-error">*</span>
              <span className="text-xs text-base-content/60 ml-2">(PDF, DOC o DOCX - Máx. 10MB)</span>
            </label>
            <input
              id="doc-archivo"
              type="file"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="file-input w-full"
              onChange={(e) => elegirArchivo(e.target)}
              required
            />
            {archivo && (
              <p className="mt-2 flex items-center gap-2 text-sm text-success">
                <CheckCircle size={16} />
                <span className="truncate">{archivo.file.name}</span>
                <span className="badge badge-success badge-sm">{archivo.tipo.toUpperCase()}</span>
              </p>
            )}
          </div>

          <div>
            <p className="block text-sm font-medium text-base-content/70 mb-2">
              Asignar Revisores <span className="text-error">*</span>
            </p>
            <RevisoresSelector revisores={revisores} seleccionados={revisoresIds} onChange={setRevisoresIds} />
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
