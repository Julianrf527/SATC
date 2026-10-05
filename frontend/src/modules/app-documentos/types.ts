// Tipos del módulo app-documentos. El detalle del proceso (versiones,
// revisiones, acciones...) usa el contrato genérico `ProcesoDetalle` de
// @features/proceso-revision; aquí solo lo propio del listado y la creación.
import type { EstadoProceso } from "@features/proceso-revision";

export type Toast = { id: number; message: string; type: "success" | "error" };
export type SetToast = (toast: Toast) => void;

/** Fila de /docs/list (`estado` con la misma forma que en el detalle). */
export type DocumentoResumen = {
  id: number;
  nombre: string;
  descripcion: string | null;
  estado: EstadoProceso;
  fecha_creacion: string;
  fecha_ultima_actualizacion: string;
  version_actual: number | null;
  numero_devoluciones: number;
  creador_id: number;
  total_revisiones: number;
  total_revisores: number;
};

export type ListaDocumentos = {
  documentos: DocumentoResumen[];
  /** Catálogo de estados del flujo (opciones del filtro). */
  estados: EstadoProceso[];
  total: number;
  total_pages: number;
  page: number;
  page_size: number;
};

export type FiltrosDocumentos = {
  estado: string;
  fechaDesde: string;
  fechaHasta: string;
};

export type EstadisticasDocumentos = {
  creador?: {
    total_creados: number;
    en_revision: number;
    aprobados: number;
    rechazados: number;
    finalizados: number;
  };
  revisor?: {
    total_asignados: number;
    pendientes: number;
    total_revisiones: number;
    aprobados: number;
    devueltos: number;
  };
};

/** Usuario de /docs/reviewers. */
export type RevisorDisponible = {
  id: number;
  nombre_completo: string;
  email: string;
};

export type TipoArchivo = "pdf" | "docx" | "doc";

export type CrearDocumentoDatos = {
  nombre: string;
  descripcion: string;
  tipo_archivo: TipoArchivo;
  revisores_ids: number[];
  archivo: File;
};
