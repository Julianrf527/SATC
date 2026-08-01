import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import ManagerFilesLayout from "./ManagerFilesLayout";

const meta = {
  title: "app-sancionatoria/Layout/ManagerFilesLayout",
  component: ManagerFilesLayout,
  parameters: { layout: "fullscreen" },
  args: {
    setToast: fn(),
  },
} satisfies Meta<typeof ManagerFilesLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Estado inicial — formulario de búsqueda vacío */
export const Default: Story = {};
