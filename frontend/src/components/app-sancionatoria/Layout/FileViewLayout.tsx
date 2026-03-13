import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import { useLocation, useNavigate } from "react-router-dom";
import FileList from "../FileManage/FileList";
import FileDetail from "../FileDetail";
import type { BasicFile, Town } from "../../../types";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function FileViewLayout({ setToast }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedFile, setSelectedFile] = useState<BasicFile | null>(null);
  const [showFileList, setShowFileList] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [showAccessDeniedModal, setShowAccessDeniedModal] = useState(false);
  const [theme, setTheme] = useState<string>("emerald");

  const [resourceList, setResourceList] = useState<
    { id: number; name: string }[]
  >([]);
  const [townList, setTownList] = useState<Town[]>([]);
  const [fileList, setFileList] = useState<BasicFile[]>([]);

  // Detectar el tema actual del documento
  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

  // Seleccionar archivo desde navegación
  useEffect(() => {
    if (location.state?.radicadoToSelect && fileList.length > 0) {
      const fileToSelect = fileList.find(
        (f) => f.radicado === location.state.radicadoToSelect
      );

      if (fileToSelect) {
        setSelectedFile(fileToSelect);
      } else {
        setShowAccessDeniedModal(true);
      }

      window.history.replaceState({}, document.title);
    }
  }, [location.state?.radicadoToSelect, fileList]);

  // Cargar recursos y municipios
  useEffect(() => {
    const getResourcesAndTowns = async () => {
      try {
        setIsLoading(true);
        const [dataTowns, dataResources] = await Promise.all([
          apiCall(API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK, { method: "GET" }),
          apiCall(API_CONFIG.ENDPOINTS.FILE_AFFECTED_RESOURCE, {
            method: "GET",
          }),
        ]);

        if (dataTowns.ok) {
          setTownList(dataTowns.data);
        } else {
          setToast({
            id: Date.now(),
            message: dataTowns.detail || "Error al cargar los municipios",
            type: "error",
          });
        }

        if (dataResources.ok) {
          setResourceList(dataResources.data);
        } else {
          setToast({
            id: Date.now(),
            message:
              dataResources.detail || "Error al cargar los recursos afectados",
            type: "error",
          });
        }
      } catch (e) {
        /* console.error("Error en el fetch:", e); */
        setToast({
          id: Date.now(),
          message: "Error en el fetch",
          type: "error",
        });
      } finally {
        setIsLoading(false);
      }
    };

    getResourcesAndTowns();
  }, []);

// Cargar TODOS los expedientes (archivados y no archivados)
  useEffect(() => {
    const getAllFiles = async () => {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.FILES_VIEW, {
          method: "GET",
        });

        if (res.ok) {
          setFileList(res.data);
        } else {
          setToast({
            id: Date.now(),
            message: "Error al cargar los expedientes",
            type: "error",
          });
        }
      } catch (e) {
        /* console.log(e); */
        setToast({
          id: Date.now(),
          message: "Error al cargar los expedientes",
          type: "error",
        });
      }
    };
    getAllFiles();
  }, []);

  const handleCloseAccessDeniedModal = () => {
    setShowAccessDeniedModal(false);
    navigate("/file/view", { replace: true });
  };

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-4rem)] bg-base-200">
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-success"></span>
            <p className="text-base-content font-medium">
              Cargando expedientes...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex h-[calc(100vh-4rem)] bg-gray-100">
        {/* SIDEBAR IZQUIERDO - FileList */}
        <div
          className={`${
            showFileList ? "w-80" : "w-0"
          } transition-all duration-300 ease-in-out overflow-hidden bg-white shadow-lg border-r border-gray-200`}
        >
          <div className="h-full">
            <FileList
              isEditable={false}
              setToast={setToast}
              setSelectedFile={setSelectedFile}
              townList={townList}
              resourceList={resourceList}
              fileList={fileList}
              setFileList={setFileList}
            />
          </div>
        </div>

        {/* DIVISOR CON BOTÓN TOGGLE */}
        <div
          className="relative flex items-center justify-center bg-gray-200 hover:bg-gray-300 transition-colors duration-200"
          style={{ width: "2px" }}
        >
          <button
            onClick={() => setShowFileList(!showFileList)}
            className="absolute w-8 h-12 bg-white hover:bg-gray-50 shadow-md border border-gray-300 rounded-md 
                       flex items-center justify-center transition-all duration-200 hover:shadow-lg
                       hover:scale-105 z-10"
          >
            <svg
              className={`w-4 h-4 text-gray-600 transition-transform duration-300 ${
                showFileList ? "rotate-180" : "rotate-0"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>

        {/* CONTENIDO PRINCIPAL - FileDetail */}
        <div className="flex-1 overflow-hidden bg-gray-50">
          <FileDetail
            isEditable={false}
            file={selectedFile}
            towns={townList}
            resources={resourceList}
            setToast={setToast}
          />
        </div>
      </div>

      {/* Modal de acceso denegado */}
      {showAccessDeniedModal && (
        <div
          data-theme={theme}
          className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
        >
          <div className="bg-base-100 rounded-2xl w-full max-w-md mx-4 shadow-2xl border border-base-300 animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="px-6 py-5 border-b border-base-300">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-warning/10 rounded-xl flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-warning"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
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
                  <h3 className="font-bold text-lg text-base-content">
                    Expediente No Encontrado
                  </h3>
                  <p className="text-xs text-base-content/60">
                    El expediente solicitado no existe
                  </p>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-5">
              <p className="text-sm text-base-content/80 leading-relaxed">
                El expediente que intentas visualizar no se encuentra en el
                sistema o ha sido eliminado.
              </p>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-base-300 flex justify-end">
              <button
                onClick={handleCloseAccessDeniedModal}
                className="btn btn-success text-white gap-2"
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
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
