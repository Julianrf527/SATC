import React from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { MemoryRouter } from "react-router-dom";
import AuthContext from "../../../context/AuthContext";
import { API_CONFIG } from "../../../utils/api";
import InfraccionLayout from "./GestionInfraccionLayout";

const mockUser = {
  user_id: 101,
  primer_nombre: "Ana",
  segundo_nombre: "Maria",
  primer_apellido: "Suarez",
  segundo_apellido: "Lopez",
  correo: "ana.suarez@satc.local",
  permisos: [{ name: "Gestion Infracciones", path: "/file/manage" }],
};

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
  { id: 2, nombre: "Ocupacion" },
];

const mockExpedientes = [
  {
    id: 1001,
    radicado: "2026-0001",
    fecha_radicado: "2026-01-10",
    direccion: "Vereda Catambuco",
    municipio: { id: 1, nombre: "Pasto" },
    fecha_creacion: "2026-01-10",
    involucrados: [
      {
        id: 1,
        nombre: "Juan Perez",
        numero_documento: "12345678",
      },
    ],
    ultima_etapa: "Respuesta",
    archivado: false,
  },
];

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

    if (url.includes(API_CONFIG.ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT)) {
      return jsonResponse({ data: mockMunicipios });
    }

    if (url.includes(API_CONFIG.ENDPOINTS.INFRACTION_AFFECTED_RESOURCE)) {
      return jsonResponse({ data: mockRecursos });
    }

    if (url.includes(API_CONFIG.ENDPOINTS.INFRACTION_CAUSES)) {
      return jsonResponse({ data: mockCausas });
    }

    if (url.includes("/sanctioning/file/")) {
      return jsonResponse({ data: mockExpedientes });
    }

    if (url.includes("/infractions/file/full/")) {
      return jsonResponse({
        data: {
          direccion: "Vereda Catambuco",
          vereda: { id: 11, nombre: "Catambuco" },
          ultima_etapa: "Respuesta",
          recurso_afectado: [{ id: 1, nombre: "Agua" }],
          involucrados: mockExpedientes[0].involucrados,
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
  title: "app-infracciones/Layout/InfraccionLayout",
  component: InfraccionLayout,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => {
      installApiMock();

      return (
        <MemoryRouter initialEntries={["/file/manage"]}>
          <AuthContext.Provider value={{ user: mockUser, setUser: fn() }}>
            <Story />
          </AuthContext.Provider>
        </MemoryRouter>
      );
    },
  ],
  args: {
    setToast: fn(),
  },
} satisfies Meta<typeof InfraccionLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithAccessDeniedModal: Story = {
  decorators: [
    (Story) => {
      installApiMock();

      return (
        <MemoryRouter
          initialEntries={[
            {
              pathname: "/file/manage",
              state: {
                radicadoToSelect: "NO-EXISTE",
                timestamp: Date.now(),
              },
            },
          ]}
        >
          <AuthContext.Provider value={{ user: mockUser, setUser: fn() }}>
            <Story />
          </AuthContext.Provider>
        </MemoryRouter>
      );
    },
  ],
};
