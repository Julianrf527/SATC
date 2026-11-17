import { useState } from "react";
import type { ModeloGenerico, Municipio } from "@shared/types/common";

/** Selección municipio/vereda del alta: las veredas salen del municipio elegido. */
export function useUbicacion(municipioList: Municipio[]) {
  const [municipioId, setMunicipioId] = useState(0);
  const [veredaId, setVeredaId] = useState(0);
  const [veredas, setVeredas] = useState<ModeloGenerico[]>([]);

  const seleccionarMunicipio = (id: number) => {
    setMunicipioId(id);
    setVeredaId(0);
    setVeredas(municipioList.find((m) => m.id === id)?.veredas ?? []);
  };

  const reset = () => {
    setMunicipioId(0);
    setVeredaId(0);
    setVeredas([]);
  };

  const municipio = municipioList.find((m) => m.id === municipioId);
  const vereda = municipio?.veredas.find((v) => v.id === veredaId);

  return { municipioId, veredaId, veredas, municipio, vereda, seleccionarMunicipio, setVeredaId, reset };
}

export type UbicacionState = ReturnType<typeof useUbicacion>;
