import { BellRing, Download, ExternalLink, Eye, Leaf } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import { TITULO_ETAPA } from "../../manage/etapasProceso";
import type { Actuacion } from "../../types";
import { pestanaDeActuacion } from "./filtros";

/** Quién revisa en el único paso de cada flujo (informes y actos). */
const REVISOR: Record<Actuacion["categoria"], string> = {
  informe: "Líder técnico",
  acto: "Líder de proyecto",
};

type Props = {
  actuaciones: Actuacion[];
  /** Sin permiso para abrir expedientes: el radicado va como texto. */
  onExpediente?: (a: Actuacion) => void;
  onProceso: (a: Actuacion) => void;
  /** Precarga el proceso al pasar el mouse (abre sin spinner). */
  onPrecargarProceso?: (a: Actuacion) => void;
  /** Informe sin proceso vigente cuya matriz puedo editar. */
  onMatriz: (a: Actuacion) => void;
};

function Estado({ a }: { a: Actuacion }) {
  const estado = a.estado_proceso;
  return (
    <div className="flex flex-wrap items-center gap-1">
      {a.informe?.aceptado ? (
        <EstadoBadge etiqueta="Aceptado" tono="success" />
      ) : estado ? (
        <EstadoBadge etiqueta={estado.etiqueta} tono={estado.tono} />
      ) : (
        <EstadoBadge etiqueta="Sin proceso" tono="neutral" />
      )}
      {a.requiere_mi_accion && (
        <EstadoBadge etiqueta="Tu turno" tono="info" icono={<BellRing size={11} />} title="Requiere tu acción" />
      )}
      {a.acto && !a.acto.vigente && <span className="text-[10px] text-base-content/60">Histórico</span>}
    </div>
  );
}

/** Paso de revisión (como recurso): cada flujo tiene un solo paso. */
function Paso({ a }: { a: Actuacion }) {
  if (a.proceso_id === null) return <span className="text-base-content/60">—</span>;
  return (
    <>
      1/1
      {a.estado_proceso?.codigo === "en_revision" && (
        <p className="text-[10px] text-base-content/60">{REVISOR[a.categoria]}</p>
      )}
    </>
  );
}

/**
 * Mis actuaciones: informes técnicos y actos administrativos del usuario,
 * con las mismas columnas que "Mis actuaciones" de recurso.
 * Resalta lo que requiere mi acción. Todo viene del backend.
 */
export default function MisActuacionesTabla({
  actuaciones,
  onExpediente,
  onProceso,
  onPrecargarProceso,
  onMatriz,
}: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="table table-sm w-full">
        <thead className="bg-base-200">
          <tr>
            <th className="text-xs">Expediente</th>
            <th className="text-xs">Documento</th>
            <th className="text-xs">Rol</th>
            <th className="text-xs">Etapa</th>
            <th className="text-xs">Estado</th>
            <th className="text-xs">Paso</th>
            <th className="text-xs">Pendiente</th>
            <th className="text-xs">Actualizado</th>
            <th className="text-xs text-center border-l border-base-300">Proceso</th>
          </tr>
        </thead>
        <tbody>
          {actuaciones.map((a) => {
            const inf = a.informe;
            return (
              <tr key={a.clave} className={`border-b border-base-200 ${a.requiere_mi_accion ? "bg-info/5" : ""}`}>
                <td className="font-mono text-xs font-semibold">
                  {onExpediente ? (
                    <button type="button" onClick={() => onExpediente(a)} className="btn btn-ghost btn-xs gap-1 text-primary">
                      {a.expediente_radicado ?? `#${a.expediente_id}`}
                      <ExternalLink size={10} />
                    </button>
                  ) : (
                    (a.expediente_radicado ?? `#${a.expediente_id}`)
                  )}
                </td>
                <td className="text-xs">
                  {a.tipo_etiqueta}
                  {inf && <p className="text-[10px] text-base-content/60">{inf.modo === "MANUAL" ? "Manual" : "Flujo"}</p>}
                </td>
                <td className="text-xs">
                  <div className="flex flex-wrap gap-1">
                    {a.roles.map((r) => (
                      <span key={r.codigo} className="badge badge-ghost badge-xs">
                        {r.etiqueta}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="text-xs">{TITULO_ETAPA[pestanaDeActuacion(a)]}</td>
                <td>
                  <Estado a={a} />
                </td>
                <td className="text-xs">
                  <Paso a={a} />
                </td>
                <td className="text-xs">
                  {a.accion_pendiente ?? <span className="text-base-content/60">—</span>}
                  {a.numero_devoluciones > 0 && (
                    <span className="badge badge-warning badge-xs ml-1" title="Devoluciones">
                      {a.numero_devoluciones}
                    </span>
                  )}
                </td>
                <td className="text-xs">{formatDate(a.fecha_actualizacion)}</td>
                <td className="text-center border-l border-base-200">
                  <div className="flex items-center justify-center gap-1">
                    {inf?.aceptado && inf.documento_informe_id && (
                      <button
                        type="button"
                        onClick={() => openDocumentById(inf.documento_informe_id!)}
                        className="btn btn-ghost btn-xs gap-1 text-success"
                        title="Ver documento aceptado"
                      >
                        <Download size={13} />
                        Ver doc
                      </button>
                    )}
                    {a.proceso_id !== null && (
                      <button
                        type="button"
                        onClick={() => onProceso(a)}
                        onMouseEnter={() => onPrecargarProceso?.(a)}
                        onFocus={() => onPrecargarProceso?.(a)}
                        className={`btn btn-xs gap-1 ${a.requiere_mi_accion ? "btn-info text-white" : "btn-ghost text-info"}`}
                      >
                        <Eye size={13} />
                        Proceso
                      </button>
                    )}
                    {inf && a.proceso_id === null && inf.puede_editar_matriz && (
                      <button type="button" onClick={() => onMatriz(a)} className="btn btn-ghost btn-xs gap-1 text-success">
                        <Leaf size={13} />
                        Editar matriz
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
