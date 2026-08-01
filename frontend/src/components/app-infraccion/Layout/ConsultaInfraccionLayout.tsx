import { useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import { apiCall, API_CONFIG } from "../../../utils/api";
import { useLocation, useNavigate } from "react-router-dom";
import ExpedienteList from "../Manage/ExpedienteList";
import DetalleInfraccion from "../Manage/DetalleInfraccion";
import type { Expediente, Quejoso, TipoAfectacion } from "../../../types/infraccionApp";
import type { ModeloGenerico, Municipio } from "../../../types/common";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ConsultaInfraccionLayout({ setToast }: Props) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [expedienteSeleccionado, setExpedienteSeleccionado] =
    useState<Expediente | null>(null);
  const [showExpedienteList, setShowExpedienteList] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [showAccessDeniedModal, setShowAccessDeniedModal] = useState(false);
  const [theme, setTheme] = useState<string>("emerald");

  const [recursoAfectadoList, setRecursoAfectadoList] = useState<
    ModeloGenerico[]
  >([]);
  const [municipioList, setMunicipioList] = useState<Municipio[]>([]);
  const [tipoAfectacionList, setTipoAfectacionList] = useState<TipoAfectacion[]>([]);
  const [expedienteList, setExpedienteList] = useState<Expediente[]>([]);
  const [quejosoList, setQuejosoList] = useState<Quejoso[]>([]);

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

  useEffect(() => {
    if (location.state?.radicadoToSelect && expedienteList.length > 0) {
      const expedienteToSelect = expedienteList.find(
        (f) => f.radicado === location.state.radicadoToSelect,
      );

      if (expedienteToSelect) {
        setExpedienteSeleccionado(expedienteToSelect);
      } else {
        setShowAccessDeniedModal(true);
      }

      window.history.replaceState({}, document.title);
    }
  }, [
    location.state?.radicadoToSelect,
    location.state?.timestamp,
    expedienteList,
  ]);

  useEffect(() => {
    const getResources = async () => {
      try {
        setIsLoading(true);
        const [municipios, recursos, tipos, quejosos] = await Promise.all([
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT, {
            method: "GET",
          }),
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_AFFECTED_RESOURCE, {
            method: "GET",
          }),
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_TIPOS_AFECTACION, { method: "GET" }),
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_COMPLAINER, {
            method: "GET",
          }),
        ]);

        if (municipios.ok) {
          setMunicipioList(municipios.data);
        } else {
          setToast({
            id: Date.now(),
            message: municipios.detail || "Error al cargar los municipios",
            type: "error",
          });
        }

        if (recursos.ok) {
          setRecursoAfectadoList(recursos.data);
        } else {
          setToast({
            id: Date.now(),
            message:
              recursos.detail || "Error al cargar los recursos afectados",
            type: "error",
          });
        }

        if (tipos.ok) {
          setTipoAfectacionList(tipos.data || []);
        } else {
          setToast({
            id: Date.now(),
            message: tipos.detail || "Error al cargar los tipos de afectación",
            type: "error",
          });
        }

        if (quejosos.ok) {
          setQuejosoList(quejosos.data);
        } else {
          setToast({
            id: Date.now(),
            message: quejosos.detail || "Error al cargar los quejosos",
            type: "error",
          });
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error en el fetch",
          type: "error",
        });
      } finally {
        setIsLoading(false);
      }
    };

    getResources();
  }, [setToast]);

  useEffect(() => {
    const getFiles = async () => {
      try {
        if (user) {
          const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_VIEW);
          if (res.ok) {
            setExpedienteList(res.data);
          } else {
            setToast({
              id: Date.now(),
              message: "Error al cargar los expedientes",
              type: "error",
            });
          }
        } else {
          setExpedienteList([]);
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error al cargar los expedientes",
          type: "error",
        });
      }
    };

    getFiles();
  }, [user, setToast]);

  const handleFileUpdate = (updatedFile: Expediente) => {
    setExpedienteList((prevList) =>
      prevList.map((f) =>
        f.radicado === expedienteSeleccionado?.radicado
          ? { ...updatedFile }
          : f,
      ),
    );

    setExpedienteSeleccionado({ ...updatedFile });
    setToast({
      id: Date.now(),
      message: "Expediente actualizado exitosamente",
      type: "success",
    });
  };

  const handleArchiveSuccess = () => {
    if (!expedienteSeleccionado) return;

    setExpedienteList((prevList) =>
      prevList.filter((f) => f.radicado !== expedienteSeleccionado.radicado),
    );

    setExpedienteSeleccionado(null);
  };

  const handleCloseAccessDeniedModal = () => {
    setShowAccessDeniedModal(false);
    navigate("/infraction/consult", { replace: true });
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
        <div
          className={`${showExpedienteList ? "w-80" : "w-0"} transition-all duration-300 ease-in-out overflow-hidden bg-white shadow-lg border-r border-gray-200`}
        >
          <div className="h-full">
            <ExpedienteList
              isEditable={false}
              setToast={setToast}
              setExpedienteSeleccionado={setExpedienteSeleccionado}
              municipioList={municipioList}
              recursoAfectadoList={recursoAfectadoList}
              tipoAfectacionList={tipoAfectacionList}
              expedienteList={expedienteList}
              quejosoList={quejosoList}
              setQuejosoList={setQuejosoList}
              setExpedienteList={setExpedienteList}
            />
          </div>
        </div>

        <div
          className="relative flex items-center justify-center bg-gray-200 hover:bg-gray-300 transition-colors duration-200"
          style={{ width: "2px" }}
        >
          <button
            onClick={() => setShowExpedienteList(!showExpedienteList)}
            className="absolute w-8 h-12 bg-white hover:bg-gray-50 shadow-md border border-gray-300 rounded-md flex items-center justify-center transition-all duration-200 hover:shadow-lg hover:scale-105 z-10"
          >
            <svg
              className={`w-4 h-4 text-gray-600 transition-transform duration-300 ${
                showExpedienteList ? "rotate-180" : "rotate-0"
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

        <div className="flex-1 overflow-hidden bg-gray-50">
          <DetalleInfraccion
            expedienteSeleccionado={expedienteSeleccionado}
            municipioList={municipioList}
            recursoAfectadoList={recursoAfectadoList}
            tipoAfectacionList={tipoAfectacionList}
            quejosoList={quejosoList}
            setToast={setToast}
            isEditable={false}
            onUpdate={handleFileUpdate}
            onArchiveSuccess={handleArchiveSuccess}
          />
        </div>
      </div>

      {showAccessDeniedModal && (
        <div
          data-theme={theme}
          className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
        >
          <div className="bg-base-100 rounded-2xl w-full max-w-md mx-4 shadow-2xl border border-base-300 animate-in zoom-in-95 duration-200">
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
                    Acceso Denegado
                  </h3>
                  <p className="text-xs text-base-content/60">
                    No tienes permisos para este expediente
                  </p>
                </div>
              </div>
            </div>

            <div className="px-6 py-5">
              <p className="text-sm text-base-content/80 leading-relaxed">
                Ya no te encuentras vinculado con este expediente. Es posible
                que hayas sido desvinculado o que el expediente haya sido
                reasignado a otro usuario.
              </p>
              <div className="mt-4 p-4 bg-info/10 rounded-lg border border-info/20">
                <p className="text-xs text-base-content/70">
                  <strong>Nota:</strong> Si crees que esto es un error, contacta
                  al administrador del sistema.
                </p>
              </div>
            </div>

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
