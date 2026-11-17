import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ProcesoAdapter } from "./adapter";
import { ProcesoDetalleModal } from "./ProcesoDetalleModal";
import type { AccionDisponible, ProcesoDetalle, SubidaVersion } from "./types";

// Adapter en memoria: no toca la red. Cada historia arma el detalle que vería
// un usuario concreto (las acciones las "calcula" el backend, aquí el mock).

const base: ProcesoDetalle = {
  id: 1,
  nombre: "Contrato de servicios 2026",
  descripcion: "Contrato marco para el área de gestión ambiental.",
  estado: { codigo: "en_revision", etiqueta: "En revisión", tono: "info" },
  version_actual: 2,
  numero_devoluciones: 1,
  max_devoluciones: 3,
  creador_id: 10,
  fecha_creacion: "2026-09-01T10:00:00",
  fecha_ultima_actualizacion: "2026-09-03T09:00:00",
  revisores: [{ revisor_id: 20, nombre: "Ana Ruiz", fecha_asignacion: "2026-09-01T10:00:00", notificado: true }],
  versiones: [
    {
      version_id: 2,
      numero_version: 2,
      archivo: { file_id: 2, url: "x", nombre: "contrato_v2.docx", size: 48_000 },
      usuario_subida_id: 10,
      comentario: "Corregidas las cláusulas 3 y 4",
      fecha_subida: "2026-09-03T09:00:00",
    },
    {
      version_id: 1,
      numero_version: 1,
      archivo: { file_id: 1, url: "x", nombre: "contrato_v1.pdf", size: 120_000 },
      usuario_subida_id: 10,
      comentario: "Versión inicial",
      fecha_subida: "2026-09-01T10:00:00",
    },
  ],
  revisiones: [
    {
      revision_id: 1,
      revisor_id: 20,
      revisor_nombre: "Ana Ruiz",
      accion: "devuelto",
      accion_etiqueta: "Devuelto",
      tono: "warning",
      comentarios: "Faltan las firmas del anexo.",
      version_revisada: 1,
      fecha_revision: "2026-09-02T15:00:00",
      adjunto: { file_id: 3, url: "x", nombre: "observaciones.pdf", size: 9_000 },
    },
  ],
  auditoria: [
    {
      auditoria_id: 1, usuario_id: 10, accion: "crear", accion_etiqueta: "Proceso creado", tono: "info",
      descripcion: "Proceso creado: Contrato de servicios 2026", datos_adicionales: null, fecha_accion: "2026-09-01T10:00:00",
    },
    {
      auditoria_id: 2, usuario_id: 10, accion: "subir_version_inicial", accion_etiqueta: "Versión inicial cargada", tono: "info",
      descripcion: "Versión inicial cargada (v1)", datos_adicionales: null, fecha_accion: "2026-09-01T10:00:00",
    },
    {
      auditoria_id: 3, usuario_id: 20, accion: "devolver", accion_etiqueta: "Devuelto", tono: "warning",
      descripcion: "Devuelto, devoluciones 1/3", datos_adicionales: null, fecha_accion: "2026-09-02T15:00:00",
    },
    {
      auditoria_id: 4, usuario_id: 10, accion: "subir_version", accion_etiqueta: "Nueva versión subida", tono: "info",
      descripcion: "Nueva versión subida (v2)", datos_adicionales: null, fecha_accion: "2026-09-03T09:00:00",
    },
  ],
  acciones_disponibles: [],
  subida_version: null,
};

const adjuntoDevolucion = { permitido: true, extensiones: [".pdf", ".doc", ".docx"] };
const sinAdjunto = { permitido: false, extensiones: [] };

const accionesRevisor: AccionDisponible[] = [
  { codigo: "aprobado", etiqueta: "Aprobar", tono: "success", requiere_comentario: false, adjunto: sinAdjunto, bloqueada: null, icono: "aprobar" },
  { codigo: "devuelto", etiqueta: "Devolver", tono: "warning", requiere_comentario: true, adjunto: adjuntoDevolucion, bloqueada: null, icono: "devolver" },
];

const accionesConBloqueo: AccionDisponible[] = [
  {
    codigo: "aprobado",
    etiqueta: "Aprobar",
    tono: "success",
    requiere_comentario: false,
    adjunto: sinAdjunto,
    bloqueada: "La versión actual debe ser PDF para aprobar",
    icono: "aprobar",
  },
  { codigo: "aprobado_firma", etiqueta: "Aprobar para firma", tono: "success", requiere_comentario: false, adjunto: sinAdjunto, bloqueada: null, icono: "firmar" },
  { codigo: "devuelto", etiqueta: "Devolver", tono: "warning", requiere_comentario: true, adjunto: adjuntoDevolucion, bloqueada: null, icono: "devolver" },
];

