import { useEffect, useRef, useState } from "react";
import { uploadFileToDocuments, generateDocumentFileName } from "@shared/lib/fileUpload";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import type { Ejecucion, EjecucionDatos, SetToast, TipoArchivoEjecucion } from "../../types";

type Params = {
  data: Ejecucion | undefined;
  expedienteId: number;
  setToast: SetToast;
  /** Tras guardar con éxito. */
  onGuardado: () => void;
};

const MAX_FILE_SIZE = 10 * 1024 * 1024;

type CampoDocumento =
  | "documento_cobro_id"
  | "documento_ruia_id"
  | "documento_memorando_id"
  | "documento_acto_administrativo_id";

/** Prefijo del nombre de archivo y campo del body por cada documento. */
const DOCS: Record<TipoArchivoEjecucion, { prefijo: string; campo: CampoDocumento }> = {
  cobro_coactivo: { prefijo: "COBRO_COACTIVO", campo: "documento_cobro_id" },
  ruia: { prefijo: "RUIA", campo: "documento_ruia_id" },
  memorando: { prefijo: "MEMORANDO", campo: "documento_memorando_id" },
  auto: { prefijo: "AUTO", campo: "documento_acto_administrativo_id" },
};

const TIPOS: TipoArchivoEjecucion[] = ["cobro_coactivo", "ruia", "memorando", "auto"];

/** Estado y envío del formulario de ejecución de la sanción. */
export function useEjecucionForm({ data, expedienteId, setToast, onGuardado }: Params) {
  const [isLoading, setIsLoading] = useState(false);
  const [autoTipo, setAutoTipo] = useState<string>("AUTO");
  const [autoNumero, setAutoNumero] = useState<string>("");
  const [fechaAuto, setFechaAuto] = useState<string>(data?.fecha_auto || "");
  const [archivos, setArchivos] = useState<Record<TipoArchivoEjecucion, File | null>>({
    cobro_coactivo: null,
    ruia: null,
    memorando: null,
    auto: null,
  });
  const inputRefs = {
    cobro_coactivo: useRef<HTMLInputElement>(null),
    ruia: useRef<HTMLInputElement>(null),
    memorando: useRef<HTMLInputElement>(null),
    auto: useRef<HTMLInputElement>(null),
  };

  useEffect(() => {
    const match = data?.tipo_acto?.match(/^(AUTO|RES)(.*)$/);
    setAutoTipo(match ? match[1] : "AUTO");
    setAutoNumero(match ? match[2] : data?.tipo_acto || "");
    setFechaAuto(data?.fecha_auto || "");
  }, [data?.tipo_acto, data?.fecha_auto]);

  const toastError = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>, tipo: TipoArchivoEjecucion) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") return toastError("Solo se permiten archivos PDF");
    if (file.size > MAX_FILE_SIZE) return toastError("El archivo no debe superar los 10MB");
    setArchivos((prev) => ({ ...prev, [tipo]: file }));
  };

  const onAutoNumeroChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (/^\d{0,4}$/.test(e.target.value)) setAutoNumero(e.target.value);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const marcado = (name: string) =>
      (form.elements.namedItem(name) as HTMLInputElement | null)?.checked || false;
    const cobro = marcado("cobro_coactivo");
    const disposicion = marcado("disposicion");
    const ruia = marcado("ruia");
    const memorando = marcado("memorando");

    // Validaciones: casilla marcada ⇒ documento (nuevo o existente)
    const error =
      autoNumero.length !== 4
        ? "El numerado debe tener exactamente 4 dígitos"
        : cobro && !archivos.cobro_coactivo && !data?.documento_cobro_id
          ? "Debe adjuntar el documento de Cobro Coactivo"
          : ruia && !archivos.ruia && !data?.documento_ruia_id
            ? "Debe adjuntar el documento RUIA"
            : memorando && !archivos.memorando && !data?.documento_memorando_id
              ? "Debe adjuntar el documento de Memorando"
              : !fechaAuto
                ? "La fecha del auto es requerida"
                : !archivos.auto && !data?.documento_acto_administrativo_id
                  ? "Debe adjuntar el documento del Acto Administrativo"
                  : null;
    if (error) return toastError(error);

    setIsLoading(true);
    try {
      const autoAdminCompleto = autoTipo + autoNumero;

      // Paso 1: subir en paralelo los archivos nuevos a app-docs
      const subidos = await Promise.all(
        TIPOS.filter((t) => archivos[t]).map(async (t) => ({
          tipo: t,
          fileId: await uploadFileToDocuments(
            archivos[t] as File,
            generateDocumentFileName(DOCS[t].prefijo, autoAdminCompleto, fechaAuto),
          ),
        })),
      );

      // Paso 2: body. Documento de cada tipo: el recién subido o el que ya estaba.
      const subidoDe = (t: TipoArchivoEjecucion) => subidos.find((x) => x.tipo === t)?.fileId;
      const documento = (t: TipoArchivoEjecucion) => subidoDe(t) ?? data?.[DOCS[t].campo] ?? null;
      const requestBody: EjecucionDatos = {
        tipo_acto: autoAdminCompleto,
        fecha_auto: fechaAuto,
        documento_acto_administrativo_id: documento("auto"),
        cobro_coactivo: cobro,
        documento_cobro_id: documento("cobro_coactivo"),
        disposicion,
        ruia,
        documento_ruia_id: documento("ruia"),
        memorando,
        documento_memorando_id: documento("memorando"),
      };

      // La etapa ya existe ("Crear Etapa" hace el POST): los datos siempre se guardan con PUT.
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_EXECUTION_UPDATE(expedienteId), {
        method: "PUT",
        body: JSON.stringify(requestBody),
        headers: { "Content-Type": "application/json" },
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data ? "Ejecución actualizada" : "Ejecución registrada",
          type: "success",
        });
        setArchivos({ cobro_coactivo: null, ruia: null, memorando: null, auto: null });
        for (const t of TIPOS) {
          const input = inputRefs[t].current;
          if (input) input.value = "";
        }
        onGuardado();
      } else {
        toastError(res.detail || "Error al guardar");
      }
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Error al procesar la solicitud");
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    autoTipo,
    autoNumero,
    fechaAuto,
    archivos,
    inputRefs,
    setAutoTipo,
    setFechaAuto,
    onAutoNumeroChange,
    onFileChange,
    onSubmit,
  };
}

export type EjecucionFormState = ReturnType<typeof useEjecucionForm>;
