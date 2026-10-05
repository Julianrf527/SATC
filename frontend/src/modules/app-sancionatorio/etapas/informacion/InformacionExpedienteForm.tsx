import type { ExpedienteDetalle } from "@shared/types/sancionatorio";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import CustomSelect from "@shared/ui/form/CustomSelect";
import AccionesFormulario from "../comun/AccionesFormulario";

type Props = {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  veredaList: ModeloGenerico[];
  recursoAfectadoList: ModeloGenerico[];
  municipioId: number;
  veredaId: number;
  recursosSeleccionados: number[];
  onMunicipioChange: (id: number) => void;
  onVeredaChange: (id: number) => void;
  onRecursoToggle: (id: number) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  isLoading: boolean;
};

/** Formulario de edición de los datos básicos del expediente. */
export default function InformacionExpedienteForm({
  expediente,
  municipioList,
  veredaList,
  recursoAfectadoList,
  municipioId,
  veredaId,
  recursosSeleccionados,
  onMunicipioChange,
  onVeredaChange,
  onRecursoToggle,
  onSubmit,
  onCancel,
  isLoading,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Radicado</span>
          </label>
          <input
            type="text"
            name="radicado"
            defaultValue={expediente.radicado}
            className="input w-full"
            required
            disabled={isLoading}
            pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
            title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
          />
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Expediente</span>
          </label>
          <input
            type="text"
            name="nombre"
            defaultValue={expediente.expediente}
            className="input w-full"
            required
            disabled={isLoading}
            pattern="^Q\d{3}-\d{2}$"
            title="Debe tener el formato: Q + 3 números + - + 2 números (ej: Q123-45)"
          />
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Municipio</span>
          </label>
          <CustomSelect
            value={municipioId}
            onChange={onMunicipioChange}
            placeholder="Seleccione un municipio"
            disabled={isLoading}
            options={municipioList.map((m) => ({ value: m.id, label: m.nombre }))}
          />
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Vereda</span>
          </label>
          <CustomSelect
            value={veredaId}
            onChange={onVeredaChange}
            placeholder="Seleccione una vereda"
            disabled={isLoading}
            options={veredaList.map((v) => ({ value: v.id, label: v.nombre }))}
          />
        </div>
      </div>

      <div className="flex flex-col">
        <label className="label">
          <span className="text-sm text-base-content font-medium">Recursos Afectados</span>
        </label>
        <div className="bg-base-200 rounded-lg p-4 border border-base-300">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recursoAfectadoList.map((r) => (
              <label
                key={r.id}
                className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success/50 cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  value={r.id}
                  checked={recursosSeleccionados.includes(r.id)}
                  onChange={() => onRecursoToggle(r.id)}
                  className="checkbox checkbox-success checkbox-sm"
                  disabled={isLoading}
                />
                <span className="text-sm font-medium">{r.nombre}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-col">
        <label className="label">
          <span className="text-sm text-base-content font-medium">Dirección</span>
        </label>
        <input
          type="text"
          name="direccion"
          defaultValue={expediente.direccion}
          className="input w-full"
          required
          disabled={isLoading}
          maxLength={100}
        />
      </div>

      <div className="flex flex-col">
        <label className="label">
          <span className="text-sm text-base-content font-medium">Motivo de Afectación</span>
        </label>
        <textarea
          name="motivo"
          defaultValue={expediente.motivo_afectacion || ""}
          rows={3}
          className="textarea resize-none w-full"
          required
          disabled={isLoading}
          maxLength={200}
        />
      </div>

      <AccionesFormulario
        onCancelar={onCancel}
        textoGuardar="Guardar Cambios"
        tono="success"
        guardando={isLoading}
      />
    </form>
  );
}
