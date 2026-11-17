import { useState } from "react";
import type { EtapaTab } from "./etapasTabs";

type Props = {
  tabs: EtapaTab[];
  activeTab: string;
  isDisponible: (tabId: string) => boolean;
  onTabClick: (tabId: string) => void;
};

/** Barra colapsable con las etapas del proceso del expediente. */
export default function EtapasNavegacion({ tabs, activeTab, isDisponible, onTabClick }: Props) {
  const [colapsada, setColapsada] = useState(false);
  const actual = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="flex-shrink-0 bg-base-100 border-b border-base-300">
      {/* Barra colapsada - muestra la etapa actual */}
      {colapsada && (
        <div className="px-4 py-3">
          <div className="container mx-auto max-w-7xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-success/20 rounded-full flex items-center justify-center flex-shrink-0">
                <i className={`bx ${actual?.icon} text-success text-base`}></i>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  Etapa Actual
                </p>
                <p className="text-sm font-semibold text-base-content">{actual?.label}</p>
              </div>
            </div>
            <button
              onClick={() => setColapsada(false)}
              className="btn btn-ghost btn-sm gap-2"
              title="Mostrar todas las etapas"
            >
              <span className="text-xs">Mostrar etapas</span>
              <i className="bx bx-chevron-down text-lg"></i>
            </button>
          </div>
        </div>
      )}

      {/* Barra expandida - todas las etapas */}
      {!colapsada && (
        <div className="px-4 py-2">
          <div className="container mx-auto max-w-7xl">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                Etapas del Proceso
              </h2>
              <button
                onClick={() => setColapsada(true)}
                className="btn btn-ghost btn-xs gap-1"
                title="Ocultar etapas"
              >
                <span className="text-[10px]">Ocultar</span>
                <i className="bx bx-chevron-up text-sm"></i>
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                const disponible = isDisponible(tab.id);
                return (
                  <button
                    key={tab.id}
                    onClick={() => onTabClick(tab.id)}
                    disabled={!disponible}
                    className={`relative flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                      !disponible
                        ? "bg-base-300/50 text-base-content/60 cursor-not-allowed opacity-50"
                        : isActive
                          ? "bg-success text-white shadow-md"
                          : "bg-base-200 text-base-content/70 hover:bg-base-300 hover:text-base-content"
                    }`}
                    title={disponible ? tab.label : `${tab.label} (No disponible)`}
                  >
                    <div
                      className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
                        isActive ? "bg-white/20" : "bg-base-300"
                      }`}
                    >
                      <i
                        className={`bx ${tab.icon} text-sm ${
                          isActive ? "text-white" : "text-base-content/60"
                        }`}
                      ></i>
                    </div>
                    <span className="text-left text-[11px] leading-tight flex-1 truncate">
                      {tab.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
