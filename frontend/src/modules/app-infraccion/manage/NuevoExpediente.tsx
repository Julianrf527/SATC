import { useRef, useState, type FormEvent } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import { Campo } from "@shared/ui/form/Campo";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import {
  CampoTexto,
  NuevoExpedienteLayout,
  RADICADO_PATTERN,
  RADICADO_TITLE,
  UbicacionFields,
  useUbicacion,
  type SetToast,
} from "@features/expedientes";
import QuejosoSelectorModal from "../common/QuejosoSelectorModal";
import QuejososField from "./nuevo-expediente/QuejososField";
import RecursosTiposField from "./nuevo-expediente/RecursosTiposField";
import RadicadosAsociadosField from "./nuevo-expediente/RadicadosAsociadosField";
import type { Expediente, Quejoso, TipoAfectacion } from "../types";

type NuevoExpedienteProps = {
  userId: number;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList: (quejosos: Quejoso[]) => void;
  setToast: SetToast;
  onCancel: () => void;
  agregarExpediente: (expediente: Expediente) => void;
};

type NuevoQuejosoPayload = {
  nombre: string | null;
  telefono: string | null;
  correo: string | null;
  anonimo: boolean;
};

const toggle = (lista: number[], id: number) =>
  lista.includes(id) ? lista.filter((x) => x !== id) : [...lista, id];

/**
 * Alta de expediente de infracción. Usa el armazón y la ubicación comunes de
 * `@features/expedientes`; quejosos, recursos+tipos de afectación, radicados
 * asociados y descripción son propios de este flujo.
 */
