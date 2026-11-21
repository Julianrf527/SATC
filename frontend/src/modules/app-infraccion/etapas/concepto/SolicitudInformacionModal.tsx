import { useState } from "react";
import { FileInput, Pencil } from "lucide-react";
import { generateDocumentFileName, uploadFileToDocuments } from "@shared/lib/fileUpload";
import { useGuardarSolicitudInformacionMutation } from "../../api/etapas";
import { detalleError } from "../../api/errors";
import type { SolicitudInformacion } from "../../types";
import { CampoFecha, CampoPdf, CampoTexto, Seccion } from "../campos/Campos";
import ModalFormulario from "../ModalFormulario";

/** Radicado de salida de la solicitud: 4 dígitos + EE + 4 o 5 dígitos (ej: 2024EE0001). */
const RADICADO_EE = /^\d{4}EE\d{4,5}$/;
/** Radicado de entrada de la respuesta: 4 dígitos + ER + 4 o 5 dígitos (ej: 2024ER0001). */
const RADICADO_ER = /^\d{4}ER\d{4,5}$/;

const esPdf = (f: File | null) => !f || /\.pdf$/i.test(f.name);

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  /** null = agregar; con valor = editar. */
  solicitud: SolicitudInformacion | null;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onClose: () => void;
};

/**
 * Agregar / editar la solicitud de información de la etapa 3 en modal (como
 * `RadicadoModal` de recurso), en dos secciones:
 * - Solicitud: radicado EE, fecha y PDF (obligatorios; al editar el PDF
 *   vacío mantiene el actual).
 * - Respuesta del usuario (opcional): radicado ER, fecha y PDF. Si se llena
 *   uno de los tres, los tres son obligatorios. Al editar, el PDF vacío
 *   mantiene el actual; "Quitar respuesta" borra los tres datos.
 */
