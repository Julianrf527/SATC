import { useMemo, type ReactNode } from "react";
import {
  Building2,
  CalendarDays,
  ClipboardCheck,
  Eye,
  FileCheck,
  FileText,
  Leaf,
  ListOrdered,
  MapPin,
  Users,
  Zap,
} from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { openDocumentById } from "@shared/lib/documentViewer";
import type { ExpedienteDetalle } from "../../types";
import type { ModeloGenerico } from "@shared/types/common";
import { etiquetaEtapa } from "../../manage/etapasProceso";


/** Fila de dato con ícono, título y contenido (mismo formato para todos los campos). */
function Dato({ icono, titulo, children }: { icono: ReactNode; titulo: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 bg-base-200 text-base-content/70 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
        {icono}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">{titulo}</p>
        {children}
      </div>
    </div>
  );
}

interface Props {
  expediente: ExpedienteDetalle;
  recursoAfectadoList: ModeloGenerico[];
}

export default function InformacionInfraccionView({
  expediente,
  recursoAfectadoList,
}: Props) {
  const ultimaEtapa = etiquetaEtapa(expediente.etapa_actual);
  const radicadoInicial = expediente.radicado_inicial ?? null;

  const recursoNombresExpediente = useMemo(() => {
    const recursos = (expediente.recurso_afectado || []) as Array<
      number | { id?: number; nombre?: string }
    >;

    const nombres = recursos
      .map((recurso) => {
        if (typeof recurso === "number") {
          return recursoAfectadoList.find((item) => item.id === recurso)
            ?.nombre;
        }
        if (recurso?.nombre) return recurso.nombre;
        if (!recurso?.id) return undefined;
        return recursoAfectadoList.find((item) => item.id === recurso.id)
          ?.nombre;
      })
      .filter((nombre): nombre is string => Boolean(nombre && nombre.trim()));

    return Array.from(new Set(nombres));
  }, [expediente.recurso_afectado, recursoAfectadoList]);

  const recursosConTipos = recursoAfectadoList
    .filter((r) => recursoNombresExpediente.includes(r.nombre))
    .map((recurso) => ({
      recurso,
      tipos: (expediente.tipos_afectacion || []).filter((t) => t.recurso_id === recurso.id),
    }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Dato icono={<FileText size={16} />} titulo="Radicado">
            <p className="text-sm font-semibold">{expediente.radicado}</p>
          </Dato>
          <Dato icono={<CalendarDays size={16} />} titulo="Fecha Radicado">
            <p className="text-sm">{formatDate(expediente.fecha_radicado, { fallback: "" })}</p>
          </Dato>
          <Dato icono={<MapPin size={16} />} titulo="Lugar">
            <p className="text-sm">
              {expediente.vereda?.nombre || "Sin vereda"}, {expediente.municipio?.nombre || "Sin municipio"}
            </p>
          </Dato>
          <Dato icono={<Building2 size={16} />} titulo="Direccion">
            <p className="text-sm">{expediente.direccion || "Sin direccion"}</p>
          </Dato>
          <Dato icono={<FileCheck size={16} />} titulo="Radicado inicial">
            {radicadoInicial ? (
              <button
                type="button"
                className="btn btn-ghost btn-xs -ml-2 gap-1 text-success"
                onClick={() => openDocumentById(radicadoInicial.file_id)}
                title="Ver radicado inicial"
              >
                <Eye size={14} />
                Ver documento
              </button>
            ) : (
              <p className="text-sm text-base-content/60">Sin documento adjunto</p>
            )}
          </Dato>
        </div>

        <div className="space-y-4">
          <Dato icono={<ClipboardCheck size={16} />} titulo="Ultima Etapa">
            {ultimaEtapa ? (
              <p className="text-sm font-medium text-success">{ultimaEtapa}</p>
            ) : (
              <p className="text-sm text-base-content/60">Sin etapa registrada</p>
            )}
          </Dato>
          <Dato icono={<Zap size={16} />} titulo="Estado">
            {expediente.estado ? (
              <p className="text-sm font-medium text-success">{expediente.estado}</p>
            ) : (
              <p className="text-sm text-base-content/60">—</p>
            )}
          </Dato>
          <Dato icono={<Users size={16} />} titulo="Quejosos">
            <p className="text-sm">
              {(expediente.quejosos || []).map((q) => (q.anonimo ? "Anónimo" : (q.nombre ?? "Sin nombre"))).join(", ") ||
                "Sin quejosos"}
            </p>
          </Dato>
          <Dato icono={<ListOrdered size={16} />} titulo="Radicados Asociados">
            <p className="text-sm">{(expediente.radicados_asociados || []).join(", ") || "Sin radicados asociados"}</p>
          </Dato>
          <Dato icono={<Leaf size={16} />} titulo="Recursos Afectados">
            {recursosConTipos.length === 0 ? (
              <p className="text-sm text-base-content/60">Sin recursos asignados</p>
            ) : (
              <div className="space-y-1.5 mt-0.5">
                {recursosConTipos.map(({ recurso, tipos }) => (
                  <div key={recurso.id} className="flex items-start gap-2 flex-wrap">
                    <span className="badge badge-success text-white badge-sm flex-shrink-0">{recurso.nombre}</span>
                    {tipos.length > 0 && (
                      <span className="text-sm text-base-content/60 leading-tight">
                        {tipos.map((t) => t.nombre).join(" · ")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Dato>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide mb-2">
          Descripcion
        </p>
        <p className="text-sm whitespace-pre-wrap bg-base-200 border border-base-300 rounded-lg p-3">
          {expediente.descripcion || "Sin descripcion"}
        </p>
      </div>
    </div>
  );
}
