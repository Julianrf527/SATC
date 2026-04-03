import React from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { API_CONFIG } from "../../../utils/api";
import DetalleInfraccion from "./DetalleInfraccion";
import type { Expediente } from "../../../types/infraccionApp";
import type { Involucrado } from "../../../types/involucradoApp";

const mockMunicipios = [
  {
    id: 1,
    nombre: "Pasto",
    veredas: [{ id: 11, nombre: "Catambuco" }],
  },
];

const mockResources = [
  { id: 1, nombre: "Agua" },
  { id: 2, nombre: "Suelo" },
];

const mockInvolucrados: Involucrado[] = [
  {
    id: 1,
    nombre: "Juan Perez",
    numero_documento: 12345678,
    tipo_documento: "CC",
    celular: 3001234567,
    correo: "juan.perez@example.com",
  },
];

const mockExpediente: Expediente = {
  id: 1001,
  radicado: "2026-0001",
  fecha_radicado: "2026-01-10",
  direccion: "Vereda Catambuco",
  municipio: { id: 1, nombre: "Pasto" },
  fecha_creacion: "2026-01-10",
  involucrados: mockInvolucrados,
  ultima_etapa: "Respuesta",
  archivado: false,
};

const jsonResponse = (payload: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );

const installApiMock = () => {
  const fetchMock: typeof window.fetch = async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url.includes(API_CONFIG.ENDPOINTS.INFRACTION_FUll(1001))) {
      return jsonResponse({
        data: {
          direccion: "Vereda Catambuco",
          vereda: { id: 11, nombre: "Catambuco" },
          ultima_etapa: "Respuesta",
          recurso_afectado: [{ id: 1, nombre: "Agua" }],
          involucrados: mockExpediente.involucrados,
        },
        tipo_notificacion: { id: 1, nombre: "Personal" },
        etapas_existentes: [1, 2, 3],
      });
    }

    return jsonResponse({ data: [] });
  };

  window.fetch = fetchMock;
};

const meta = {
  title: "app-infracciones/Manage/DetalleInfraccion",
  component: DetalleInfraccion,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => {
      installApiMock();
      return <Story />;
    },
  ],
  args: {
    setToast: fn(),
    onUpdate: fn(),
    onArchiveSuccess: fn(),
    municipioList: mockMunicipios,
    recursoAfectadoList: mockResources,
    causaList: [{ id: 1, nombre: "Vertimiento" }],
  },
} satisfies Meta<typeof DetalleInfraccion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SinExpediente: Story = {
  args: {
    expedienteList: null,
    isEditable: true,
  },
};

export const ConExpedienteEditable: Story = {
  args: {
    expedienteList: mockExpediente,
    isEditable: true,
  },
};

export const ConExpedienteSoloLectura: Story = {
  args: {
    expedienteList: mockExpediente,
    isEditable: false,
  },
};
