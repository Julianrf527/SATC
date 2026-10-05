export type FiltrosUsuarios = {
  documento: string;
  nombre: string;
  correo: string;
  /** "all" o id del rol. */
  rol: string;
  /** "all" | "active" | "inactive" */
  estado: string;
};

export const FILTROS_VACIOS: FiltrosUsuarios = {
  documento: "",
  nombre: "",
  correo: "",
  rol: "all",
  estado: "all",
};

export const hayFiltrosActivos = (f: FiltrosUsuarios) =>
  f.documento.trim() !== "" ||
  f.nombre.trim() !== "" ||
  f.correo.trim() !== "" ||
  f.rol !== "all" ||
  f.estado !== "all";
