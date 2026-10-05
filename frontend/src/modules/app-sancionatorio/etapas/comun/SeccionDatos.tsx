import type { ReactNode } from "react";
import Icono from "./Icono";
import { ICONOS, TONOS, type Tono } from "./iconos";

type Props = {
  titulo: string;
  subtitulo: ReactNode;
  /** Trazo del icono del encabezado. */
  icono: string;
  tono: Tono;
  /** Si se pasa, muestra el botón "Editar" en el encabezado. */
  onEditar?: () => void;
  /** Texto del botón editar (vacío = solo icono). */
  textoEditar?: string;
  deshabilitado?: boolean;
  children: ReactNode;
};

/** Tarjeta de datos propios de una etapa (encabezado con icono + Editar). */
export default function SeccionDatos({
  titulo,
  subtitulo,
  icono,
  tono,
  onEditar,
  textoEditar = "Editar",
  deshabilitado,
  children,
}: Props) {
  const t = TONOS[tono];
  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 ${t.fondo} rounded-lg flex items-center justify-center`}>
              <Icono d={icono} className={`w-5 h-5 ${t.texto}`} />
            </div>
            <div>
              <h3 className="text-xl font-bold">{titulo}</h3>
              <p className="text-sm text-base-content/60">{subtitulo}</p>
            </div>
          </div>
          {onEditar && (
            <button
              className={`btn btn-ghost btn-sm gap-2 ${t.hover}`}
              onClick={onEditar}
              disabled={deshabilitado}
            >
              <Icono d={ICONOS.editar} />
              {textoEditar}
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
