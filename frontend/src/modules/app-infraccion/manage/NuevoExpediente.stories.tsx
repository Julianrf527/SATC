import { useState, type ComponentProps } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import type { Quejoso, TipoAfectacion } from "../types";
import NuevoExpediente from "./NuevoExpediente";

const mockMunicipios: Municipio[] = [
  {
    id: 1,
    nombre: "Garagoa",
    veredas: [
      { id: 11, nombre: "Ciénega Valvanera" },
      { id: 12, nombre: "Quigua Abajo" },
    ],
  },
  {
    id: 2,
    nombre: "Macanal",
    veredas: [{ id: 21, nombre: "Centro" }],
  },
];

const mockRecursos: ModeloGenerico[] = [
  { id: 1, nombre: "Agua" },
  { id: 2, nombre: "Suelo" },
  { id: 3, nombre: "Aire" },
];

const mockTiposAfectacion: TipoAfectacion[] = [
  { id: 101, nombre: "Vertimiento", recurso_id: 1 },
  { id: 102, nombre: "Captación ilegal", recurso_id: 1 },
  { id: 201, nombre: "Tala", recurso_id: 2 },
  { id: 301, nombre: "Quema a cielo abierto", recurso_id: 3 },
];

const mockQuejosos: Quejoso[] = [
  {
    id: 101,
    nombre: "Ana Ruiz",
    telefono: "3001234567",
    correo: "ana.ruiz@example.com",
    anonimo: false,
  },
  {
    id: 102,
    nombre: null,
    telefono: null,
    correo: null,
    anonimo: true,
  },
];

const meta = {
  title: "app-infracciones/Manage/NuevoExpediente",
  component: NuevoExpediente,
  parameters: { layout: "fullscreen" },
  args: {
    userId: 88,
    municipioList: mockMunicipios,
    recursoAfectadoList: mockRecursos,
    tipoAfectacionList: mockTiposAfectacion,
    quejosoList: mockQuejosos,
    setQuejosoList: fn(),
    setToast: fn(),
    onCancel: fn(),
    agregarExpediente: fn(),
  },
} satisfies Meta<typeof NuevoExpediente>;

export default meta;
type Story = StoryObj<typeof meta>;

function StatefulNuevoExpediente({
  inicial,
  ...args
}: ComponentProps<typeof NuevoExpediente> & { inicial: Quejoso[] }) {
  const [quejosoList, setQuejosoList] = useState<Quejoso[]>(inicial);

  return (
    <div className="h-screen p-6 bg-base-200">
      <div className="mx-auto max-w-5xl h-full border border-base-300 rounded-xl overflow-hidden bg-base-100">
        <NuevoExpediente {...args} quejosoList={quejosoList} setQuejosoList={setQuejosoList} />
      </div>
    </div>
  );
}

export const Default: Story = {
  render: (args) => <StatefulNuevoExpediente {...args} inicial={mockQuejosos} />,
};

export const SinQuejososIniciales: Story = {
  render: (args) => <StatefulNuevoExpediente {...args} inicial={[]} />,
};
