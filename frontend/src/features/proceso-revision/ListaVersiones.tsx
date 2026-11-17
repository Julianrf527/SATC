import { memo } from "react";
import { Download, FileText } from "lucide-react";
import { formatDateTime, formatFileSize } from "@shared/lib/format";
import type { VersionProceso } from "./types";
import { abrirArchivo } from "./visual";

type Props = {
  versiones: VersionProceso[];
  versionActual: number;
  /** Ruta de descarga (la da el adapter del módulo). */
  urlVersion: (version: VersionProceso) => string;
};

/** Versiones del proceso, la más reciente primero (orden del backend). */
export function ListaVersiones({ versiones, versionActual, urlVersion }: Props) {
  return (
    <section className="bg-base-200 rounded-lg p-4">
      <h4 className="font-semibold text-base-content mb-3 flex items-center gap-2">
        <FileText size={18} />
        Versiones ({versiones.length})
      </h4>
      {versiones.length === 0 ? (
        <p className="text-sm text-base-content/60 text-center py-4">
          Aún no se ha cargado ninguna versión
        </p>
      ) : (
        <ul className="space-y-3 max-h-72 overflow-y-auto">
          {versiones.map((version) => {
            const nombre = version.archivo.nombre ?? `Versión ${version.numero_version}`;
            return (
              <li
                key={version.version_id}
                className="bg-base-100 rounded-lg p-3 border border-base-300 flex items-start justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-base-content">
                      Versión {version.numero_version}
                    </span>
                    {version.numero_version === versionActual && (
                      <span className="badge badge-success badge-sm">Actual</span>
                    )}
                  </div>
                  <p className="text-xs text-base-content/60 truncate" title={nombre}>
                    {nombre}
                  </p>
                  <p className="text-xs text-base-content/60">
                    {formatDateTime(version.fecha_subida)} · {formatFileSize(version.archivo.size)}
                  </p>
                  {version.comentario && (
                    <p className="text-xs text-base-content/60 mt-1 italic">"{version.comentario}"</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => abrirArchivo(urlVersion(version))}
                  className="btn btn-xs btn-outline btn-success gap-1 shrink-0"
                  title={nombre}
                >
                  <Download size={12} />
                  Descargar
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// memo: no se re-dibuja al abrir/cerrar los formularios del modal padre.
export default memo(ListaVersiones);
