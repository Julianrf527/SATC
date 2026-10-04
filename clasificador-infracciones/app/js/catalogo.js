// Catálogo de documentos esperados por etapa del proceso de infracciones.
// Abstraído de app-infraction (backend + frontend real). Es solo una
// plantilla inicial: cada fila se puede duplicar, renombrar o borrar en la UI.
// Este archivo no se conecta ni depende del sistema SATC.

const CATALOGO_ETAPAS = [
  {
    id: "etapa_visita",
    label: "Visita Técnica",
    documentos: ["Informe Técnico de Visita"],
  },
  {
    id: "etapa_seguimiento",
    label: "Seguimiento",
    documentos: ["Informe Técnico de Seguimiento"],
  },
  {
    id: "etapa_concepto",
    label: "Concepto",
    documentos: [
      "Solicitud de Información",
      "Acto Administrativo (AUTO Requerimiento)",
      "Notificación - Citación",
      "Notificación - Constancia",
      "Comunicación",
      "Oficio de Remisión",
    ],
  },
  {
    id: "etapa_respuesta",
    label: "Respuesta",
    documentos: [
      "Documento Radicado SIAF",
      "Acto Administrativo Medida Preventiva",
      "Comunicación Medida Preventiva",
    ],
  },
  {
    id: "etapa_cierre",
    label: "Cierre",
    documentos: [
      "Acto Administrativo de Cierre",
      "Notificación - Citación",
      "Notificación - Constancia",
    ],
  },
];

export { CATALOGO_ETAPAS };