export default function SolicitudInformacionModal({ etapaConceptoId, expedienteId, solicitud, setToast, onClose }: Props) {
  const [radicado, setRadicado] = useState(solicitud?.radicado ?? "");
  const [fechaRadicado, setFechaRadicado] = useState(solicitud?.fecha_radicado ?? "");
  const [archivo, setArchivo] = useState<File | null>(null);

  const [radicadoResp, setRadicadoResp] = useState(solicitud?.radicado_respuesta ?? "");
  const [fechaResp, setFechaResp] = useState(solicitud?.fecha_radicado_respuesta ?? "");
  const [archivoResp, setArchivoResp] = useState<File | null>(null);
  /** PDF de respuesta ya guardado (se descarta con "Quitar respuesta"). */
  const [respuestaActualId, setRespuestaActualId] = useState<number | null>(solicitud?.archivo_respuesta_id ?? null);

  /** Cambia para vaciar el selector de archivo al quitar la respuesta. */
  const [resetResp, setResetResp] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const guardarSolicitud = useGuardarSolicitudInformacionMutation(expedienteId, etapaConceptoId);
  const ocupado = subiendo || guardarSolicitud.isPending;

  const radicadoInvalido = radicado !== "" && !RADICADO_EE.test(radicado);
  const radicadoRespInvalido = radicadoResp !== "" && !RADICADO_ER.test(radicadoResp);
  const conRespuesta = radicadoResp !== "" || fechaResp !== "" || !!archivoResp || !!respuestaActualId;
  const limpiar = () => setError(null);

  const quitarRespuesta = () => {
    setRadicadoResp("");
    setFechaResp("");
    setArchivoResp(null);
    setRespuestaActualId(null);
    setResetResp((n) => n + 1);
    setError(null);
  };

  const validar = (): string | null => {
    if (!RADICADO_EE.test(radicado.trim())) return "El radicado de la solicitud no cumple el formato (ej: 2024EE0001)";
    if (!fechaRadicado) return "Seleccione la fecha de radicado de la solicitud";
    if (!archivo && !solicitud?.archivo_solicitud_id) return "Adjunte el documento de la solicitud (PDF)";
    if (!esPdf(archivo)) return "El documento de la solicitud debe ser PDF";
    if (conRespuesta) {
      if (!radicadoResp || !fechaResp || (!archivoResp && !respuestaActualId)) {
        return "Si registra la respuesta, indique el radicado, la fecha de radicado y el documento de respuesta";
      }
      if (!RADICADO_ER.test(radicadoResp.trim())) return "El radicado de la respuesta no cumple el formato (ej: 2024ER0001)";
      if (!esPdf(archivoResp)) return "El documento de respuesta debe ser PDF";
    }
    return null;
  };

  const guardar = async () => {
    // Validar ANTES de subir los PDF (si no, quedan huérfanos en app-docs).
    const invalido = validar();
    if (invalido) return setError(invalido);
    setError(null);
    setSubiendo(true);
    try {
      let archivoId = solicitud?.archivo_solicitud_id;
      if (archivo) {
        archivoId = await uploadFileToDocuments(archivo, generateDocumentFileName("SOLICITUD_INFO", radicado, fechaRadicado));
      }
      let respuestaId = conRespuesta ? respuestaActualId : null;
      if (conRespuesta && archivoResp) {
        respuestaId = await uploadFileToDocuments(
          archivoResp,
          generateDocumentFileName("RESPUESTA_SOLICITUD_INFO", radicadoResp, fechaResp),
        );
      }
      await guardarSolicitud.mutateAsync({
        solicitudId: solicitud?.id ?? null,
        payload: {
          radicado: radicado.trim(),
          fecha_radicado: fechaRadicado,
          archivo_solicitud_id: archivoId as number,
          radicado_respuesta: conRespuesta ? radicadoResp.trim() : null,
          fecha_radicado_respuesta: conRespuesta ? fechaResp : null,
          archivo_respuesta_id: respuestaId,
        },
      });
      setToast({ id: Date.now(), message: solicitud ? "Solicitud actualizada" : "Solicitud registrada", type: "success" });
      onClose();
    } catch (err) {
      setError(detalleError(err) ?? (err instanceof Error && err.message ? err.message : "Error al guardar la solicitud"));
    } finally {
      setSubiendo(false);
    }
  };

  return (
    <ModalFormulario
      titulo={solicitud ? "Editar solicitud de información" : "Agregar solicitud de información"}
      icono={solicitud ? <Pencil size={20} /> : <FileInput size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar={solicitud ? "Guardar cambios" : "Registrar"}
      onGuardar={() => void guardar()}
      onClose={onClose}
      size="2xl"
    >
      <Seccion titulo="Solicitud de información">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CampoTexto
            etiqueta="Radicado"
            valor={radicado}
            onChange={(v) => {
              setRadicado(v.toUpperCase());
              limpiar();
            }}
            maxLength={11}
            placeholder="2024EE0001"
            ayuda="4 dígitos + EE + 4 o 5 dígitos"
            error={radicadoInvalido ? "Formato inválido (ej: 2024EE0001)" : null}
            requerido
          />
          <CampoFecha etiqueta="Fecha de radicado" valor={fechaRadicado} onChange={setFechaRadicado} requerido />
        </div>
        <CampoPdf
          etiqueta="Solicitud de información (PDF)"
          archivo={archivo}
          onChange={(a) => {
            setArchivo(a);
            limpiar();
          }}
          requerido={!solicitud}
          actualId={solicitud?.archivo_solicitud_id ?? null}
        />
      </Seccion>

      <Seccion titulo="Respuesta del usuario (opcional)">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="text-xs text-base-content/60">
            Si diligencia uno de estos datos, los tres son obligatorios.
          </p>
          {conRespuesta && (
            <button type="button" className="btn btn-ghost btn-xs text-error" onClick={quitarRespuesta}>
              Quitar respuesta
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CampoTexto
            etiqueta="Radicado"
            valor={radicadoResp}
            onChange={(v) => {
              setRadicadoResp(v.toUpperCase());
              limpiar();
            }}
            maxLength={11}
            placeholder="2024ER0001"
            ayuda="4 dígitos + ER + 4 o 5 dígitos"
            error={radicadoRespInvalido ? "Formato inválido (ej: 2024ER0001)" : null}
            requerido={conRespuesta}
          />
          <CampoFecha
            etiqueta="Fecha de radicado"
            valor={fechaResp}
            onChange={(v) => {
              setFechaResp(v);
              limpiar();
            }}
            requerido={conRespuesta}
          />
        </div>
        <CampoPdf
          key={resetResp}
          etiqueta="Documento de respuesta (PDF)"
          archivo={archivoResp}
          onChange={(a) => {
            setArchivoResp(a);
            limpiar();
          }}
          requerido={conRespuesta && !respuestaActualId}
          actualId={respuestaActualId}
        />
      </Seccion>
    </ModalFormulario>
  );
}
