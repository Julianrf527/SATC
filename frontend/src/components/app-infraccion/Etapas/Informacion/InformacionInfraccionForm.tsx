import type { Quejoso, TipoAfectacion } from "../../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../../types/common";
import type { InformacionInfraccionFormState } from "./useInformacionInfraccionForm";
import CustomSelect from "../../../Common/Form/CustomSelect";
import CustomDateInput from "../../../Common/Form/CustomDateInput";

interface Props {
  form: InformacionInfraccionFormState;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  onOpenQuejosoModal: () => void;
}

export default function InformacionInfraccionForm({
  form,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  onOpenQuejosoModal,
}: Props) {
  const {
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
    radicadosAsociados,
    veredaList,
    handleResourceToggle,
    handleToggleExpand,
    handleTipoToggle,
    handleAddRadicado,
    handleRemoveRadicado,
    handleChangeRadicadoAsociado,
    handleSubmit,
    handleCancel,
  } = form;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Radicado *</span>
          </label>
          <input
            className="input input-bordered w-full"
            value={radicado}
            onChange={(e) => setRadicado(e.target.value.toUpperCase())}
            maxLength={15}
            required
            pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
            title="Debe tener el formato: 4 numeros + IE o EE o ER + 4 o 5 numeros (ej: 2015IE5678)"
            disabled={isLoading}
          />
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Fecha radicado *</span>
          </label>
          <CustomDateInput
            value={fechaRadicado}
            onChange={setFechaRadicado}
            max={new Date().toISOString().split('T')[0]}
            disabled={isLoading}
          />
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Municipio *</span>
          </label>
          <CustomSelect
            value={municipioId || 0}
            onChange={(v) => {
              setMunicipioId(v);
              setVeredaId(0);
            }}
            placeholder="Seleccione un municipio"
            disabled={isLoading}
            options={municipioList.map((m) => ({ value: m.id, label: m.nombre }))}
          />
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Vereda *</span>
          </label>
          <CustomSelect
            value={veredaId || 0}
            onChange={setVeredaId}
            placeholder={veredaList.length === 0 ? "Seleccione primero un municipio" : "Seleccione una vereda"}
            disabled={isLoading || veredaList.length === 0}
            options={veredaList.map((v) => ({ value: v.id, label: v.nombre }))}
          />
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Direccion *</span>
          </label>
          <input
            className="input input-bordered w-full"
            value={direccion}
            onChange={(e) => setDireccion(e.target.value)}
            maxLength={100}
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-control md:col-span-2">
          <label className="label">
            <span className="label-text font-medium">Quejoso *</span>
          </label>
          <div className="bg-base-200 rounded-lg p-4 border border-base-300">
            <div className="space-y-3">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={onOpenQuejosoModal}
                disabled={isLoading}
              >
                Seleccionar o crear quejoso
              </button>
              {quejososIds.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {quejosoList
                    .filter((q) => quejososIds.includes(q.id))
                    .map((q) => (
                      <span key={q.id} className="badge badge-success badge-outline p-3">
                        {q.anonimo ? "Anónimo" : (q.nombre ?? "Sin nombre")}
                      </span>
                    ))}
                </div>
              ) : (
                <p className="text-sm text-base-content/60">No hay quejosos seleccionados</p>
              )}
            </div>
          </div>
        </div>

        <div className="form-control md:col-span-2">
          <label className="label">
            <span className="label-text font-medium">Radicados asociados</span>
          </label>
          <div className="space-y-2">
            {radicadosAsociados.map((item, index) => (
              <div key={index} className="flex gap-2">
                <input
                  className="input input-bordered w-full"
                  value={item}
                  onChange={(e) => handleChangeRadicadoAsociado(index, e.target.value)}
                  maxLength={15}
                  pattern="^$|^\d{4}(IE|EE|ER)\d{4,5}$"
                  title="Debe tener el formato: 4 numeros + IE o EE o ER + 4 o 5 numeros (ej: 2015IE5678)"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="btn btn-outline btn-error"
                  onClick={() => handleRemoveRadicado(index)}
                  disabled={isLoading}
                >
                  <i className="bx bx-trash"></i>
                </button>
              </div>
            ))}
          </div>
          <div className="mt-2">
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={handleAddRadicado}
              disabled={isLoading}
            >
              + Agregar radicado
            </button>
          </div>
        </div>

        <div className="form-control md:col-span-2">
          <label className="label">
            <span className="label-text font-medium">Recursos Afectados *</span>
          </label>
          <div className="border border-base-300 rounded-lg overflow-hidden divide-y divide-base-300">
            {recursoAfectadoList.map((r) => {
              const isSelected = recursosIds.includes(r.id);
              const isExpanded = expandedRecursos.includes(r.id);
              const tipos = tipoAfectacionList.filter((t) => t.recurso_id === r.id);
              return (
                <div key={r.id}>
                  <div
                    className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                      isSelected ? "bg-success/5" : "bg-base-100 hover:bg-base-200"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleResourceToggle(r.id)}
                      className="checkbox checkbox-success checkbox-sm flex-shrink-0"
                      disabled={isLoading}
                    />
                    <span
                      className="flex-1 text-sm font-semibold text-base-content cursor-pointer select-none"
                      onClick={() => handleResourceToggle(r.id)}
                    >
                      {r.nombre}
                    </span>
                    {tipos.length > 0 && (
                      <button
                        type="button"
                        onClick={() => handleToggleExpand(r.id)}
                        className="btn btn-ghost btn-xs btn-circle"
                        disabled={isLoading}
                      >
                        <svg
                          className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    )}
                  </div>
                  {isExpanded && tipos.length > 0 && (
                    <div className="bg-base-200/50 border-t border-base-300 px-4 py-2 space-y-0.5">
                      {tipos.map((tipo) => (
                        <label
                          key={tipo.id}
                          className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                            isSelected ? "hover:bg-base-200" : "opacity-40 cursor-not-allowed"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={tiposIds.includes(tipo.id)}
                            onChange={() => handleTipoToggle(tipo.id)}
                            className="checkbox checkbox-success checkbox-xs flex-shrink-0"
                            disabled={isLoading || !isSelected}
                          />
                          <span className="text-sm text-base-content">{tipo.nombre}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="form-control md:col-span-2">
          <label className="label">
            <span className="label-text font-medium">Descripcion *</span>
          </label>
          <textarea
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            rows={3}
            className="textarea textarea-bordered resize-none w-full"
            required
            disabled={isLoading}
            maxLength={300}
          />
        </div>
      </div>

      <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
        <button
          type="button"
          onClick={handleCancel}
          className="btn btn-outline"
          disabled={isLoading}
        >
          Cancelar
        </button>
        <button
          type="submit"
          className="btn btn-success text-white gap-2"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="loading loading-spinner loading-sm"></span>
              Guardando...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Guardar Cambios
            </>
          )}
        </button>
      </div>
    </form>
  );
}
