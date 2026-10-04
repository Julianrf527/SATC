import { useMemo } from "react";
import type { ExpedienteDetalle } from "../../../../types/infraccionApp";
import type { ModeloGenerico } from "../../../../types/common";
import type { ExpedienteDetalleExt } from "./useInformacionInfraccionForm";

const ETAPA_LABELS: Record<string, string> = {
  info: "Información",
  respuesta: "Respuesta",
  visita: "Visita Técnica",
  concepto: "Acoger Concepto",
  seguimiento: "Visita Seguimiento",
  cierre: "Cierre Expediente",
};

const formatEtapa = (etapa?: string | null) =>
  etapa ? ETAPA_LABELS[etapa] || etapa : etapa;

const formatDate = (dateString: string) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

interface Props {
  expediente: ExpedienteDetalle;
  recursoAfectadoList: ModeloGenerico[];
}

export default function InformacionInfraccionView({
  expediente,
  recursoAfectadoList,
}: Props) {
  const expedienteExt = expediente as ExpedienteDetalleExt;
  const ultimaEtapa = formatEtapa(
    expedienteExt.ultima_etapa || expediente.etapa_actual,
  );

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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Radicado</p>
              <p className="text-sm font-semibold">{expediente.radicado}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Fecha Radicado</p>
              <p className="text-sm">{formatDate(expediente.fecha_radicado)}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Lugar</p>
              <p className="text-sm">
                {expediente.vereda?.nombre || "Sin vereda"},{" "}
                {expediente.municipio?.nombre || "Sin municipio"}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Direccion</p>
              <p className="text-sm">{expediente.direccion || "Sin direccion"}</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Ultima Etapa</p>
              {ultimaEtapa ? (
                <p className="text-sm font-medium text-success">{ultimaEtapa}</p>
              ) : (
                <p className="text-sm text-base-content/40">Sin etapa registrada</p>
              )}
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Estado</p>
              {expediente.estado ? (
                <p className="text-sm font-medium text-success">{expediente.estado}</p>
              ) : (
                <p className="text-sm text-base-content/40">—</p>
              )}
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Quejosos</p>
              <p className="text-sm">
                {(expediente.quejosos || []).map((q) => q.anonimo ? "Anónimo" : (q.nombre ?? "Sin nombre")).join(", ") || "Sin quejosos"}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4h10M11 8h7M5 4v4m0 0l-2-2m2 2l2-2m-2 8h10m-10 4h7" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Radicados Asociados</p>
              <p className="text-sm">
                {(expedienteExt.radicados_asociados || []).join(", ") || "Sin radicados asociados"}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide mb-3">
          Recursos Afectados
        </p>
        {recursoNombresExpediente.length === 0 ? (
          <span className="text-sm text-base-content/40">Sin recursos asignados</span>
        ) : (
          <div className="space-y-2">
            {recursoAfectadoList
              .filter((r) => recursoNombresExpediente.includes(r.nombre))
              .map((recurso) => {
                const tiposRecurso = (expediente.tipos_afectacion || []).filter(
                  (t) => t.recurso_id === recurso.id,
                );
                return (
                  <div key={recurso.id} className="flex items-start gap-2 flex-wrap">
                    <span className="badge badge-success text-white badge-sm mt-0.5 flex-shrink-0">
                      {recurso.nombre}
                    </span>
                    {tiposRecurso.length > 0 && (
                      <span className="text-sm text-base-content/60 leading-tight">
                        {tiposRecurso.map((t) => t.nombre).join(" · ")}
                      </span>
                    )}
                  </div>
                );
              })}
          </div>
        )}
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
