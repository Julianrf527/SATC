import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import FileLogLayout from "./FileLogLayout";

const meta = {
  title: "app-sancionatoria/Layout/FileLogLayout",
  component: FileLogLayout,
  parameters: { layout: "fullscreen" },
  args: {
    setToast: fn(),
  },
} satisfies Meta<typeof FileLogLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Estado inicial — formulario de búsqueda vacío */
export const Default: Story = {};
