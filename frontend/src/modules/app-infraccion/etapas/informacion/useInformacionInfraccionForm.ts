import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  useActualizarDatosBasicosMutation,
  useCrearQuejosoMutation,
  type NuevoQuejosoPayload,
} from "../../api/expediente";
import { detalleError, esErrorDeConexion } from "../../api/errors";
import type {
  ExpedienteDetalle,
  Quejoso,
  TipoAfectacion,
} from "../../types";
import type { Municipio, ModeloGenerico } from "@shared/types/common";

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

  const actualizarDatosBasicos = useActualizarDatosBasicosMutation(expediente.id);
  const crearQuejoso = useCrearQuejosoMutation();
  const isLoading = actualizarDatosBasicos.isPending;

  // Vuelve a los valores del expediente (al cambiar de expediente o cancelar).
  const resetForm = () => {
    const next = expediente as ExpedienteDetalleExt;
    setRadicado(expediente.radicado || "");
    setFechaRadicado(expediente.fecha_radicado || "");
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setDireccion(expediente.direccion || "");
    setDescripcion(expediente.descripcion || "");
    const ids = getRecursoIds(
      (expediente.recurso_afectado || []) as Array<number | { id?: number; nombre?: string }>,
    );
    setRecursosIds(ids);
    setExpandedRecursos(ids);
    setTiposIds((expediente.tipos_afectacion || []).map((t) => t.id));
    setQuejososIds((expediente.quejosos || []).map((q) => q.id));
    setRadicadosAsociados(
      next.radicados_asociados && next.radicados_asociados.length > 0
        ? next.radicados_asociados
        : [""],
    );
  };

  useEffect(() => {
    resetForm();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al cambiar el expediente
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

  const handleCreateQuejoso = async (payload: NuevoQuejosoPayload): Promise<Quejoso | null> => {
    let nuevoQuejoso: Quejoso | null;
    try {
      nuevoQuejoso = await crearQuejoso.mutateAsync(payload);
    } catch (err) {
      // Sin respuesta HTTP: el modal muestra su propio error de conexión.
      if (esErrorDeConexion(err)) throw err;
      setToast({ id: Date.now(), message: detalleError(err) || "No se pudo crear el quejoso", type: "error" });
      return null;
    }
    if (!nuevoQuejoso) {
      setToast({ id: Date.now(), message: "No se pudo crear el quejoso", type: "error" });
      return null;
    }
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

  const validateForm = (): boolean => {
    if (!RADICADO_REGEX.test(radicado.trim())) {
      setToast({
        id: Date.now(),
        message: "El radicado no cumple el formato requerido",
        type: "error",
      });
      return false;
    }

    if (!fechaRadicado) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar la fecha de radicado",
        type: "error",
      });
      return false;
    }

    if (!municipioId) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un municipio",
        type: "error",
      });
      return false;
    }

    if (!veredaId) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar una vereda",
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

  const handleSubmit = (e: FormEvent) => {
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

    actualizarDatosBasicos.mutate(payload, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Expediente actualizado exitosamente", type: "success" });
        if (onUpdate) onUpdate(updated);
        if (onSaved) onSaved();
      },
      onError: (err) => {
        setToast({
          id: Date.now(),
          message: esErrorDeConexion(err)
            ? "Error de conexion al actualizar el expediente"
            : (detalleError(err) || "No se pudo actualizar el expediente"),
          type: "error",
        });
      },
    });
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
