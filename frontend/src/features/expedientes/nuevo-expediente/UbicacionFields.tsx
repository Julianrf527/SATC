import CustomSelect from "@shared/ui/form/CustomSelect";
import { Campo } from "@shared/ui/form/Campo";
import type { Municipio } from "@shared/types/common";
import type { UbicacionState } from "./useUbicacion";

type Props = {
  municipioList: Municipio[];
  ubicacion: UbicacionState;
  disabled?: boolean;
};

/** Municipio → Vereda → Dirección (input `name="direccion"`). */
export default function UbicacionFields({ municipioList, ubicacion, disabled = false }: Props) {
  const { municipioId, veredaId, veredas, seleccionarMunicipio, setVeredaId } = ubicacion;

  return (
    <>
      <Campo etiqueta="Municipio *">
        <CustomSelect
          value={municipioId}
          onChange={seleccionarMunicipio}
          placeholder="Seleccione un municipio"
          disabled={disabled}
          options={municipioList.map((m) => ({ value: m.id, label: m.nombre }))}
        />
      </Campo>

      <Campo etiqueta="Vereda *">
        <CustomSelect
          value={veredaId}
          onChange={setVeredaId}
          placeholder={
            veredas.length === 0 ? "Seleccione primero un municipio" : "Seleccione una vereda"
          }
          disabled={disabled || veredas.length === 0}
          options={veredas.map((v) => ({ value: v.id, label: v.nombre }))}
        />
      </Campo>

      <Campo etiqueta="Dirección *">
        <input
          type="text"
          name="direccion"
          placeholder="Dirección del predio"
          className="input w-full"
          required
          disabled={disabled}
          maxLength={100}
        />
      </Campo>
    </>
  );
}
