import type { ExpedienteDetalle } from "@shared/types/sancionatorio";
import type { ModeloGenerico } from "@shared/types/common";
import { formatDate } from "@shared/lib/format";
import InfoItem from "../comun/InfoItem";
import { ICONOS } from "../comun/iconos";

const ETAPA_LABELS: Record<string, string> = {
  "INDAGACION PRELIMINAR": "Indagación Preliminar",
  "DETALLE MEDIDA PREVENTIVA": "Medida Preventiva",
  "INICIO PROCESO SANCIONATORIO": "Inicio Proceso Sancionatorio",
  "CESACION": "Cesacion",
  "FORMULACION DE CARGOS": "Formulacion de Cargos",
  "APERTURA ETAPA PROBATORIA": "Apertura Etapa Probatoria",
  "CIERRE ETAPA PROBATORIA": "Cierre Etapa Probatoria",
  "DECISION DE FONDO": "Decisión de Fondo",
  "RECURSO": "Probatoria del Recurso",
  "EJECUCION DE LA SANCION": "Ejecución Sanción",
};

const formatEtapa = (etapa?: string | null) =>
  etapa ? ETAPA_LABELS[etapa.toUpperCase()] || etapa : etapa;

const ICONO_HOJA =
  "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z";
const ICONO_UBICACION =
  "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0zM15 11a3 3 0 11-6 0 3 3 0 016 0z";
const ICONO_CALENDARIO =
  "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z";
const ICONO_EDIFICIO =
  "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4";

type Props = {
  expediente: ExpedienteDetalle;
  recursoAfectadoList: ModeloGenerico[];
};

/** Datos del expediente en solo lectura. */
export default function InformacionExpedienteView({ expediente, recursoAfectadoList }: Props) {
  const recursos = (expediente.recurso_afectado || [])
    .map((id) => recursoAfectadoList.find((r) => r.id === id)?.nombre)
    .filter((nombre) => nombre);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <InfoItem icono={ICONO_HOJA} etiqueta="Radicado">
          <p className="text-sm font-semibold">{expediente.radicado}</p>
        </InfoItem>
        <InfoItem icono={ICONOS.documento} etiqueta="Expediente">
          <p className="text-sm">{expediente.expediente}</p>
        </InfoItem>
        <InfoItem icono={ICONO_UBICACION} etiqueta="Lugar">
          <p className="text-sm">
            {expediente.vereda?.nombre || "No definido"}, {expediente.municipio.nombre}
          </p>
        </InfoItem>
        <InfoItem icono={ICONOS.corazon} etiqueta="Recursos Afectados">
          <div className="flex flex-wrap gap-1 mt-1">
            {expediente.recurso_afectado && expediente.recurso_afectado.length > 0 ? (
              recursos.map((nombre, index) => (
                <span key={index} className="badge badge-success text-white badge-sm">
                  {nombre}
                </span>
              ))
            ) : (
              <span className="text-sm text-base-content/60">Sin recursos asignados</span>
            )}
          </div>
        </InfoItem>
      </div>

      <div className="space-y-4">
        <InfoItem icono={ICONO_CALENDARIO} etiqueta="Fecha de Creación">
          <p className="text-sm">{formatDate(expediente.fecha_creacion)}</p>
        </InfoItem>
        <InfoItem icono={ICONOS.portapapeles} etiqueta="Última Etapa">
          {expediente.ultima_etapa ? (
            <p className="text-sm font-medium text-success">{formatEtapa(expediente.ultima_etapa)}</p>
          ) : (
            <p className="text-sm text-base-content/60">Sin etapa registrada</p>
          )}
        </InfoItem>
        <InfoItem icono={ICONO_EDIFICIO} etiqueta="Dirección">
          <p className="text-sm">{expediente.direccion}</p>
        </InfoItem>
        <InfoItem icono={ICONOS.alerta} etiqueta="Motivo de Afectación">
          <p className="text-sm">{expediente.motivo_afectacion || "Sin motivo especificado"}</p>
        </InfoItem>
      </div>
    </div>
  );
}
