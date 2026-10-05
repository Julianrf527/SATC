import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Upload } from "lucide-react";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { Modal } from "./Modal";

const meta: Meta<typeof Modal> = {
  title: "Shared/Modal",
  component: Modal,
};
export default meta;
type Story = StoryObj<typeof Modal>;

function Demo(props: Partial<React.ComponentProps<typeof Modal>>) {
  const [open, setOpen] = useState(true);
  const [inner, setInner] = useState(false);
  return (
    <div data-theme="emerald" className="p-6">
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        Abrir modal
      </button>
      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Subir nueva versión"
        subtitle="Documento DOC-2026-001"
        icon={<Upload size={20} />}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button className="btn btn-primary" onClick={() => setInner(true)}>
              Abrir anidado
            </button>
          </>
        }
        {...props}
      >
        <label className="block text-sm font-medium text-base-content/70 mb-1">Comentario</label>
        <textarea className="textarea w-full h-24" />
      </Modal>
      <Modal isOpen={inner} onClose={() => setInner(false)} title="Modal anidado" size="sm">
        Esc cierra solo este modal.
      </Modal>
    </div>
  );
}

// El modal se monta por portal en document.body, por eso se consulta ahí.
const body = () => within(document.body);

export const Basico: Story = {
  render: () => <Demo />,
  play: async () => {
    const dialog = await body().findByRole("dialog", { name: "Subir nueva versión" });
    // Foco inicial en el primer enfocable del contenido (no la X del header).
    await waitFor(() => expect(dialog.querySelector("textarea")).toHaveFocus());

    // Anidado: Esc cierra solo el de arriba.
    await userEvent.click(body().getByRole("button", { name: "Abrir anidado" }));
    await body().findByRole("dialog", { name: "Modal anidado" });
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(body().queryByRole("dialog", { name: "Modal anidado" })).toBeNull());
    expect(body().getByRole("dialog", { name: "Subir nueva versión" })).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(body().queryByRole("dialog")).toBeNull());
  },
};

export const SinCierrePorFondo: Story = {
  render: () => <Demo closeOnBackdrop={false} closeOnEsc={false} />,
  play: async () => {
    await body().findByRole("dialog", { name: "Subir nueva versión" });
    await userEvent.keyboard("{Escape}");
    expect(body().getByRole("dialog", { name: "Subir nueva versión" })).toBeInTheDocument();
    await userEvent.click(body().getByRole("button", { name: "Cerrar" }));
    await waitFor(() => expect(body().queryByRole("dialog")).toBeNull());
  },
};
export const Grande: Story = { render: () => <Demo size="4xl" /> };
