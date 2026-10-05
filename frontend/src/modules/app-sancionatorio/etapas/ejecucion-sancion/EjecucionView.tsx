import { Fragment } from "react";
import { formatDate } from "@shared/lib/format";
import type { Ejecucion } from "../../types";
import Icono from "../comun/Icono";
import { ICONOS, PDF_RELLENO_20, PDF_RELLENO_24 } from "../comun/iconos";

type Props = {
  data: Ejecucion;
  onViewDocument: (documentId: number) => void;
};

const formatAutoAdmin = (autoAdmin: string) => {
  if (!autoAdmin) return "No registrado";
  const match = autoAdmin.match(/^(AUTO|RES)(.*)$/);
  return match ? `${match[1]} ${match[2]}` : autoAdmin;
};

export default function EjecucionView({ data, onViewDocument }: Props) {
  const estados = [
    { etiqueta: "Cobro Coactivo", valor: data.cobro_coactivo, doc: data.documento_cobro_id, claseIcono: "text-error" },
    { etiqueta: "RUIA", valor: data.ruia, doc: data.documento_ruia_id, claseIcono: "text-tono-info" },
    { etiqueta: "Memorando", valor: data.memorando, doc: data.documento_memorando_id, claseIcono: "text-tono-info" },
    { etiqueta: "Disposición", valor: data.disposicion, doc: null, claseIcono: "" },
  ];

  return (
    <div className="space-y-6">
      {/* Estados de documentos en una línea horizontal */}
      <div className="flex flex-wrap items-center gap-6">
        {estados.map((e, i) => (
          <Fragment key={e.etiqueta}>
            {i > 0 && <div className="divider divider-horizontal mx-0"></div>}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-base-content/70">{e.etiqueta}</span>
              <span className={`badge text-white badge-sm ${e.valor ? "badge-success" : "badge-error"}`}>
                {e.valor ? "Sí" : "No"}
              </span>
              {/* Solo si está marcado como SÍ y tiene documento */}
              {e.valor && e.doc && (
                <button
                  onClick={() => onViewDocument(e.doc as number)}
                  className="btn btn-ghost btn-xs text-tono-info hover:bg-info/10"
                  title="Ver documento"
                >
                  <svg className={`w-5 h-5 ${e.claseIcono}`} fill="currentColor" viewBox="0 0 20 20">
                    <path d={PDF_RELLENO_20} />
                  </svg>
                </button>
              )}
            </div>
          </Fragment>
        ))}
      </div>

      <div className="divider my-4"></div>

      {/* Acto Administrativo en sección separada */}
      <div className="bg-base-200/50 rounded-lg p-6">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <Icono d={ICONOS.documento} className="w-5 h-5 text-primary" />
          Acto Administrativo
        </h4>

        <div className="flex items-center gap-4">
          <div className="flex-1">
            <p className="text-sm text-base-content/60 mb-1">Número del acto</p>
            <p className="text-lg font-bold font-mono">{formatAutoAdmin(data.tipo_acto)}</p>
          </div>
          <div className="flex-1">
            <p className="text-sm text-base-content/60 mb-1">Fecha</p>
            <p className="text-base font-semibold">
              {formatDate(data.fecha_auto, { style: "long", fallback: "No registrada" })}
            </p>
          </div>
          {data.documento_acto_administrativo_id && (
            <div className="flex-shrink-0">
              <button
                onClick={() => onViewDocument(data.documento_acto_administrativo_id as number)}
                className="btn btn-ghost btn-xs text-tono-info hover:bg-info/10"
                title="Ver documento"
              >
                <svg className="w-8 h-8 text-error" viewBox="0 0 24 24" fill="currentColor">
                  <path d={PDF_RELLENO_24} />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
