import type { Meta, StoryObj } from "@storybook/react-vite";
import { CheckCircle, Clock, AlertCircle } from "lucide-react";
import { EstadoBadge } from "./EstadoBadge";

const meta: Meta<typeof EstadoBadge> = {
  title: "Shared/EstadoBadge",
  component: EstadoBadge,
  args: { etiqueta: "En revisión", tono: "warning" },
};
export default meta;
type Story = StoryObj<typeof EstadoBadge>;

export const Default: Story = {};

export const Tonos: Story = {
  render: () => (
    <div data-theme="emerald" className="flex flex-wrap gap-2 p-4">
      <EstadoBadge etiqueta="Aceptado" tono="success" icono={<CheckCircle size={12} />} />
      <EstadoBadge etiqueta="En revisión" tono="warning" icono={<Clock size={12} />} />
      <EstadoBadge etiqueta="Devuelto" tono="error" icono={<AlertCircle size={12} />} />
      <EstadoBadge etiqueta="Pendiente de firma" tono="info" />
      <EstadoBadge etiqueta="Sin proceso" tono="neutral" />
      <EstadoBadge etiqueta="Grande" tono="success" size="md" />
    </div>
  ),
};
