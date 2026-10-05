import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import ExpedienteLogLayout from "./ExpedienteLogLayout";

const meta = {
  title: "app-sancionatoria/Layout/ExpedienteLogLayout",
  component: ExpedienteLogLayout,
  parameters: { layout: "fullscreen" },
  args: {
    setToast: fn(),
  },
} satisfies Meta<typeof ExpedienteLogLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Estado inicial — formulario de búsqueda vacío */
export const Default: Story = {};
