import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type {
  ExpedienteDetalle,
  Quejoso,
  TipoAfectacion,
} from "../../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../../types/common";

export type ExpedienteDetalleExt = ExpedienteDetalle & {
  radicados_asociados?: string[];
  ultima_etapa?: string | null;
};

export type ToastSetter = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

const RADICADO_REGEX = /^\d{4}(IE|EE|ER)\d{4}$/;

export const getRecursoIds = (
  recursos: Array<number | { id?: number; nombre?: string }> = [],
): number[] =>
  recursos
    .map((recurso) =>
      typeof recurso === "number" ? recurso : (recurso?.id ?? 0),
    )
    .filter((id) => id > 0);

interface UseInformacionInfraccionFormArgs {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
  onUpdate?: (expediente: ExpedienteDetalle) => void;
  setToast: ToastSetter;
  onSaved?: () => void;
  onCancelled?: () => void;
}

export function useInformacionInfraccionForm({
  expediente,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  onUpdate,
  setToast,
  onSaved,
  onCancelled,
}: UseInformacionInfraccionFormArgs) {
  const [isLoading, setIsLoading] = useState(false);

  const [radicado, setRadicado] = useState(expediente.radicado || "");
  const [fechaRadicado, setFechaRadicado] = useState(
    expediente.fecha_radicado || "",
  );
  const [municipioId, setMunicipioId] = useState(expediente.municipio?.id || 0);
  const [veredaId, setVeredaId] = useState(expediente.vereda?.id || 0);
  const [direccion, setDireccion] = useState(expediente.direccion || "");
  const [descripcion, setDescripcion] = useState(expediente.descripcion || "");
  const [recursosIds, setRecursosIds] = useState<number[]>(
    getRecursoIds(
      (expediente.recurso_afectado || []) as Array<
        number | { id?: number; nombre?: string }
      >,
    ),
  );
  const [tiposIds, setTiposIds] = useState<number[]>(
    (expediente.tipos_afectacion || []).map((t) => t.id),
  );
  const [expandedRecursos, setExpandedRecursos] = useState<number[]>(() =>
    getRecursoIds(
      (expediente.recurso_afectado || []) as Array<number | { id?: number; nombre?: string }>,
    ),
  );
  const [quejososIds, setQuejososIds] = useState<number[]>(
    (expediente.quejosos || []).map((q) => q.id),
  );
  const [radicadosAsociados, setRadicadosAsociados] = useState<string[]>(() => {
    const ext = expediente as ExpedienteDetalleExt;
    return ext.radicados_asociados && ext.radicados_asociados.length > 0
      ? ext.radicados_asociados
      : [""];
  });

  useEffect(() => {
    const next = expediente as ExpedienteDetalleExt;
    setRadicado(expediente.radicado || "");
    setFechaRadicado(expediente.fecha_radicado || "");
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setDireccion(expediente.direccion || "");
    setDescripcion(expediente.descripcion || "");
    const nextRecursosIds = getRecursoIds(
      (expediente.recurso_afectado || []) as Array<number | { id?: number; nombre?: string }>,
    );
    setRecursosIds(nextRecursosIds);
    setExpandedRecursos(nextRecursosIds);
    setTiposIds((expediente.tipos_afectacion || []).map((t) => t.id));
    setQuejososIds((expediente.quejosos || []).map((q) => q.id));
    setRadicadosAsociados(
      next.radicados_asociados && next.radicados_asociados.length > 0
        ? next.radicados_asociados
        : [""],
    );
  }, [expediente]);

  const veredaList = useMemo(() => {
    const municipio = municipioList.find((m) => m.id === municipioId);
    return municipio?.veredas || [];
  }, [municipioList, municipioId]);

  const handleResourceToggle = (id: number) => {
    setRecursosIds((prev) => {
      const next = prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id];
      if (!next.includes(id)) {
        const tiposDeEsteRecurso = tipoAfectacionList
          .filter((t) => t.recurso_id === id)
          .map((t) => t.id);
        setTiposIds((prevTipos) =>
          prevTipos.filter((tid) => !tiposDeEsteRecurso.includes(tid))
        );
        setExpandedRecursos((prev) => prev.filter((r) => r !== id));
      } else {
        setExpandedRecursos((prev) => prev.includes(id) ? prev : [...prev, id]);
      }
      return next;
    });
  };

  const handleToggleExpand = (id: number) => {
    setExpandedRecursos((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const handleTipoToggle = (id: number) => {
    setTiposIds((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    );
  };

  const handleCreateQuejoso = async (payload: {
    nombre: string | null;
    telefono: string | null;
    correo: string | null;
    anonimo: boolean;
  }) => {
    const res = await apiCall(
      API_CONFIG.ENDPOINTS.INFRACTION_CREATE_COMPLAINER,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );

    if (!res.ok || !res.data) {
      setToast({
        id: Date.now(),
        message: res.detail || "No se pudo crear el quejoso",
        type: "error",
      });
      return null;
    }

    const nuevoQuejoso = res.data as Quejoso;
    if (setQuejosoList) {
      setQuejosoList([...quejosoList, nuevoQuejoso]);
    }
    return nuevoQuejoso;
  };

  const handleAddRadicado = () => {
    setRadicadosAsociados((prev) => [...prev, ""]);
  };

  const handleRemoveRadicado = (index: number) => {
    setRadicadosAsociados((prev) =>
      prev.length === 1 ? [""] : prev.filter((_, i) => i !== index),
    );
  };

  const handleChangeRadicadoAsociado = (index: number, value: string) => {
    setRadicadosAsociados((prev) =>
      prev.map((item, i) => (i === index ? value.toUpperCase() : item)),
    );
  };

  const resetForm = () => {
    const next = expediente as ExpedienteDetalleExt;
    setRadicado(expediente.radicado || "");
    setFechaRadicado(expediente.fecha_radicado || "");
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setDireccion(expediente.direccion || "");
    setDescripcion(expediente.descripcion || "");
    const resetRecursosIds = getRecursoIds(
      (expediente.recurso_afectado || []) as Array<number | { id?: number; nombre?: string }>,
    );
    setRecursosIds(resetRecursosIds);
    setExpandedRecursos(resetRecursosIds);
    setTiposIds((expediente.tipos_afectacion || []).map((t) => t.id));
    setQuejososIds((expediente.quejosos || []).map((q) => q.id));
    setRadicadosAsociados(
      next.radicados_asociados && next.radicados_asociados.length > 0
        ? next.radicados_asociados
        : [""],
    );
  };

  const validateForm = (): boolean => {
    if (!RADICADO_REGEX.test(radicado.trim())) {
      setToast({
        id: Date.now(),
        message: "El radicado no cumple el formato requerido",
        type: "error",
      });
      return false;
    }

    if (quejososIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un quejoso",
        type: "error",
      });
      return false;
    }

    if (recursosIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un recurso afectado",
        type: "error",
      });
      return false;
    }

    if (tiposIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un tipo de afectación",
        type: "error",
      });
      return false;
    }

    for (const item of radicadosAsociados) {
      const value = item.trim();
      if (!value) continue;
      if (!RADICADO_REGEX.test(value)) {
        setToast({
          id: Date.now(),
          message: "Todos los radicados asociados deben tener formato valido",
          type: "error",
        });
        return false;
      }
    }

    return true;
  };

  const buildUpdatedExpediente = (): ExpedienteDetalleExt => {
    const selectedMunicipio = municipioList.find((m) => m.id === municipioId);
    const selectedVereda = veredaList.find((v) => v.id === veredaId);
    const selectedTipos = tipoAfectacionList.filter((t) => tiposIds.includes(t.id));

    return {
      ...expediente,
      radicado: radicado.trim(),
      fecha_radicado: fechaRadicado,
      direccion: direccion.trim(),
      descripcion: descripcion.trim(),
      municipio: {
        id: municipioId,
        nombre: selectedMunicipio?.nombre || expediente.municipio.nombre,
      },
      vereda: {
        id: veredaId,
        nombre: selectedVereda?.nombre || expediente.vereda?.nombre || "",
      },
      tipos_afectacion: selectedTipos,
      recurso_afectado: recursoAfectadoList.filter((r) =>
        recursosIds.includes(r.id),
      ),
      quejosos: quejosoList.filter((q) => quejososIds.includes(q.id)),
      radicados_asociados: radicadosAsociados
        .map((r) => r.trim())
        .filter((r) => r.length > 0),
    };
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    const updated = buildUpdatedExpediente();

    const payload = {
      radicado: updated.radicado,
      fecha_radicado: updated.fecha_radicado,
      vereda_id: updated.vereda.id,
      direccion: updated.direccion,
      descripcion: updated.descripcion,
      tipos_afectacion_ids: tiposIds,
      quejosos_ids: quejososIds,
      recursos_ids: recursosIds,
      radicados_asociados: updated.radicados_asociados || [],
    };

    setIsLoading(true);
    try {
      const response = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_BASIC_DATA(expediente.id),
        {
          method: "PUT",
          body: JSON.stringify(payload),
        },
      );

      if (!response.ok) {
        setToast({
          id: Date.now(),
          message: response.detail || "No se pudo actualizar el expediente",
          type: "error",
        });
        return;
      }

      setToast({
        id: Date.now(),
        message: "Expediente actualizado exitosamente",
        type: "success",
      });

      if (onUpdate) onUpdate(updated);
      if (onSaved) onSaved();
    } catch {
      setToast({
        id: Date.now(),
        message: "Error de conexion al actualizar el expediente",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    if (onCancelled) onCancelled();
  };

  return {
    isLoading,
    radicado,
    setRadicado,
    fechaRadicado,
    setFechaRadicado,
    municipioId,
    setMunicipioId,
    veredaId,
    setVeredaId,
    direccion,
    setDireccion,
    descripcion,
    setDescripcion,
    recursosIds,
    tiposIds,
    expandedRecursos,
    quejososIds,
    setQuejososIds,
    radicadosAsociados,
    veredaList,
    handleResourceToggle,
    handleToggleExpand,
    handleTipoToggle,
    handleCreateQuejoso,
    handleAddRadicado,
    handleRemoveRadicado,
    handleChangeRadicadoAsociado,
    handleSubmit,
    handleCancel,
  };
}

export type InformacionInfraccionFormState = ReturnType<
  typeof useInformacionInfraccionForm
>;
