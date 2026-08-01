import { useState, useEffect, useRef } from "react";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../../utils/fileUpload";
import {
  openDocumentById,
  isValidDocumentId,
} from "../../../../utils/documentViewer";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import ExecutionView from "./EjecucionView";
import ExecutionForm from "./EjecucionForm";

type Execution = {
  id?: number;
  cobro_coactivo: boolean;
  documento_cobro_coactivo_id: number | null;
  disposicion: boolean;
  ruia: boolean;
  documento_ruia_id: number | null;
  memorando: boolean;
  documento_memorando_id: number | null;
  auto_admin: string;
  fecha_auto: string | null;
  documento_auto_id: number | null;
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
  expedienteId: number;
  tipoEtapa: string;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function EjecucionSancionData({
  data,
  setToast,
  etapaId,
  expedienteId,
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

  const handleViewDocument = (documentId: number) => {
    if (isValidDocumentId(documentId)) {
      openDocumentById(documentId);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const form = e.target as HTMLFormElement;

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
        !data?.documento_cobro_coactivo_id
      ) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento de Cobro Coactivo",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (ruiaChecked && !ruiaFile && !data?.documento_ruia_id) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento RUIA",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (memorandoChecked && !memorandoFile && !data?.documento_memorando_id) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento de Memorando",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (!fechaAuto) {
        setToast({
          id: Date.now(),
          message: "La fecha del auto es requerida",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      if (!autoFile && !data?.documento_auto_id) {
        setToast({
          id: Date.now(),
          message: "Debe adjuntar el documento del Acto Administrativo",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      // Paso 1: Subir todos los archivos a app-docs en paralelo
      const uploadPromises: Promise<{ type: string; fileId: number }>[] = [];

      if (cobroCoactivoFile) {
        const fileName = generateDocumentFileName(
          "COBRO_COACTIVO",
          autoAdminCompleto,
          fechaAuto,
        );
        uploadPromises.push(
          uploadFileToDocuments(cobroCoactivoFile, fileName).then((fileId) => ({
            type: "cobro_coactivo",
            fileId,
          })),
        );
      }

      if (ruiaFile) {
        const fileName = generateDocumentFileName(
          "RUIA",
          autoAdminCompleto,
          fechaAuto,
        );
        uploadPromises.push(
          uploadFileToDocuments(ruiaFile, fileName).then((fileId) => ({
            type: "ruia",
            fileId,
          })),
        );
      }

      if (memorandoFile) {
        const fileName = generateDocumentFileName(
          "MEMORANDO",
          autoAdminCompleto,
          fechaAuto,
        );
        uploadPromises.push(
          uploadFileToDocuments(memorandoFile, fileName).then((fileId) => ({
            type: "memorando",
            fileId,
          })),
        );
      }

      if (autoFile) {
        const fileName = generateDocumentFileName(
          "AUTO",
          autoAdminCompleto,
          fechaAuto,
        );
        uploadPromises.push(
          uploadFileToDocuments(autoFile, fileName).then((fileId) => ({
            type: "auto",
            fileId,
          })),
        );
      }

      const uploadResults = await Promise.all(uploadPromises);

      // Paso 2: Preparar datos para enviar al backend
      const requestBody: any = {
        etapa_id: etapaId.toString(),
        cobro_coactivo: cobroCoactivoChecked.toString(),
        disposicion: disposicionChecked.toString(),
        ruia: ruiaChecked.toString(),
        memorando: memorandoChecked.toString(),
        auto_admin: autoAdminCompleto,
        fecha_auto: fechaAuto,
      };

      uploadResults.forEach(({ type, fileId }) => {
        switch (type) {
          case "cobro_coactivo":
            requestBody.documento_cobro_coactivo_id = fileId.toString();
            break;
          case "ruia":
            requestBody.documento_ruia_id = fileId.toString();
            break;
          case "memorando":
            requestBody.documento_memorando_id = fileId.toString();
            break;
          case "auto":
            requestBody.documento_auto_id = fileId.toString();
            break;
        }
      });

      // Mantener IDs existentes para documentos no reemplazados
      if (!cobroCoactivoFile && data?.documento_cobro_coactivo_id) {
        requestBody.documento_cobro_coactivo_id =
          data.documento_cobro_coactivo_id.toString();
      }
      if (!ruiaFile && data?.documento_ruia_id) {
        requestBody.documento_ruia_id = data.documento_ruia_id.toString();
      }
      if (!memorandoFile && data?.documento_memorando_id) {
        requestBody.documento_memorando_id =
          data.documento_memorando_id.toString();
      }
      if (!autoFile && data?.documento_auto_id) {
        requestBody.documento_auto_id = data.documento_auto_id.toString();
      }

      const endpoint = data?.id
        ? API_CONFIG.ENDPOINTS.FILE_EXECUTION_UPDATE(expedienteId)
        : API_CONFIG.ENDPOINTS.FILE_EXECUTION_CREATE(expedienteId);
      const res = await apiCall(endpoint, {
        method: data?.id ? "PUT" : "POST",
        body: JSON.stringify(requestBody),
        headers: { "Content-Type": "application/json" },
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

        onDataUpdated?.();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al guardar",
          type: "error",
        });
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Error al procesar la solicitud";

      setToast({
        id: Date.now(),
        message: errorMessage,
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
