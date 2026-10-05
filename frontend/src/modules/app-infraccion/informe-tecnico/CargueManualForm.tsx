import { useState } from "react";
import { getErrorMessage } from "@shared/lib/api";
import { uploadFileToDocuments, validateFile } from "@shared/lib/fileUpload";
import { openDocumentById } from "@shared/lib/documentViewer";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import CustomSelect from "@shared/ui/form/CustomSelect";
import { detalleError } from "../api/errors";
import { useCargueManualMutation, useDisponiblesQuery } from "../api/informes";
import type { InformeTecnico } from "../types";

type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

type Props = {
  informe: InformeTecnico;
  setToast: SetToast;
  /** Al guardar o cancelar la edición. */
  onTerminar: () => void;
  editando: boolean;
};

const hoy = () => new Date().toISOString().split("T")[0];

/** Cargue directo (modo MANUAL) de un informe ya aceptado fuera del sistema. */
export default function CargueManualForm({ informe, setToast, onTerminar, editando }: Props) {
  const disponibles = useDisponiblesQuery(true);
  const cargue = useCargueManualMutation(informe.id);

  const [archivo, setArchivo] = useState<File | null>(null);
  const [fechaRecibido, setFechaRecibido] = useState(informe.fecha_recibido_informe ?? "");
  const [fechaAceptacion, setFechaAceptacion] = useState(informe.fecha_aceptacion_informe ?? "");
  const [fechaProgramacion, setFechaProgramacion] = useState(informe.fecha_programacion_visita ?? "");
  const [profesionalId, setProfesionalId] = useState<number | "">(informe.profesional_asignado_id ?? "");
  const [revisorId, setRevisorId] = useState<number | "">(informe.revisor_asignado_id ?? "");
  const [subiendo, setSubiendo] = useState(false);
  const ocupado = subiendo || cargue.isPending;

  const error = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const guardar = async () => {
    if (!archivo && !informe.documento_informe_id) return error("Selecciona un archivo");
    if (archivo) {
      const validacion = validateFile(archivo, ["application/pdf"]);
      if (!validacion.isValid) return error(validacion.error!);
    }
    if (!fechaRecibido || !fechaAceptacion) return error("Completa la fecha de recibido y de aceptación");
    if (fechaAceptacion < fechaRecibido) {
      return error("La fecha de aceptación no puede ser anterior a la fecha de recibido");
    }
    if (profesionalId && profesionalId === revisorId) {
      return error("El profesional y el revisor deben ser personas distintas");
    }

    let fileId = informe.documento_informe_id!;
    if (archivo) {
      setSubiendo(true);
      try {
        fileId = await uploadFileToDocuments(archivo, archivo.name);
      } catch (e) {
        setSubiendo(false);
        return error(getErrorMessage(e, "Error al subir el archivo"));
      }
      setSubiendo(false);
    }

    cargue.mutate(
      {
        file_id: fileId,
        fecha_recibido: fechaRecibido,
        fecha_aceptacion: fechaAceptacion,
        ...(fechaProgramacion ? { fecha_programacion_visita: fechaProgramacion } : {}),
        ...(profesionalId ? { profesional_id: profesionalId } : {}),
        ...(revisorId ? { revisor_id: revisorId } : {}),
      },
      {
        onSuccess: () => {
          setToast({
            id: Date.now(),
            message: informe.documento_informe_id
              ? "Informe actualizado correctamente"
              : "Informe cargado y aceptado correctamente",
            type: "success",
          });
          onTerminar();
        },
        onError: (e) => error(detalleError(e) ?? "Error al cargar el informe"),
      },
    );
  };

  const profesionales = disponibles.data?.profesionales ?? [];
  const revisores = disponibles.data?.revisores ?? [];

  return (
    <fieldset disabled={ocupado} className="space-y-4">
      <p className="text-sm text-base-content/60">
        Cargue directo de un informe ya aceptado previamente fuera del sistema (expedientes históricos). No pasa
        por asignación ni revisión.
      </p>

      <div className="flex flex-col">
        <label htmlFor={`cargue-archivo-${informe.id}`} className="label py-1">
          <span className="text-sm text-base-content font-medium">
            Archivo PDF {!informe.documento_informe_id && <span className="text-error">*</span>}
            {informe.documento_informe_id && (
              <span className="text-base-content/60 text-xs font-normal ml-1">
                (Opcional — deja vacío para mantener el actual)
              </span>
            )}
          </span>
        </label>
        {informe.documento_informe_id && (
          <button
            type="button"
            onClick={() => openDocumentById(informe.documento_informe_id!)}
            className="btn btn-ghost btn-xs gap-1 text-success w-fit mb-1"
          >
            Ver archivo actual
          </button>
        )}
        <input
          id={`cargue-archivo-${informe.id}`}
          type="file"
          accept=".pdf,application/pdf"
          className="file-input w-full"
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Fecha de Recibido <span className="text-error">*</span>
            </span>
          </span>
          <CustomDateInput value={fechaRecibido} onChange={setFechaRecibido} max={hoy()} disabled={ocupado} />
        </div>
        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Fecha de Aceptación <span className="text-error">*</span>
            </span>
          </span>
          <CustomDateInput value={fechaAceptacion} onChange={setFechaAceptacion} max={hoy()} disabled={ocupado} />
        </div>
        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Fecha de Programación de Visita
              <span className="text-base-content/60 text-xs font-normal ml-1">(Opcional)</span>
            </span>
          </span>
          <CustomDateInput value={fechaProgramacion} onChange={setFechaProgramacion} max={hoy()} disabled={ocupado} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Profesional que cargó
              <span className="text-base-content/60 text-xs font-normal ml-1">(Opcional)</span>
            </span>
          </span>
          <CustomSelect
            value={profesionalId === "" ? 0 : profesionalId}
            onChange={(v) => setProfesionalId(v === 0 ? "" : v)}
            placeholder="Sin asignar"
            disabled={ocupado}
            options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
          />
        </div>
        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">
              Revisor
              <span className="text-base-content/60 text-xs font-normal ml-1">(Opcional)</span>
            </span>
          </span>
          <CustomSelect
            value={revisorId === "" ? 0 : revisorId}
            onChange={(v) => setRevisorId(v === 0 ? "" : v)}
            placeholder="Sin asignar"
            disabled={ocupado}
            options={revisores.map((r) => ({ value: r.id, label: r.nombre }))}
          />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        {editando && (
          <button type="button" className="btn btn-ghost" onClick={onTerminar}>
            Cancelar
          </button>
        )}
        <button type="button" className="btn btn-success text-white gap-2" onClick={guardar}>
          {ocupado ? (
            <>
              <span className="loading loading-spinner loading-xs" />
              Guardando...
            </>
          ) : informe.documento_informe_id ? (
            "Guardar cambios"
          ) : (
            "Cargar informe"
          )}
        </button>
      </div>
    </fieldset>
  );
}
