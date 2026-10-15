import { useState } from "react";
import { ChevronDown, Search, SlidersHorizontal, UserSearch, X } from "lucide-react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Municipio } from "@shared/types/common";
import { buscarPersona } from "../../api/involucrados";
import { contarFiltrosActivos, FILTROS_LISTA_INICIALES, type FiltrosListaExpedientes } from "../../api/listaParams";
import type { SetToast } from "../../types";

type Props = {
  filtros: FiltrosListaExpedientes;
  /** Cambia filtros (siempre vuelve a la página 1). */
  onChange: (cambio: Partial<FiltrosListaExpedientes>) => void;
  municipios: Municipio[];
  setToast: SetToast;
};

const TIPOS_DOCUMENTO = [
  { value: "CC", label: "CC" },
  { value: "NIT", label: "NIT" },
  { value: "CE", label: "CE" },
  { value: "PP", label: "PP" },
];

/**
 * Cabecera de la lista: búsqueda por radicado y filtros del backend
 * (API.md A.2). Mismo aspecto que el panel de `@features/expedientes`, pero
 * aquí todo se filtra en BD porque el listado es paginado.
 */
export default function FiltrosListaPanel({ filtros, onChange, municipios, setToast }: Props) {
  const [abiertos, setAbiertos] = useState(false);
  const [tipoDoc, setTipoDoc] = useState("CC");
  const [documento, setDocumento] = useState("");
  const [persona, setPersona] = useState<string | null>(null);
  const [buscando, setBuscando] = useState(false);

  const activos = contarFiltrosActivos(filtros);
  const veredas = municipios.find((m) => m.id === filtros.municipio_id)?.veredas ?? [];

  const buscarSolicitante = async () => {
    if (!documento.trim()) return;
    setBuscando(true);
    try {
      const encontrada = await buscarPersona(tipoDoc, documento.trim());
      if (!encontrada) {
        setToast({ id: Date.now(), message: "No se encontró una persona con ese documento", type: "error" });
        return;
      }
      setPersona(encontrada.nombre ?? `#${encontrada.id}`);
      onChange({ involucrado_id: encontrada.id });
    } finally {
      setBuscando(false);
    }
  };

  const quitarSolicitante = () => {
    setPersona(null);
    setDocumento("");
    onChange({ involucrado_id: null });
  };

  const limpiar = () => {
    setPersona(null);
    setDocumento("");
    onChange({ ...FILTROS_LISTA_INICIALES, limit: filtros.limit });
  };

  return (
    <div className="flex-shrink-0 p-6 border-b border-base-300 bg-base-100">
      <h2 className="text-2xl font-bold text-base-content mb-4">Expedientes</h2>

      <div className="relative">
        <input
          className="w-full input"
          placeholder="Buscar por radicado..."
          type="text"
          value={filtros.radicado}
          onChange={(e) => onChange({ radicado: e.target.value })}
        />
        <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-base-content/40" />
      </div>

      <button
        type="button"
        onClick={() => setAbiertos(!abiertos)}
        className="btn btn-ghost btn-sm w-full justify-between mt-3"
        aria-expanded={abiertos}
      >
        <span className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4" />
          Filtros
          {activos > 0 && <span className="badge badge-success badge-sm text-white">{activos}</span>}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${abiertos ? "rotate-180" : "rotate-0"}`} />
      </button>

      <div className={`${abiertos ? "block" : "hidden"} mt-3 space-y-3`}>
        <input
          className="input input-sm w-full"
          placeholder="Expediente (ej: CA 001)"
          type="text"
          value={filtros.expediente}
          onChange={(e) => onChange({ expediente: e.target.value })}
        />
        <input
          className="input input-sm w-full"
          placeholder="Número VITAL"
          type="text"
          value={filtros.numero_vital}
          onChange={(e) => onChange({ numero_vital: e.target.value })}
        />
        <CustomSelect
          className="select-sm"
          value={filtros.municipio_id}
          onChange={(id) => onChange({ municipio_id: id, vereda_id: 0 })}
          placeholder="Todos los municipios"
          emptyValue={0}
          options={municipios.map((m) => ({ value: m.id, label: m.nombre }))}
        />
        {filtros.municipio_id > 0 && (
          <CustomSelect
            className="select-sm"
            value={filtros.vereda_id}
            onChange={(id) => onChange({ vereda_id: id })}
            placeholder="Todas las veredas"
            emptyValue={0}
            options={veredas.map((v) => ({ value: v.id, label: v.nombre }))}
          />
        )}

        {persona ? (
          <div className="flex items-center gap-2 border border-success/40 bg-success/5 rounded-lg px-3 py-1.5">
            <UserSearch size={14} className="text-success" />
            <span className="text-xs flex-1 truncate" title={persona}>
              {persona}
            </span>
            <button type="button" className="btn btn-ghost btn-xs" onClick={quitarSolicitante} aria-label="Quitar filtro de persona">
              <X size={12} />
            </button>
          </div>
        ) : (
          <div className="flex gap-1">
            <CustomSelect className="select-sm w-20" value={tipoDoc} onChange={setTipoDoc} hidePlaceholderOption options={TIPOS_DOCUMENTO} />
            <input
              className="input input-sm flex-1 min-w-0 font-mono"
              placeholder="Documento involucrado"
              type="text"
              value={documento}
              onChange={(e) => setDocumento(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => {
                if (e.key === "Enter") void buscarSolicitante();
              }}
            />
            <button
              type="button"
              className="btn btn-sm btn-outline"
              onClick={() => void buscarSolicitante()}
              disabled={buscando || !documento.trim()}
              aria-label="Buscar persona"
            >
              {buscando ? <span className="loading loading-spinner loading-xs" /> : <Search size={14} />}
            </button>
          </div>
        )}
      </div>

      {activos > 0 && (
        <button type="button" onClick={limpiar} className="btn btn-sm btn-ghost w-full mt-3 gap-2">
          <X className="w-4 h-4" />
          Limpiar todos los filtros
        </button>
      )}
    </div>
  );
}
