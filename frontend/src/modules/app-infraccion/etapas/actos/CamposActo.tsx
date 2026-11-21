import { CampoFecha, CampoOpciones, CampoPdf, CampoTexto } from "../campos/Campos";
import type { DatosActo, TipoActo } from "./datosActo";

const OPCIONES_TIPO: { value: TipoActo; label: string }[] = [
  { value: "AUTO", label: "AUTO" },
  { value: "RES", label: "RES" },
];

type Props = {
  datos: DatosActo;
  cambiar: (cambio: Partial<DatosActo>) => void;
};

/**
 * Campos del acto firmado, como la sección "Acto administrativo firmado" del
 * cargue directo de recurso: PDF, tipo y numerado en dos columnas, fecha. Los
 * usan "Cargar versión final" y el cargue directo de super gestión.
 */
export default function CamposActo({ datos, cambiar }: Props) {
  return (
    <>
      <CampoPdf
        etiqueta="Acto firmado y numerado (PDF)"
        archivo={datos.archivo}
        onChange={(archivo) => cambiar({ archivo })}
        requerido
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CampoOpciones
          etiqueta="Tipo de acto"
          valor={datos.tipoActo}
          opciones={OPCIONES_TIPO}
          onChange={(v) => cambiar({ tipoActo: v || "AUTO" })}
          requerido
        />
        <CampoTexto
          etiqueta="Numerado"
          valor={datos.numerado}
          onChange={(v) => cambiar({ numerado: v.replace(/\D/g, "").slice(0, 4) })}
          inputMode="numeric"
          placeholder="0012"
          requerido
        />
      </div>
      <CampoFecha etiqueta="Fecha de numerado" valor={datos.fecha} onChange={(fecha) => cambiar({ fecha })} requerido />
    </>
  );
}
