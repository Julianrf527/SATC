import { ActoAdmin } from "@features/acto-administrativo";
import type { ActoAdministrativo, TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { ActoEtapa, SetToast } from "../../types";
import Icono from "./Icono";
import { ICONOS } from "./iconos";

const COLORES = {
  indigo: { fondo: "bg-indigo-500/10", texto: "text-indigo-600" },
  purple: { fondo: "bg-purple-500/10", texto: "text-purple-600" },
} as const;

type Props = {
  titulo: string;
  subtitulo: string;
  color: keyof typeof COLORES;
  expedienteId: number;
  etapaId: number;
  tipoBinding: string;
  acto: ActoEtapa | null | undefined;
  onActoAdminUpdate: (acto: ActoAdministrativo) => void;
  setExistActoAdmin?: (existe: boolean) => void;
  involucrados?: Involucrado[];
  tiposNotificacion?: TipoNotificacion[];
  setToast: SetToast;
  isEditable: boolean;
};

/** Acto administrativo auxiliar de una etapa (nivel auxiliar, con encabezado propio). */
export default function ActoAuxiliar({
  titulo,
  subtitulo,
  color,
  expedienteId,
  etapaId,
  tipoBinding,
  acto,
  onActoAdminUpdate,
  setExistActoAdmin,
  involucrados,
  tiposNotificacion,
  setToast,
  isEditable,
}: Props) {
  const c = COLORES[color];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 px-1">
        <div className={`w-10 h-10 ${c.fondo} rounded-lg flex items-center justify-center`}>
          <Icono d={ICONOS.documento} className={`h-5 w-5 ${c.texto}`} />
        </div>
        <div>
          <h3 className="text-lg font-bold text-base-content">{titulo}</h3>
          <p className="text-sm text-base-content/70">{subtitulo}</p>
        </div>
      </div>

      <ActoAdmin
        expedienteId={expedienteId}
        actoAdmin={acto || {}}
        etapaId={etapaId}
        stageBinding={{ type: tipoBinding, id: etapaId }}
        setToast={setToast}
        tipoActo="notificacion"
        isEditable={isEditable}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        setExistActoAdmin={setExistActoAdmin}
        onActoAdminUpdate={onActoAdminUpdate}
        nivelAuxiliar={true}
      />
    </div>
  );
}
