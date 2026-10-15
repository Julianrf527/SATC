import { useState } from "react";
import { FileUp } from "lucide-react";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";
import type { DatosAdmite, SetToast } from "../../types";
import { CampoPdf } from "../comun/campos/Campos";
import ModalFormulario from "../comun/ModalFormulario";
import { useEscritura } from "../comun/useEscritura";
import { esPdf } from "../formularios/comunes";
import { CAMPOS_DOCUMENTOS_ADMITE, type CampoDocumentoAdmite } from "./documentosAdmite";

type Props = {
  expedienteId: number;
  version: number;
  datos: DatosAdmite;
  /** Documentos que el backend deja cargar (`cargar_*` en `acciones_disponibles`). */
  permitidos: CampoDocumentoAdmite[];
  setToast: SetToast;
  onClose: () => void;
};

/**
 * Oficio a la Alcaldía, fijación del aviso y constancia de fijación (C.3,
 * PUT /admite/documentos con `version`). Reemplaza los que se adjunten.
 */
export default function DocumentosAdmiteModal({ expedienteId, version, datos, permitidos, setToast, onClose }: Props) {
  const [archivos, setArchivos] = useState<Partial<Record<CampoDocumentoAdmite, File | null>>>({});
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    const elegidos = permitidos.filter((c) => archivos[c]);
    if (elegidos.length === 0) return setError("Adjunte al menos un documento");
    if (elegidos.some((c) => !esPdf(archivos[c] as File))) return setError("Todos los documentos deben ser PDF");
    setError(null);
    ejecutar(
      {
        archivos: Object.fromEntries(elegidos.map((c) => [c, archivos[c]])),
        peticion: (ids) => ({
          url: RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, "admite/documentos"),
          method: "PUT",
          body: { version, ...ids },
        }),
      },
      { exito: "Documentos del auto actualizados", error: "Error al cargar los documentos", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Documentos del auto que admite"
      icono={<FileUp size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Guardar"
      onGuardar={guardar}
      onClose={onClose}
    >
      {CAMPOS_DOCUMENTOS_ADMITE.filter((c) => permitidos.includes(c.campo)).map((c) => (
        <CampoPdf
          key={c.campo}
          etiqueta={c.etiqueta}
          archivo={archivos[c.campo] ?? null}
          onChange={(archivo) => setArchivos((a) => ({ ...a, [c.campo]: archivo }))}
          actualId={datos[c.campo]}
        />
      ))}
    </ModalFormulario>
  );
}
