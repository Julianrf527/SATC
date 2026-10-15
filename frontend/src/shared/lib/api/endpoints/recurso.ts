// Endpoints del servicio app-recurso (Concesiones de Aguas Superficiales, /recurso).
// Contrato: app-recurso/API.md (secciones A, B y C). Strings fijos o funciones que
// construyen la ruta; se concatenan a BASE_URL en apiCall.
//
// Ojo: las rutas SPA (/recurso/manage, /recurso/consult, /recurso/my-reports)
// comparten prefijo con la API; nginx las distingue (frontend/nginx.conf).
export const RECURSO_ENDPOINTS = {
  // === A.1 Catálogos (lectura) ===
  RECURSO_CATALOGOS: "/recurso/catalogos",
  RECURSO_CATALOGO_MUNICIPIOS: "/recurso/catalogos/municipios",
  RECURSO_CATALOGO_TIPOS_FUENTE: "/recurso/catalogos/tipos-fuente",
  RECURSO_CATALOGO_FUENTES: "/recurso/catalogos/fuentes",
  RECURSO_CATALOGO_USOS: "/recurso/catalogos/usos",
  RECURSO_CATALOGO_TIPOS_NOTIFICACION: "/recurso/catalogos/tipos-notificacion",

  // === A.2 / A.3 Expedientes ===
  /** GET listado paginado (query: page, limit, radicado, expediente, numero_vital, municipio_id, vereda_id, involucrado_id) · POST crear. */
  RECURSO_EXPEDIENTES: "/recurso/expedientes",
  /** GET detalle (información base + involucrados + etapas) · PUT editar (con `version`). */
  RECURSO_EXPEDIENTE: (expedienteId: number) => `/recurso/expedientes/${expedienteId}`,

  // === A.4 Solicitantes (vínculos con app-involved) ===
  RECURSO_INVOLUCRADOS_EXPEDIENTE: (expedienteId: number, tipoVinculo?: string) =>
    `/recurso/involucrados/expediente/${expedienteId}${tipoVinculo ? `?tipo_vinculo=${tipoVinculo}` : ""}`,
  RECURSO_VINCULOS: "/recurso/involucrados/vinculos",
  RECURSO_VINCULO_REPRESENTANTE: (vinculoId: number) =>
    `/recurso/involucrados/vinculos/${vinculoId}/representante`,
  RECURSO_VINCULO_DELETE: (vinculoId: number, version: number) =>
    `/recurso/involucrados/vinculos/${vinculoId}?version=${version}`,

  // === A.5 Descarga del expediente completo ===
  RECURSO_EXPEDIENTE_DOCUMENTOS: (expedienteId: number) =>
    `/recurso/expedientes/${expedienteId}/documentos`,
  RECURSO_EXPEDIENTE_DESCARGAR: (expedienteId: number) =>
    `/recurso/expedientes/${expedienteId}/descargar`,

  // === B.1 Revisión de documentos ===
  RECURSO_REVISION_DETALLE: (procesoId: number) => `/recurso/revision-documentos/${procesoId}`,
  RECURSO_REVISION_POR_ETAPA: (etapaTipo: string, etapaRefId: number) =>
    `/recurso/revision-documentos/por-etapa/${etapaTipo}/${etapaRefId}`,
  RECURSO_REVISION_VERSIONES: (procesoId: number) =>
    `/recurso/revision-documentos/${procesoId}/versiones`,
  RECURSO_REVISION_REVISAR: (procesoId: number) =>
    `/recurso/revision-documentos/${procesoId}/revisiones`,
  RECURSO_REVISION_HISTORIAL: (procesoId: number) =>
    `/recurso/revision-documentos/${procesoId}/historial`,
  RECURSO_REVISION_AUDITORIA: (procesoId: number) =>
    `/recurso/revision-documentos/${procesoId}/auditoria`,
  RECURSO_REVISION_DESCARGA_VERSION: (procesoId: number, versionId: number) =>
    `/recurso/revision-documentos/${procesoId}/versiones/${versionId}/descarga`,
  RECURSO_REVISION_ADJUNTO: (procesoId: number, revisionId: number) =>
    `/recurso/revision-documentos/${procesoId}/revisiones/${revisionId}/adjunto`,

  // === B.2 Mis informes ===
  /** GET (query: vista, expediente, tipo_documento, estado). */
  RECURSO_MIS_DOCUMENTOS: "/recurso/mis-documentos",

  // === B.3 Actos, comunicación y notificación (para @features/acto-administrativo) ===
  RECURSO_TIPOS_NOTIFICACION: "/recurso/actos/tipos-notificacion",
  /** No existe en el backend: el acto lo crea la etapa ("Cargar versión final", sección C). */
  RECURSO_ACTO_ADMIN: "/recurso/actos/administrativos",
  RECURSO_ACTO_ADMIN_DETALLE: (actoId: number) => `/recurso/actos/administrativos/${actoId}`,
  RECURSO_ACTO_ADMIN_UPDATE: (actoId: number) => `/recurso/actos/administrativos/${actoId}`,
  RECURSO_ACTO_ADMIN_DELETE: (actoId: number) => `/recurso/actos/administrativos/${actoId}`,
  RECURSO_COMUNICACION: "/recurso/actos/comunicaciones",
  RECURSO_COMUNICACION_UPDATE: (id: number) => `/recurso/actos/comunicaciones/${id}`,
  RECURSO_COMUNICACION_DELETE: (id: number) => `/recurso/actos/comunicaciones/${id}`,
  RECURSO_NOTIFICACION: "/recurso/actos/notificaciones",
  RECURSO_NOTIFICACION_UPDATE: (id: number) => `/recurso/actos/notificaciones/${id}`,
  RECURSO_NOTIFICACION_DELETE: (id: number) => `/recurso/actos/notificaciones/${id}`,

  // === Etapas (F2) ===
  // Sección C de app-recurso/API.md (prefijos del backend: /recurso/etapas,
  // /recurso/terceros, /recurso/documentos-anexos, /recurso/super-gestion).
  /** GET árbol de etapas (C.2; también llega en `etapas` de GET /expedientes/{id}). */
  RECURSO_ETAPAS: (expedienteId: number) => `/recurso/etapas/${expedienteId}`,
  /**
   * Acción de una etapa (C.3–C.8): `ruta` relativa al expediente, p. ej.
   * `admite/asignarme`, `conceptos/memorias/tecnico`, `requerimientos/etapa3/respuesta`,
   * `decision/ejecutoria`, `recurso/version-final`, `memorias/subsanacion`, `obras/nuevo-informe`.
   */
  RECURSO_ETAPA_ACCION: (expedienteId: number, ruta: string) => `/recurso/etapas/${expedienteId}/${ruta}`,
  /** GET técnicos seleccionables (usuarios con `recurso_tecnico`, C.4). */
  RECURSO_ETAPAS_TECNICOS: "/recurso/etapas/tecnicos",
  /** GET abogados (usuarios con `recurso_gestionar`): encargado en el cargue directo (C.9). */
  RECURSO_ETAPAS_ABOGADOS: "/recurso/etapas/abogados",
  /** GET concepto para el técnico desde Mis informes (C.4). */
  RECURSO_CONCEPTO: (conceptoId: number) => `/recurso/etapas/conceptos/${conceptoId}`,
  /** POST versión final del concepto por id (técnico, desde Mis informes). */
  RECURSO_CONCEPTO_VERSION_FINAL: (conceptoId: number) => `/recurso/etapas/conceptos/${conceptoId}/version-final`,
  // C.9 Super gestión (cargue directo). `ruta`: admite, conceptos/{tipo},
  // requerimientos/{ambito}, decision, recurso, memorias, memorias/subsanacion,
  // obras, obras/nuevo-informe.
  RECURSO_SUPER_GESTION: (expedienteId: number, ruta: string) => `/recurso/super-gestion/${expedienteId}/${ruta}`,
  RECURSO_SUPER_GESTION_TERCERO_ACTO: (vinculoId: number) => `/recurso/super-gestion/terceros/${vinculoId}/acto`,
  // C.10 Tercero interviniente
  RECURSO_TERCEROS: "/recurso/terceros",
  RECURSO_TERCERO_REPRESENTANTE: (vinculoId: number) => `/recurso/terceros/${vinculoId}/representante`,
  RECURSO_TERCERO_DELETE: (vinculoId: number, version: number) => `/recurso/terceros/${vinculoId}?version=${version}`,
  RECURSO_TERCERO_ASIGNARME: (vinculoId: number) => `/recurso/terceros/${vinculoId}/asignarme`,
  RECURSO_TERCERO_VERSION_FINAL: (vinculoId: number) => `/recurso/terceros/${vinculoId}/version-final`,
  // C.11 Documentos anexos
  RECURSO_ANEXOS: "/recurso/documentos-anexos",
  RECURSO_ANEXO: (anexoId: number) => `/recurso/documentos-anexos/${anexoId}`,
  RECURSO_ANEXO_DELETE: (anexoId: number, expedienteId: number) =>
    `/recurso/documentos-anexos/${anexoId}?expediente_id=${expedienteId}`,
};