export default function NuevoExpediente({
  userId,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  setToast,
  onCancel,
  agregarExpediente,
}: NuevoExpedienteProps) {
  const ubicacion = useUbicacion(municipioList);
  const [fechaRadicado, setFechaRadicado] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>([]);
  const [tiposSeleccionados, setTiposSeleccionados] = useState<number[]>([]);
  const [expandedRecursos, setExpandedRecursos] = useState<number[]>([]);
  const [quejosoSeleccionado, setQuejosoSeleccionado] = useState<number[]>([]);
  const [showQuejosoModal, setShowQuejosoModal] = useState(false);
  const [radicadosAsociados, setRadicadosAsociados] = useState<string[]>([""]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const resetForm = () => {
    formRef.current?.reset();
    ubicacion.reset();
    setFechaRadicado("");
    setRecursosSeleccionados([]);
    setTiposSeleccionados([]);
    setExpandedRecursos([]);
    setQuejosoSeleccionado([]);
    setRadicadosAsociados([""]);
    setErrorMsg("");
  };

  const handleRecursoToggle = (id: number) => {
    const quitando = recursosSeleccionados.includes(id);
    setRecursosSeleccionados(toggle(recursosSeleccionados, id));
    if (quitando) {
      const tiposDelRecurso = tipoAfectacionList.filter((t) => t.recurso_id === id).map((t) => t.id);
      setTiposSeleccionados((prev) => prev.filter((tid) => !tiposDelRecurso.includes(tid)));
      setExpandedRecursos((prev) => prev.filter((r) => r !== id));
    } else {
      setExpandedRecursos((prev) => (prev.includes(id) ? prev : [...prev, id]));
    }
  };

  const handleCreateQuejoso = async (payload: NuevoQuejosoPayload) => {
    const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_CREATE_COMPLAINER, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok || !res.data) {
      setToast({
        id: Date.now(),
        message: res.detail || "No se pudo crear el quejoso",
        type: "error",
      });
      return null;
    }
    const nuevoQuejoso = res.data as Quejoso;
    setQuejosoList([...quejosoList, nuevoQuejoso]);
    return nuevoQuejoso;
  };

  const validar = (): string | null => {
    if (!fechaRadicado) return "Seleccione la fecha de radicado";
    if (!ubicacion.municipioId) return "Seleccione un municipio";
    if (!ubicacion.veredaId) return "Seleccione una vereda";
    if (recursosSeleccionados.length === 0) return "Seleccione al menos un recurso afectado";
    if (tiposSeleccionados.length === 0) return "Seleccione al menos un tipo de afectación";
    if (quejosoSeleccionado.length === 0) return "Seleccione al menos un quejoso";
    return null;
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const error = validar();
    if (error) {
      setErrorMsg(error);
      return;
    }
    setErrorMsg("");

    const payload = {
      radicado: formData.get("radicado"),
      fecha_radicado: fechaRadicado,
      direccion: formData.get("direccion"),
      descripcion: formData.get("descripcion"),
      vereda_id: ubicacion.veredaId,
      abogado_responsable_id: userId,
      recursos_ids: recursosSeleccionados,
      tipos_afectacion_ids: tiposSeleccionados,
      quejosos_ids: quejosoSeleccionado,
      radicados_asociados: radicadosAsociados.map((r) => r.trim()).filter((r) => r.length > 0),
    };

    setIsSubmitting(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_ADD, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setErrorMsg(res.detail || "Error al registrar el expediente");
        return;
      }
      // Igual que en sancionatorio: sin id no se agrega una tarjeta inválida.
      const expedienteId = res.expediente_id ?? res.data?.expediente_id;
      if (!expedienteId) {
        setErrorMsg("Error al registrar el expediente");
        return;
      }
      setToast({ id: Date.now(), message: "Expediente registrado", type: "success" });

      const municipio = ubicacion.municipio;
      agregarExpediente({
        id: expedienteId,
        radicado: String(payload.radicado ?? ""),
        fecha_radicado: fechaRadicado,
        municipio: municipio
          ? { id: municipio.id, nombre: municipio.nombre }
          : { id: 0, nombre: "Desconocido" },
        fecha_creacion: new Date().toISOString(),
        involucrados: [],
        archivado: false,
      });

      resetForm();
      onCancel();
    } catch {
      setErrorMsg("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelClick = () => {
    resetForm();
    onCancel();
  };

  // Ubicación de los mensajes de error (se conserva la de la versión anterior).
  const errorQuejosos = errorMsg && quejosoSeleccionado.length === 0 ? errorMsg : null;
  const errorRecursos =
    errorMsg &&
    (recursosSeleccionados.length === 0 ||
      (tiposSeleccionados.length === 0 && recursosSeleccionados.length > 0))
      ? errorMsg
      : null;
  const errorGeneral =
    errorMsg &&
    recursosSeleccionados.length > 0 &&
    tiposSeleccionados.length > 0 &&
    quejosoSeleccionado.length > 0
      ? errorMsg
      : null;

  return (
    <NuevoExpedienteLayout
      formId="new-file-form"
      formRef={formRef}
      onSubmit={handleSubmit}
      onCancelar={handleCancelClick}
      isSubmitting={isSubmitting}
      errorGeneral={errorGeneral}
      extra={
        <QuejosoSelectorModal
          isOpen={showQuejosoModal}
          title="Quejosos"
          quejosoList={quejosoList}
          selectedIds={quejosoSeleccionado}
          onSelectionChange={setQuejosoSeleccionado}
          onCreateQuejoso={handleCreateQuejoso}
          setToast={setToast}
          onClose={() => setShowQuejosoModal(false)}
          isDisabled={isSubmitting}
        />
      }
    >
      <CampoTexto
        etiqueta="Radicado *"
        name="radicado"
        placeholder="Ingrese el radicado"
        required
        disabled={isSubmitting}
        maxLength={11}
        pattern={RADICADO_PATTERN}
        title={RADICADO_TITLE}
      />

      <Campo etiqueta="Fecha de Radicado *">
        <CustomDateInput
          value={fechaRadicado}
          onChange={setFechaRadicado}
          max={new Date().toISOString().split("T")[0]}
          disabled={isSubmitting}
        />
      </Campo>

      <QuejososField
        quejosoList={quejosoList}
        seleccionados={quejosoSeleccionado}
        onAbrirSelector={() => setShowQuejosoModal(true)}
        disabled={isSubmitting}
        error={errorQuejosos}
      />

      <UbicacionFields municipioList={municipioList} ubicacion={ubicacion} disabled={isSubmitting} />

      <RecursosTiposField
        recursoAfectadoList={recursoAfectadoList}
        tipoAfectacionList={tipoAfectacionList}
        recursosSeleccionados={recursosSeleccionados}
        tiposSeleccionados={tiposSeleccionados}
        expandidos={expandedRecursos}
        onToggleRecurso={handleRecursoToggle}
        onToggleTipo={(id) => setTiposSeleccionados((prev) => toggle(prev, id))}
        onToggleExpandir={(id) => setExpandedRecursos((prev) => toggle(prev, id))}
        disabled={isSubmitting}
        error={errorRecursos}
      />

      <RadicadosAsociadosField
        radicados={radicadosAsociados}
        onChange={setRadicadosAsociados}
        disabled={isSubmitting}
      />

      <Campo etiqueta="Descripción *" ayuda="Máximo 400 caracteres">
        <textarea
          name="descripcion"
          placeholder="Describa el expediente"
          className="textarea w-full h-24 resize-none"
          required
          disabled={isSubmitting}
          maxLength={400}
        />
      </Campo>
    </NuevoExpedienteLayout>
  );
}
