import React from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { API_CONFIG } from "../../../utils/api";
import Informacion from "./InformacionInfraccion";

const mockMunicipios = [
  {
    id: 1,
    nombre: "Pasto",
    veredas: [
      { id: 11, nombre: "Catambuco" },
      { id: 12, nombre: "Jamondino" },
    ],
  },
];

const mockRecursos = [
  { id: 1, nombre: "Agua" },
  { id: 2, nombre: "Suelo" },
];

const mockCausas = [
  { id: 1, nombre: "Vertimiento" },
  { id: 2, nombre: "Tala" },
];

const mockQuejosos = [
  {
    id: 101,
    nombre: "Ana Ruiz",
    telefonmo: 3001234567,
    correo: "ana@example.com",
  },
  {
    id: 102,
    nombre: "Carlos Mora",
    telefonmo: 3011234567,
    correo: "carlos@example.com",
  },
];

const mockExpediente = {
  id: 1001,
  radicado: "2026IE1234",
  fecha_radicado: "2026-04-01",
  municipio: { id: 1, nombre: "Pasto" },
  vereda: { id: 11, nombre: "Catambuco" },
  direccion: "Vereda Catambuco, sector alto",
  descripcion: "Descripción inicial del expediente de infracción.",
  causa: { id: 1, nombre: "Vertimiento" },
  recurso_afectado: [
    { id: 1, nombre: "Agua" },
    { id: 2, nombre: "Suelo" },
  ],
  quejosos: [
    { id: 101, nombre: "Ana Ruiz" },
    { id: 102, nombre: "Carlos Mora" },
  ],
  radicados_asociados: ["2025IE9876", "2024EE1001"],
  fecha_creacion: "2026-04-01T10:00:00Z",
  involucrados: [],
  etapa_actual: "informacion",
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

    if (
      url.includes("/infractions/file/") &&
      input instanceof Request &&
      input.method === "PUT"
    ) {
      return jsonResponse({ ok: true, message: "Actualizado" });
    }

    if (url.includes(API_CONFIG.ENDPOINTS.INFRACTION_BASIC_DATA(1001))) {
      return jsonResponse({ ok: true, message: "Actualizado" });
    }

    return jsonResponse({ ok: true });
  };

  window.fetch = fetchMock;
};

const meta = {
  title: "app-infracciones/Stages/Informacion",
  component: Informacion,
  parameters: { layout: "padded" },
  decorators: [
    (Story) => {
      installApiMock();
      return <Story />;
    },
  ],
  args: {
    expediente: mockExpediente,
    municipioList: mockMunicipios,
    recursoAfectadoList: mockRecursos,
    causaList: mockCausas,
    quejosoList: mockQuejosos,
    setToast: fn(),
    onUpdate: fn(),
    isEditable: true,
  },
} satisfies Meta<typeof Informacion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const SoloLectura: Story = {
  args: {
    isEditable: false,
  },
};
