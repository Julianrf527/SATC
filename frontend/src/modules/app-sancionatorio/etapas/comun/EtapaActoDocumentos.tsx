import type { ReactNode } from "react";
import { ActoAdmin, type TipoActo } from "@features/acto-administrativo";
import type { ActoAdministrativo, TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { ActoEtapa, DocumentoAnexo, SetToast } from "../../types";
import Documentos from "../document/Document";
import Icono from "./Icono";
import { ICONOS } from "./iconos";

type Props = {
  expedienteId: number;
  etapaId: number;
  /** tipo_etapa del backend ("etapa_cesacion", ...). */
  tipoEtapa: string;
  /** Tipo del stageBinding del acto ("etapa_san_cesacion", ...). */
  tipoBinding: string;
  tipoActo: TipoActo;
  acto: ActoEtapa | null | undefined;
  existeActo: boolean;
  onActoAdminUpdate: (acto: ActoAdministrativo) => void;
  customDeleteHandler?: () => Promise<void>;
  involucrados?: Involucrado[];
  tiposNotificacion?: TipoNotificacion[];
  documentos: DocumentoAnexo[];
  tiposDocumento: string[];
  onDocumentosUpdate: (documentos: DocumentoAnexo[]) => void;
  setToast: SetToast;
  isEditable: boolean;
  /** Formulario de datos propio de la etapa (solo si ya existe el acto). */
  informacion?: ReactNode;
  /** Aviso cuando aún no hay acto (por defecto "Documentos no disponibles"). */
  avisoSinActo?: { titulo: string; texto: string };
  /** Contenido extra al final (acto auxiliar, modales...). */
  children?: ReactNode;
};

const AVISO_DOCUMENTOS = {
  titulo: "Documentos no disponibles",
  texto: "Debe crear un acto administrativo antes de subir documentos.",
};

/**
 * Cuerpo común de una etapa existente: acto administrativo principal →
 * (datos de la etapa) → documentos anexos, o el aviso de que falta el acto.
 */
export default function EtapaActoDocumentos({
  expedienteId,
  etapaId,
  tipoEtapa,
  tipoBinding,
  tipoActo,
  acto,
  existeActo,
  onActoAdminUpdate,
  customDeleteHandler,
  involucrados,
  tiposNotificacion,
  documentos,
  tiposDocumento,
  onDocumentosUpdate,
  setToast,
  isEditable,
  informacion,
  avisoSinActo = AVISO_DOCUMENTOS,
  children,
}: Props) {
  const actoId = acto && "id" in acto ? acto.id : undefined;
  return (
    <div className="space-y-6">
      {/* key: si el acto cambia desde fuera (borrado/recarga) se remonta con el nuevo */}
      <ActoAdmin
        key={actoId ?? "sin-acto"}
        expedienteId={expedienteId}
        actoAdmin={acto || {}}
        etapaId={etapaId}
        stageBinding={{ type: tipoBinding, id: etapaId }}
        tipoActo={tipoActo}
        setToast={setToast}
        isEditable={isEditable}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        onActoAdminUpdate={onActoAdminUpdate}
        customDeleteHandler={customDeleteHandler}
      />

      {existeActo && informacion}

      {existeActo ? (
        <Documentos
          documentos={documentos}
          etapaId={etapaId}
          tipoEtapa={tipoEtapa}
          tiposDocumento={tiposDocumento}
          setToast={setToast}
          isEditable={isEditable}
          onDocumentosUpdate={onDocumentosUpdate}
        />
      ) : (
        isEditable && (
          <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
            <div className="card-body">
              <div className="flex items-center gap-4">
                <div className="bg-warning/10 rounded-full p-3">
                  <Icono d={ICONOS.alerta} className="h-8 w-8 text-warning" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{avisoSinActo.titulo}</h3>
                  <p className="text-sm text-base-content/70 mt-1">{avisoSinActo.texto}</p>
                </div>
              </div>
            </div>
          </div>
        )
      )}

      {children}
    </div>
  );
}
