import { useState, type ReactNode } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { MemoryRouter, type InitialEntry } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AuthContext from "@shared/context/AuthContext";
import { INFRACTION_ENDPOINTS } from "@shared/lib/api";
import InfraccionLayout from "./GestionInfraccionLayout";

const mockUser = {
  user_id: 101,
  primer_nombre: "Ana",
  segundo_nombre: "Maria",
  primer_apellido: "Suarez",
  segundo_apellido: "Lopez",
  correo: "ana.suarez@satc.local",
  permisos: [{ name: "Gestion Infracciones", path: "/infraction/manage" }],
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

const mockTiposAfectacion = [
  { id: 1, nombre: "Vertimiento", recurso_id: 1 },
  { id: 2, nombre: "Ocupacion", recurso_id: 2 },
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

// Rutas actuales (renombradas a español): se toman de las constantes.
const ROUTES: [string, () => unknown][] = [
  [INFRACTION_ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT, () => ({ data: mockMunicipios })],
  [INFRACTION_ENDPOINTS.INFRACTION_AFFECTED_RESOURCE, () => ({ data: mockRecursos })],
  [INFRACTION_ENDPOINTS.INFRACTION_TIPOS_AFECTACION, () => ({ data: mockTiposAfectacion })],
  [INFRACTION_ENDPOINTS.INFRACTION_COMPLAINER, () => ({ data: [] })],
  [INFRACTION_ENDPOINTS.INFRACTION_BY_USER(mockUser.user_id), () => ({ data: mockExpedientes })],
  [
    INFRACTION_ENDPOINTS.INFRACTION_FUll(mockExpedientes[0].id),
    () => ({
      data: {
        direccion: "Vereda Catambuco",
        vereda: { id: 11, nombre: "Catambuco" },
        ultima_etapa: "Respuesta",
        recurso_afectado: [{ id: 1, nombre: "Agua" }],
        involucrados: mockExpedientes[0].involucrados,
      },
      tipo_notificacion: { id: 1, nombre: "Personal" },
      etapas_existentes: [1, 2, 3],
    }),
  ],
];

const installApiMock = () => {
  const fetchMock: typeof window.fetch = async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const match = ROUTES.find(([path]) => url.includes(path));
    return jsonResponse(match ? match[1]() : { data: [] });
  };
  window.fetch = fetchMock;
};

function Providers({ children, initialEntries }: { children: ReactNode; initialEntries: InitialEntry[] }) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  );
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthContext.Provider value={{ user: mockUser, setUser: fn() }}>
          {children}
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// Un único decorator con Router + QueryClient. Antes la historia
// "WithAccessDeniedModal" añadía su propio MemoryRouter dentro del de `meta`
// (Router anidado → error); ahora solo cambia `parameters.initialEntries`.
const meta = {
  title: "app-infracciones/Layout/InfraccionLayout",
  component: InfraccionLayout,
  parameters: {
    layout: "fullscreen",
    initialEntries: ["/infraction/manage"] as InitialEntry[],
  },
  decorators: [
    (Story, context) => {
      installApiMock();
      return (
        <Providers initialEntries={context.parameters.initialEntries as InitialEntry[]}>
          <Story />
        </Providers>
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
  parameters: {
    initialEntries: [
      {
        pathname: "/infraction/manage",
        state: {
          radicadoToSelect: "NO-EXISTE",
          timestamp: Date.now(),
        },
      },
    ] as InitialEntry[],
  },
};
