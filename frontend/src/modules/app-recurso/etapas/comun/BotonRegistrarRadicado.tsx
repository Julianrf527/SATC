import { useState } from "react";
import { FileInput } from "lucide-react";
import type { SetToast } from "../../types";
import { bodyRadicado } from "../formularios/radicado";
import RadicadoModal from "./RadicadoModal";

type Props = {
  expedienteId: number;
  /** POST que crea la fila con el `Radicado` (urlRegistrarRadicado). */
  url: string;
  documento: string;
  setToast: SetToast;
  grande?: boolean;
};

/** "Registrar <documento>": radicado, fecha y PDF del usuario (crea la fila, 201). */
export default function BotonRegistrarRadicado({ expedienteId, url, documento, setToast, grande }: Props) {
  const [abierto, setAbierto] = useState(false);
  return (
    <>
      <button
        type="button"
        className={
          grande
            ? "btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
            : "btn btn-success btn-sm text-white gap-1.5"
        }
        onClick={() => setAbierto(true)}
      >
        <FileInput size={grande ? 20 : 14} /> Registrar {documento.toLowerCase()}
      </button>
      {abierto && (
        <RadicadoModal
          expedienteId={expedienteId}
          titulo={`Registrar ${documento.toLowerCase()}`}
          documento={documento}
          peticion={(form, id) => ({ url, method: "POST", body: bodyRadicado(form, id) })}
          setToast={setToast}
          onClose={() => setAbierto(false)}
        />
      )}
    </>
  );
}
