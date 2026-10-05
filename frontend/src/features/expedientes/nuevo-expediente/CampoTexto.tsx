import { Campo } from "@shared/ui/form/Campo";
import type { InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
  etiqueta: string;
};

/** Input de texto con etiqueta en el estilo del formulario de alta. */
export default function CampoTexto({ etiqueta, type = "text", ...input }: Props) {
  return (
    <Campo etiqueta={etiqueta}>
      <input type={type} className="input w-full" {...input} />
    </Campo>
  );
}
