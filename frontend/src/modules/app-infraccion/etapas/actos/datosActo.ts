export type TipoActo = "AUTO" | "RES";

export type DatosActo = {
  archivo: File | null;
  tipoActo: TipoActo;
  numerado: string;
  fecha: string;
};

export const DATOS_ACTO_VACIO: DatosActo = { archivo: null, tipoActo: "AUTO", numerado: "", fecha: "" };

export const hoy = () => new Date().toISOString().split("T")[0];

/** Mensaje de error de los datos del acto (o null si están completos). */
export function validarDatosActo(d: DatosActo): string | null {
  if (!d.archivo) return "Seleccione el acto firmado (PDF)";
  if (!/\.pdf$/i.test(d.archivo.name)) return "El acto firmado debe ser PDF";
  if (!/^\d{1,4}$/.test(d.numerado) || Number(d.numerado) === 0) return "El numerado debe tener entre 1 y 4 números";
  if (!d.fecha) return "Indique la fecha de numerado";
  if (d.fecha > hoy()) return "La fecha de numerado no puede ser futura";
  return null;
}