const subidaCreador: SubidaVersion = { permitida: true, extensiones: [".pdf", ".doc", ".docx"], motivo: null };

function mockAdapter(detalle: ProcesoDetalle): ProcesoAdapter {
  const esperar = () => new Promise((r) => setTimeout(r, 500));
  return {
    queryKey: (id) => ["story-proceso", detalle.estado.codigo, detalle.acciones_disponibles.length, id],
    detalle: async () => detalle,
    revisar: async (_id, datos) => {
      await esperar();
      return { ok: true, message: `Acción "${datos.accion}" registrada (mock)` };
    },
    subirVersion: async (_id, datos) => {
      await esperar();
      return { ok: true, message: `Archivo ${datos.archivo.name} subido (mock)` };
    },
    urlVersion: (_id, v) => `/mock/version/${v.version_id}`,
    urlAdjunto: (_id, r) => `/mock/adjunto/${r.revision_id}`,
  };
}

function Demo({ detalle, extra }: { detalle: ProcesoDetalle; extra?: boolean }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  const [adapter] = useState(() => mockAdapter(detalle));
  const [open, setOpen] = useState(true);
  return (
    <QueryClientProvider client={client}>
      <div data-theme="emerald" className="p-6">
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          Abrir proceso
        </button>
        <ProcesoDetalleModal
          adapter={adapter}
          id={detalle.id}
          isOpen={open}
          onClose={() => setOpen(false)}
          extraHeader={extra ? <span className="badge badge-ghost">Expediente 2026-0001</span> : undefined}
          extraAcciones={extra ? <button className="btn btn-sm btn-outline">Acción del módulo</button> : undefined}
        />
      </div>
    </QueryClientProvider>
  );
}

const meta: Meta<typeof Demo> = {
  title: "Features/ProcesoRevision/ProcesoDetalleModal",
  component: Demo,
  parameters: { layout: "fullscreen" },
};
export default meta;
type Story = StoryObj<typeof Demo>;

/** El creador tras una devolución: puede subir versión (botón "Subir versión"). */
export const Creador: Story = {
  args: {
    detalle: {
      ...base,
      estado: { codigo: "rechazado", etiqueta: "Devuelto", tono: "warning" },
      subida_version: subidaCreador,
    },
  },
};

/** Revisor asignado con la versión en revisión: aprobar o devolver (con adjunto). */
export const Revisor: Story = {
  args: { detalle: { ...base, acciones_disponibles: accionesRevisor } },
};

/** Acción que aplica pero está bloqueada: se ve deshabilitada con su motivo. */
export const AccionBloqueada: Story = {
  args: { detalle: { ...base, acciones_disponibles: accionesConBloqueo }, extra: true },
};

/** Sin acciones: solo lectura, con el motivo de por qué no se puede subir. */
export const SoloLectura: Story = {
  args: {
    detalle: {
      ...base,
      estado: { codigo: "finalizado", etiqueta: "Finalizado", tono: "error" },
      subida_version: { permitida: false, extensiones: [], motivo: "El proceso alcanzó el máximo de devoluciones" },
    },
  },
};

/**
 * Flujo extendido (informe técnico): el historial y la auditoría muestran la
 * etiqueta en participio y el tono que define el flujo ("Aprobado para firma").
 */
export const FlujoExtendido: Story = {
  args: {
    detalle: {
      ...base,
      estado: { codigo: "aprobado_firma", etiqueta: "Aprobado para firma", tono: "warning" },
      revisiones: [
        {
          revision_id: 2,
          revisor_id: 20,
          revisor_nombre: "Ana Ruiz",
          accion: "aprobado_firma",
          accion_etiqueta: "Aprobado para firma",
          tono: "success",
          comentarios: "",
          version_revisada: 2,
          fecha_revision: "2026-09-04T11:00:00",
          adjunto: null,
        },
        ...base.revisiones,
      ],
      auditoria: [
        ...base.auditoria,
        {
          auditoria_id: 5, usuario_id: 20, accion: "aprobar_firma", accion_etiqueta: "Aprobado para firma", tono: "success",
          descripcion: "Aprobar para firma: estado Aprobado para firma", datos_adicionales: null, fecha_accion: "2026-09-04T11:00:00",
        },
      ],
      subida_version: { permitida: true, extensiones: [".pdf"], motivo: null },
    },
    extra: true,
  },
};
