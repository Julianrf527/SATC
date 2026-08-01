import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import type { Quejoso } from "../../../types/infraccionApp";
import NuevoExpediente from "./NuevoExpediente";

const mockMunicipios = [
  {
    id: 1,
    nombre: "Pasto",
    veredas: [
      { id: 11, nombre: "Catambuco" },
      { id: 12, nombre: "Jamondino" },
    ],
  },
  {
    id: 2,
    nombre: "Ipiales",
    veredas: [{ id: 21, nombre: "Las Lajas" }],
  },
];

const mockRecursos = [
  { id: 1, nombre: "Agua" },
  { id: 2, nombre: "Suelo" },
  { id: 3, nombre: "Aire" },
];

const mockCausas = [
  { id: 1, nombre: "Vertimiento" },
  { id: 2, nombre: "Tala" },
];

const mockQuejosos: Quejoso[] = [
  {
    id: 101,
    nombre: "Ana Ruiz",
    telefonmo: 3001234567,
    correo: "ana.ruiz@example.com",
  },
  {
    id: 102,
    nombre: "Carlos Mora",
    telefonmo: 3019876543,
    correo: "carlos.mora@example.com",
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
    quejosoList: mockQuejosos,
    setQuejosoList: fn(),
    causaList: mockCausas,
    setToast: fn(),
    onCancel: fn(),
    agregarExpediente: fn(),
  },
} satisfies Meta<typeof NuevoExpediente>;

export default meta;
type Story = StoryObj<typeof meta>;

function StatefulNuevoExpediente(
  args: React.ComponentProps<typeof NuevoExpediente>,
) {
  const [quejosoList, setQuejosoList] = useState<Quejoso[]>(mockQuejosos);

  return (
    <div className="h-screen p-6 bg-base-200">
      <div className="mx-auto max-w-5xl h-full border border-base-300 rounded-xl overflow-hidden bg-base-100">
        <NuevoExpediente
          {...args}
          quejosoList={quejosoList}
          setQuejosoList={setQuejosoList}
        />
      </div>
    </div>
  );
}

export const Default: Story = {
  render: (args) => <StatefulNuevoExpediente {...args} />,
};

export const SinQuejososIniciales: Story = {
  render: (args) => {
    const EmptyStart = () => {
      const [quejosoList, setQuejosoList] = useState<Quejoso[]>([]);
      return (
        <div className="h-screen p-6 bg-base-200">
          <div className="mx-auto max-w-5xl h-full border border-base-300 rounded-xl overflow-hidden bg-base-100">
            <NuevoExpediente
              {...args}
              quejosoList={quejosoList}
              setQuejosoList={setQuejosoList}
            />
          </div>
        </div>
      );
    };

    return <EmptyStart />;
  },
};
