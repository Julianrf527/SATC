import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ActoAdmin from "../../Common/ActoAdministrativo/ActoAdmin";
import Documentos from "./Document/Document";
import DataStageMeasure from "./MedidaPreventiva/MedidaPreventivaData";

type DocumentoData = {
  id: number;
  nombre: string;
  documento_anexo_id: number;
  fecha_subida: string;
};

type MigracionData = {
  medida: { tipo_medida_id: number; cantidad: string; especie: string; estado_medida: boolean | null };
  informe_tecnico_documento_id: number | null;
  acto: {
    tipo_acto: string;
    numerado: number;
    fecha_numerado: string | null;
    documento_acto_administrativo_id: number;
    comunicacion?: {
      numerado: number;
      fecha_numerado: string | null;
      fecha_envio: string | null;
      documento_comunicacion_id: number;
    } | null;
  } | null;
};

type Props = {
  expedienteId: number;
  radicado?: string;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "DETALLE MEDIDA PREVENTIVA";
const TIPOS_DOCUMENTO = ["Informe Tecnico", "Solicitud Revocatoria Directa"];

export default function DetalleMedidaPreventiva({
  expedienteId,
  radicado,
  setToast,
  onStageUpdate,
  isEditable = true,
}: Props) {
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [localMedida, setLocalMedida] = useState<any>(null);
  const [existActoAdmin, setExistActoAdmin] = useState<boolean>(false);
  const [migracionData, setMigracionData] = useState<MigracionData | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [documentos, setDocumentos] = useState<DocumentoData[]>([]);
  const [tiposMedidaList, setTiposMedidaList] = useState<{id:number; nombre:string}[]>([]);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch tipos en mount — independiente del estado de la etapa
  useEffect(() => {
    apiCall(API_CONFIG.ENDPOINTS.FILE_TIPO_MEDIDA, { method: "GET" })
      .then((res) => { if (res.ok) setTiposMedidaList(res.data || []); })
      .catch(() => {});
  }, []);

  const fetchMedida = useCallback(async () => {
    if (!expedienteId) {
      setIsLoadingData(false);
      return;
    }

    try {
      setIsLoadingData(true);

      // Solo mostrar loading si tarda más de 300ms
      loadingTimerRef.current = setTimeout(() => {
        setShowLoading(true);
      }, 300);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_MEASURE(expedienteId),
        {
          method: "GET",
        },
      );

      if (res.ok) {
        setLocalMedida(res.medida);
        setDocumentos(res.medida?.documentos_anexos || []);
        if (res.medida?.acto_admin?.id) {
          setExistActoAdmin(true);
        }
        // Si la etapa aún no existe y hay radicado, buscar datos migrables desde infracciones
        if (!res.medida?.etapa_id && radicado) {
          try {
            const migRes = await apiCall(
              API_CONFIG.ENDPOINTS.INFRACTION_MIGRATION_MEDIDA(radicado),
              { method: "GET" },
            );
            if (migRes.ok) setMigracionData(migRes);
          } catch { /* silently ignore — migration is optional */ }
        }
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al obtener la medida preventiva.",
        type: "error",
      });
    } finally {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      setShowLoading(false);
      setIsLoadingData(false);
    }
  }, [expedienteId, setToast]);

  useEffect(() => {
    fetchMedida();

    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, [fetchMedida]);

  const handleImportarDesdeInfracciones = async () => {
    if (!migracionData || !expedienteId) return;
    setIsImporting(true);
    try {
      // 1. Crear etapa medida preventiva con los datos importados
      const resCreate = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_MEASURE_CREATE(expedienteId),
        {
          method: "POST",
          body: JSON.stringify({
            tipo_medida_id: migracionData.medida.tipo_medida_id,
            cantidad: migracionData.medida.cantidad,
            especie: migracionData.medida.especie,
            estado_medida: migracionData.medida.estado_medida,
          }),
        },
      );

      if (!resCreate.ok) {
        setToast({ id: Date.now(), message: resCreate.detail || "Error al importar datos", type: "error" });
        return;
      }

      const etapaId = resCreate.etapa_id;

      // 2. Importar acto administrativo si tiene documento
      if (migracionData.acto && etapaId) {
        const formData = new FormData();
        formData.append("expediente_id", String(expedienteId));
        formData.append("tipo_acto", migracionData.acto.tipo_acto);
        formData.append("numerado", String(migracionData.acto.numerado));
        formData.append("fecha_numerado", migracionData.acto.fecha_numerado ?? "");
        formData.append("documento_acto_administrativo_id", String(migracionData.acto.documento_acto_administrativo_id));
        formData.append("etapa_tipo", "etapa_medida_preventiva");
        formData.append("etapa_ref_id", String(etapaId));
        const resActo = await apiCall(API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN, { method: "POST", body: formData });
        if (!resActo.ok) {
          setToast({ id: Date.now(), message: resActo.detail || "Error al importar el acto administrativo", type: "error" });
          return;
        }

        // 2.1 Importar comunicación del acto, si existe
        const com = migracionData.acto.comunicacion;
        const actoId = resActo.data?.id;
        if (com && com.documento_comunicacion_id && actoId) {
          const comFormData = new FormData();
          comFormData.append("expediente_id", String(expedienteId));
          comFormData.append("acto_admin_id", String(actoId));
          comFormData.append("numerado", String(com.numerado).padStart(4, "0"));
          comFormData.append("fecha_numerado", com.fecha_numerado ?? "");
          comFormData.append("fecha_envio", com.fecha_envio ?? "");
          comFormData.append("documento_comunicacion_id", String(com.documento_comunicacion_id));
          const resCom = await apiCall(API_CONFIG.ENDPOINTS.FILE_COMUNICACION, { method: "POST", body: comFormData });
          if (!resCom.ok) {
            setToast({ id: Date.now(), message: resCom.detail || "Error al importar la comunicación del acto", type: "error" });
            return;
          }
        }
      }

      // 3. Si hay informe técnico aprobado en infracciones, adjuntarlo como documento anexo
      if (migracionData.informe_tecnico_documento_id && etapaId) {
        await apiCall(
          API_CONFIG.ENDPOINTS.FILE_POST_DOC_ATTACHED(etapaId),
          {
            method: "POST",
            body: JSON.stringify({
              nombre: "Informe Tecnico",
              documento_anexo_id: migracionData.informe_tecnico_documento_id,
            }),
          },
        );
      }

      setToast({ id: Date.now(), message: "Datos importados desde infracciones exitosamente", type: "success" });
      setMigracionData(null);
      onStageUpdate(STAGE_NAME);
      await fetchMedida();
    } catch {
      setToast({ id: Date.now(), message: "Error al importar datos desde infracciones", type: "error" });
    } finally {
      setIsImporting(false);
    }
  };

  const createStage = async () => {
    if (!expedienteId) {
      setToast({
        id: Date.now(),
        message: "No se ha seleccionado un expediente.",
        type: "error",
      });
      return;
    }

    try {
      setIsCreatingStage(true);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_MEASURE_CREATE(expedienteId),
        { method: "POST" },
      );

      if (res.ok && res.etapa_id) {
        const nuevaMedida = {
          etapa_id: res.etapa_id,
          informacion: {},
          acto_admin: {},
          documento: [],
        };
        setLocalMedida(nuevaMedida);
        setDocumentos([]);
        setExistActoAdmin(false);
        onStageUpdate(STAGE_NAME);

        setToast({
          id: Date.now(),
          message: "Etapa creada exitosamente.",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al crear la etapa.",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al crear la etapa.",
        type: "error",
      });
    } finally {
      setIsCreatingStage(false);
    }
  };

  const handleDocumentosUpdate = useCallback(
    (updatedDocumentos: DocumentoData[]) => {
      setDocumentos(updatedDocumentos);
    },
    [],
  );

  // Solo mostrar loading si está cargando Y ha pasado el delay
  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la medida preventiva
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No File Selected
  if (!expedienteId) {
    return (
      <div className="card bg-base-100 shadow w-full">
        <div className="card-body flex items-center justify-center text-gray-500">
          <p>
            Seleccione un expediente para ver {isEditable ? "o editar" : ""} sus
            datos
          </p>
        </div>
      </div>
    );
  }

  // Si aún está cargando pero no ha pasado el delay, mostrar contenedor vacío
  if (isLoadingData) {
    return <div className="min-h-[200px]" />;
  }

  // Stage Doesn't Exist - Read Only
  if (!localMedida?.etapa_id && !isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-16 w-16 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>

            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-gray-700 whitespace-nowrap">
                  "{STAGE_NAME}"
                </span>
                .
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                No hay información disponible para visualizar en esta etapa.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Stage Doesn't Exist - Editable
  if (!localMedida?.etapa_id) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-blue-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-16 w-16 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>

            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-blue-400 whitespace-nowrap">
                  "{STAGE_NAME}"
                </span>
                .
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Para continuar, debe crear esta etapa y así poder gestionar la
                medida preventiva correspondiente.
              </p>
            </div>

            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={createStage}
              disabled={isCreatingStage}
            >
              {isCreatingStage ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Creando etapa...
                </>
              ) : (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Crear Etapa
                </>
              )}
            </button>

            {/* Migración desde infracciones */}
            {migracionData && isEditable && (
              <div className="mt-4 rounded-xl border border-info/30 bg-info/5 overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3">
                  <div className="w-8 h-8 rounded-lg bg-info/15 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-base-content">
                      Datos disponibles desde el proceso de Infracciones
                    </p>
                    <p className="text-xs text-base-content/60 mt-0.5 leading-relaxed">
                      Se encontró una medida preventiva registrada en el expediente de infracciones con el mismo radicado.
                      {migracionData.informe_tecnico_documento_id && " También se adjuntará el informe técnico de visita aprobado."}
                    </p>
                  </div>
                </div>
                <div className="border-t border-info/20 px-4 py-2.5 flex justify-end bg-info/5">
                  <button
                    className="btn btn-info btn-sm text-white gap-2"
                    onClick={handleImportarDesdeInfracciones}
                    disabled={isImporting || isCreatingStage}
                  >
                    {isImporting ? (
                      <><span className="loading loading-spinner loading-xs" />Importando...</>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        Importar desde Infracciones
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Stage Exists - Show Content
  return (
    <div className="space-y-6">
      <ActoAdmin
        expedienteId={expedienteId}
        actoAdmin={localMedida.acto_admin || {}}
        etapaId={localMedida.etapa_id}
        stageBinding={{ type: "etapa_san_medida_preventiva", id: localMedida.etapa_id }}
        tipoEtapa="etapa_medida_preventiva"
        tipoActo="comunicacion"
        setToast={setToast}
        isEditable={isEditable}
        setExistActoAdmin={setExistActoAdmin}
      />
      {existActoAdmin && (
        <DataStageMeasure
          data={localMedida.informacion !== undefined
            ? { id: localMedida.id ?? localMedida.etapa_id, ...localMedida.informacion }
            : null}
          tipoMedida={tiposMedidaList.length > 0 ? tiposMedidaList : (localMedida.informacion?.tipo_medidas || [])}
          setToast={setToast}
          etapaId={localMedida.etapa_id}
          expedienteId={expedienteId}
          isEditable={isEditable}
        />
      )}

      {existActoAdmin ? (
        <Documentos
          documentos={documentos}
          etapaId={localMedida.etapa_id}
          expedienteId={expedienteId}
          tipoEtapa="etapa_medida_preventiva"
          tiposDocumento={TIPOS_DOCUMENTO}
          setToast={setToast}
          isEditable={isEditable}
          onDocumentosUpdate={handleDocumentosUpdate}
        />
      ) : (
        isEditable && (
          <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
            <div className="card-body">
              <div className="flex items-center gap-4">
                <div className="bg-warning/10 rounded-full p-3">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-8 w-8 text-warning"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold">
                    Información y documentos no disponibles
                  </h3>
                  <p className="text-sm text-base-content/70 mt-1">
                    Debe crear un acto administrativo antes de registrar
                    información o subir documentos.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
