import { useEffect, useMemo, useState } from "react";

export type QuejosoOption = {
  id: number;
  nombre: string | null;
  correo?: string | null;
  telefono?: string | number | null;
  anonimo?: boolean;
};

type Props = {
  isOpen: boolean;
  title?: string;
  quejosoList: QuejosoOption[];
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  onCreateQuejoso: (payload: {
    nombre: string | null;
    telefono: string | null;
    correo: string | null;
    anonimo: boolean;
  }) => Promise<QuejosoOption | null>;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onClose: () => void;
  isDisabled?: boolean;
};

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function getDisplayName(q: QuejosoOption): string {
  return q.anonimo ? "Anónimo" : (q.nombre ?? "Sin nombre");
}

export default function QuejosoSelectorModal({
  isOpen,
  title = "Quejosos",
  quejosoList,
  selectedIds,
  onSelectionChange,
  onCreateQuejoso,
  setToast,
  onClose,
  isDisabled = false,
}: Props) {
  const [search, setSearch] = useState("");
  const [newNombre, setNewNombre] = useState("");
  const [newTelefono, setNewTelefono] = useState("");
  const [newCorreo, setNewCorreo] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setSearch("");
    setNewNombre("");
    setNewTelefono("");
    setNewCorreo("");
  }, [isOpen]);

  const selectedQuejosos = useMemo(
    () => quejosoList.filter((q) => selectedIds.includes(q.id)),
    [quejosoList, selectedIds],
  );

  const availableQuejosos = useMemo(() => {
    const text = search.trim().toLowerCase();
    return quejosoList.filter((q) => {
      if (selectedIds.includes(q.id)) return false;
      if (q.anonimo) return false;
      if (!text) return true;
      return (q.nombre ?? "").toLowerCase().includes(text);
    });
  }, [quejosoList, selectedIds, search]);

  const hasAnonimoSelected = selectedQuejosos.some((q) => q.anonimo);

  const handleAdd = (id: number) => {
    if (selectedIds.includes(id)) return;
    onSelectionChange([...selectedIds, id]);
  };

  const handleRemove = (id: number) => {
    onSelectionChange(selectedIds.filter((sid) => sid !== id));
  };

  const handleAddAnonimo = async () => {
    if (hasAnonimoSelected) return;
    setIsCreating(true);
    try {
      const creado = await onCreateQuejoso({
        nombre: null,
        telefono: null,
        correo: null,
        anonimo: true,
      });
      if (!creado) return;
      if (!selectedIds.includes(creado.id)) {
        onSelectionChange([...selectedIds, creado.id]);
      }
      setToast({ id: Date.now(), message: "Quejoso anónimo agregado", type: "success" });
    } catch {
      setToast({ id: Date.now(), message: "Error al agregar quejoso anónimo", type: "error" });
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreate = async () => {
    const nombre = newNombre.trim();
    const telefono = newTelefono.trim();
    const correo = newCorreo.trim();

    if (!nombre) {
      setToast({ id: Date.now(), message: "El nombre del quejoso es obligatorio", type: "error" });
      return;
    }
    const _nombreNorm = nombre.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    if (/\banon[io]/.test(_nombreNorm)) {
      setToast({ id: Date.now(), message: "El nombre no puede hacer referencia a un quejoso anónimo", type: "error" });
      return;
    }
    if (telefono && !/^\d+$/.test(telefono)) {
      setToast({ id: Date.now(), message: "El teléfono debe contener solo números", type: "error" });
      return;
    }
    if (telefono && telefono.length > 10) {
      setToast({ id: Date.now(), message: "El teléfono no puede tener más de 10 dígitos", type: "error" });
      return;
    }
    if (correo && !emailRegex.test(correo)) {
      setToast({ id: Date.now(), message: "El correo no tiene un formato válido", type: "error" });
      return;
    }

    setIsCreating(true);
    try {
      const creado = await onCreateQuejoso({
        nombre,
        telefono: telefono || null,
        correo: correo || null,
        anonimo: false,
      });
      if (!creado) return;
      if (!selectedIds.includes(creado.id)) {
        onSelectionChange([...selectedIds, creado.id]);
      }
      setNewNombre("");
      setNewTelefono("");
      setNewCorreo("");
      setToast({ id: Date.now(), message: "Quejoso creado y seleccionado", type: "success" });
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión al crear quejoso", type: "error" });
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-base-100 shadow-2xl border border-base-300 flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-base-300 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-success/10 flex items-center justify-center">
              <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-semibold text-base-content">{title}</h3>
              <p className="text-xs text-base-content/50">
                {selectedIds.length === 0
                  ? "Ninguno seleccionado"
                  : `${selectedIds.length} seleccionado${selectedIds.length > 1 ? "s" : ""}`}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm btn-circle"
            onClick={onClose}
            disabled={isDisabled || isCreating}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">

          {/* Seleccionados */}
          <div>
            <p className="text-xs font-semibold text-base-content/50 uppercase tracking-widest mb-2">
              Seleccionados
            </p>
            {selectedQuejosos.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {selectedQuejosos.map((q) => (
                  <span
                    key={q.id}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${
                      q.anonimo
                        ? "bg-base-200 border-base-300 text-base-content/70"
                        : "bg-success/10 border-success/30 text-success"
                    }`}
                  >
                    {q.anonimo && (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                      </svg>
                    )}
                    {getDisplayName(q)}
                    <button
                      type="button"
                      onClick={() => handleRemove(q.id)}
                      disabled={isDisabled || isCreating}
                      className="ml-0.5 hover:text-error transition-colors disabled:opacity-50"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-base-content/40 italic">Sin quejosos seleccionados</p>
            )}
          </div>

          <div className="divider my-1" />

          {/* Buscar y agregar existente */}
          <div>
            <p className="text-xs font-semibold text-base-content/50 uppercase tracking-widest mb-2">
              Agregar existente
            </p>
            {hasAnonimoSelected ? (
              <div className="rounded-xl bg-warning/5 px-4 py-3 text-sm text-warning flex items-center gap-2">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Con quejoso anónimo no se pueden vincular otras personas.
              </div>
            ) : (
              <>
                <input
                  type="text"
                  className="input input-bordered input-sm w-full mb-2"
                  placeholder="Buscar por nombre..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  disabled={isDisabled || isCreating}
                />
                <div className="rounded-xl border border-base-300 overflow-hidden">
                  {availableQuejosos.length === 0 ? (
                    <div className="py-6 text-center text-sm text-base-content/40">
                      {search.trim() ? "Sin resultados para esa búsqueda" : "No hay quejosos disponibles"}
                    </div>
                  ) : (
                    <ul className="divide-y divide-base-300 max-h-48 overflow-y-auto">
                      {availableQuejosos.map((q) => (
                        <li
                          key={q.id}
                          className="flex items-center justify-between px-4 py-2.5 hover:bg-base-200 transition-colors"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-base-content truncate">{q.nombre}</p>
                            {(q.telefono || q.correo) && (
                              <p className="text-xs text-base-content/50 truncate">
                                {[q.telefono, q.correo].filter(Boolean).join(" · ")}
                              </p>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn btn-success btn-xs btn-outline ml-3 flex-shrink-0"
                            onClick={() => handleAdd(q.id)}
                            disabled={isDisabled || isCreating}
                          >
                            + Agregar
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Anónimo */}
          <div className="rounded-xl border border-base-300 bg-base-200/60 px-4 py-3 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-base-content">Quejoso anónimo</p>
              <p className="text-xs text-base-content/50 mt-0.5">
                Identidad reservada. Excluye vincular otras personas.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-warning btn-sm btn-outline flex-shrink-0"
              onClick={handleAddAnonimo}
              disabled={isDisabled || isCreating || hasAnonimoSelected || selectedIds.length > 0}
            >
              {hasAnonimoSelected ? "Ya agregado" : isCreating ? (
                <span className="loading loading-spinner loading-xs" />
              ) : selectedIds.length > 0 ? (
                "No aplica"
              ) : (
                "+ Anónimo"
              )}
            </button>
          </div>

          <div className="divider my-1">Crear nuevo quejoso</div>

          {/* Crear nuevo */}
          {hasAnonimoSelected ? (
            <div className="rounded-xl bg-warning/5 px-4 py-3 text-sm text-warning flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Con quejoso anónimo no se puede crear ni vincular nuevos quejosos.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  type="text"
                  className="input input-bordered input-sm"
                  placeholder="Nombre *"
                  value={newNombre}
                  onChange={(e) => setNewNombre(e.target.value)}
                  disabled={isDisabled || isCreating}
                />
                <input
                  type="tel"
                  className="input input-bordered input-sm"
                  placeholder="Teléfono"
                  value={newTelefono}
                  onChange={(e) => setNewTelefono(e.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  maxLength={10}
                  disabled={isDisabled || isCreating}
                />
                <input
                  type="email"
                  className="input input-bordered input-sm"
                  placeholder="Correo"
                  value={newCorreo}
                  onChange={(e) => setNewCorreo(e.target.value)}
                  disabled={isDisabled || isCreating}
                />
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  className="btn btn-success btn-sm text-white"
                  onClick={handleCreate}
                  disabled={isDisabled || isCreating}
                >
                  {isCreating ? (
                    <>
                      <span className="loading loading-spinner loading-xs" />
                      Creando...
                    </>
                  ) : (
                    "Crear quejoso"
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 px-6 py-3 border-t border-base-300 flex justify-end">
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={onClose}
            disabled={isDisabled || isCreating}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
