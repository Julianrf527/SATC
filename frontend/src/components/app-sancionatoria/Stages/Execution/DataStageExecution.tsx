import { useState, useEffect, useRef } from "react";
import { apiCall, API_CONFIG, BASE_URL } from "../../../../utils/api";
import ExecutionView from "./ExecutionView";
import ExecutionForm from "./ExecutionForm";

type Execution = {
  id?: number;
  cobro_coactivo: boolean;
  cobro_coactivo_doc_url: string | null;
  disposicion: boolean;
  ruia: boolean;
  ruia_doc_url: string | null;
  memorando: boolean;
  memorando_doc_url: string | null;
  auto_admin: string;
  fecha_auto: string | null;
  auto_doc_url: string | null;
  etapa_id: number;
};

type Props = {
  data: Execution | undefined;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  etapaId: number;
  tipoEtapa: string;
  idAuxiliar: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function DataStageExecution({
  data,
  setToast,
  etapaId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(!data && isEditable);
  const [isLoading, setIsLoading] = useState(false);
  const [autoTipo, setAutoTipo] = useState<string>("AUTO");
  const [autoNumero, setAutoNumero] = useState<string>("");
  const [cobroCoactivoFile, setCobroCoactivoFile] = useState<File | null>(null);
  const [ruiaFile, setRuiaFile] = useState<File | null>(null);
  const [memorandoFile, setMemorandoFile] = useState<File | null>(null);
  const [autoFile, setAutoFile] = useState<File | null>(null);

  const cobroCoactivoInputRef = useRef<HTMLInputElement>(null);
  const ruiaInputRef = useRef<HTMLInputElement>(null);
  const memorandoInputRef = useRef<HTMLInputElement>(null);
  const autoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (data?.auto_admin) {
      const match = data.auto_admin.match(/^(AUTO|RES)(.*)$/);
      if (match) {
        setAutoTipo(match[1]);
        setAutoNumero(match[2]);
      } else {
        setAutoTipo("AUTO");
        setAutoNumero(data.auto_admin);
      }
    } else {
      setAutoTipo("AUTO");
      setAutoNumero("");
    }
  }, [data?.auto_admin]);

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    fileType: "cobro_coactivo" | "ruia" | "memorando" | "auto",
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      setToast({
        id: Date.now(),
        message: "Solo se permiten archivos PDF",
        type: "error",
      });
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setToast({
        id: Date.now(),
        message: "El archivo no debe superar los 10MB",
        type: "error",
      });
      return;
    }

    const setters = {
      cobro_coactivo: setCobroCoactivoFile,
      ruia: setRuiaFile,
      memorando: setMemorandoFile,
      auto: setAutoFile,
    };

    setters[fileType](file);
  };

  const handleAutoNumeroChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (/^\d{0,4}$/.test(value)) {
      setAutoNumero(value);
    }
  };

  const handleViewDocument = (url: string) => {
    const fullUrl = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(url)}`;
    window.open(fullUrl, "_blank");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const form = e.target as HTMLFormElement;
      const formData = new FormData();

      // Validar número del auto
      if (autoNumero.length !== 4) {
        setToast({
          id: Date.now(),
          message: "El numerado debe tener exactamente 4 dígitos",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      const autoAdminCompleto = autoTipo + autoNumero;

      // Obtener valores de checkboxes
      const cobroCoactivoChecked =
        (form.elements.namedItem("cobro_coactivo") as HTMLInputElement)
          ?.checked || false;
      const disposicionChecked =
        (form.elements.namedItem("disposicion") as HTMLInputElement)?.checked ||
        false;
      const ruiaChecked =
        (form.elements.namedItem("ruia") as HTMLInputElement)?.checked || false;
      const memorandoChecked =
        (form.elements.namedItem("memorando") as HTMLInputElement)?.checked ||
        false;
      const fechaAuto = (
        form.elements.namedItem("fecha_auto") as HTMLInputElement
      )?.value;

      // Validaciones: Si el checkbox está marcado, debe tener documento
      if (
        cobroCoactivoChecked &&
        !cobroCoactivoFile &&
        !data?.cobro_coactivo_doc_url
      ) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento de Cobro Coactivo",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (ruiaChecked && !ruiaFile && !data?.ruia_doc_url) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento RUIA",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (memorandoChecked && !memorandoFile && !data?.memorando_doc_url) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento de Memorando",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      // Validar campos requeridos del acto administrativo
      if (!fechaAuto) {
        setToast({
          id: Date.now(),
          message: "La fecha del auto es requerida",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (!autoFile && !data?.auto_doc_url) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento del Acto Administrativo",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      // Agregar datos al FormData - Enviando booleanos correctamente
      formData.append("etapa_id", etapaId.toString());
      formData.append("cobro_coactivo", cobroCoactivoChecked.toString());
      formData.append("disposicion", disposicionChecked.toString());
      formData.append("ruia", ruiaChecked.toString());
      formData.append("memorando", memorandoChecked.toString());
      formData.append("auto_admin", autoAdminCompleto);
      formData.append("fecha_auto", fechaAuto);

      // Agregar archivos si existen
      if (cobroCoactivoFile)
        formData.append("cobro_coactivo_doc", cobroCoactivoFile);
      if (ruiaFile) formData.append("ruia_doc", ruiaFile);
      if (memorandoFile) formData.append("memorando_doc", memorandoFile);
      if (autoFile) formData.append("auto_doc", autoFile);

      const endpoint = data?.id
        ? API_CONFIG.ENDPOINTS.FILE_EXECUTION_UPDATE(data.id)
        : API_CONFIG.ENDPOINTS.FILE_EXECUTION_CREATE;
      const res = await apiCall(endpoint, {
        method: data?.id ? "PUT" : "POST",
        body: formData,
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data?.id ? "Ejecución actualizada" : "Ejecución registrada",
          type: "success",
        });
        setShowForm(false);
        setCobroCoactivoFile(null);
        setRuiaFile(null);
        setMemorandoFile(null);
        setAutoFile(null);
        if (cobroCoactivoInputRef.current)
          cobroCoactivoInputRef.current.value = "";
        if (ruiaInputRef.current) ruiaInputRef.current.value = "";
        if (memorandoInputRef.current) memorandoInputRef.current.value = "";
        if (autoInputRef.current) autoInputRef.current.value = "";

        // Actualizar datos desde el servidor
        onDataUpdated?.();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al guardar",
          type: "error",
        });
      }
    } catch (error) {
      /* console.error("Error al guardar:", error); */
      setToast({
        id: Date.now(),
        message: "Error al procesar la solicitud",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    if (data) {
      setShowForm(false);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-primary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Ejecución de la Sanción</h3>
              <p className="text-sm text-base-content/60">
                {data
                  ? "Información sobre la ejecución"
                  : isEditable
                    ? "Registra información de ejecución"
                    : "No hay ejecución registrada"}
              </p>
            </div>
          </div>
          {!showForm && data && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 hover:bg-primary/10"
              onClick={() => setShowForm(true)}
              disabled={isLoading}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                ></path>
              </svg>
            </button>
          )}
        </div>

        {/* Vista de Solo Lectura */}
        {!showForm && data && (
          <ExecutionView data={data} onViewDocument={handleViewDocument} />
        )}

        {/* Estado Vacío - Solo Lectura */}
        {!showForm && !data && !isEditable && (
          <div className="text-center py-8 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
            <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4 mx-auto">
              <svg
                className="w-8 h-8 text-base-content/40"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-base-content/70 mb-2">
              Sin ejecución registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de ejecución para este expediente
            </p>
          </div>
        )}

        {/* Formulario de Edición */}
        {showForm && isEditable && (
          <ExecutionForm
            data={data}
            isLoading={isLoading}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            onViewDocument={handleViewDocument}
            onFileChange={handleFileChange}
            autoTipo={autoTipo}
            autoNumero={autoNumero}
            onAutoTipoChange={setAutoTipo}
            onAutoNumeroChange={handleAutoNumeroChange}
            cobroCoactivoInputRef={cobroCoactivoInputRef}
            ruiaInputRef={ruiaInputRef}
            memorandoInputRef={memorandoInputRef}
            autoInputRef={autoInputRef}
            cobroCoactivoFile={cobroCoactivoFile}
            ruiaFile={ruiaFile}
            memorandoFile={memorandoFile}
            autoFile={autoFile}
          />
        )}
      </div>
    </div>
  );
}
