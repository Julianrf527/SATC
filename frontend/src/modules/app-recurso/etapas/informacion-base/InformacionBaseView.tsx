import type { ReactNode } from "react";
import {
  CalendarDays,
  Droplets,
  Eye,
  FileCheck,
  FileText,
  Fingerprint,
  Hash,
  Home,
  Layers,
  Map as MapIcon,
  MapPin,
  ScrollText,
  Waves,
} from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { openDocumentById } from "@shared/lib/documentViewer";
import type { ExpedienteDetalle } from "../../types";
import { textoFuente } from "./formatoInformacion";

/** Celda de dato con ícono, título y contenido de una línea (mismo formato que infraction). */
function Dato({ icono, titulo, children }: { icono: ReactNode; titulo: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 min-w-0">
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

const Texto = ({ children, title }: { children: ReactNode; title?: string }) => (
  <p className="text-sm truncate" title={title}>
    {children || "—"}
  </p>
);

/**
 * Información base del expediente en solo lectura (plan §3). Cuadrícula de
 * 3 columnas, una fila por tema: identificación, trámite, predio y fuente.
 * Cada dato ocupa una sola línea para que las filas queden parejas.
 */
export default function InformacionBaseView({ expediente: e }: { expediente: ExpedienteDetalle }) {
  const fuente = textoFuente(
    e.fuentes.map((f) => f.nombre),
    e.nombre_fuente,
  );
  const lugar = [e.vereda?.nombre, e.municipio?.nombre].filter(Boolean).join(", ");

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-5">
      {/* Identificación */}
      <Dato icono={<Hash size={16} />} titulo="Expediente">
        <p className="text-sm font-semibold">{e.expediente}</p>
      </Dato>
      <Dato icono={<FileText size={16} />} titulo="Radicado">
        <p className="text-sm font-semibold truncate">
          {e.radicado}
          <span className="font-normal text-base-content/60"> · {formatDate(e.fecha_radicado, { fallback: "" })}</span>
        </p>
      </Dato>
      <Dato icono={<Fingerprint size={16} />} titulo="Número VITAL">
        <Texto>{e.numero_vital}</Texto>
      </Dato>

      {/* Trámite */}
      <Dato icono={<CalendarDays size={16} />} titulo="Radicado de la solicitud">
        <Texto>
          {e.radicado_oficio_entrada}
          {e.fecha_oficio_entrada ? ` · ${formatDate(e.fecha_oficio_entrada)}` : ""}
        </Texto>
      </Dato>
      <Dato icono={<FileCheck size={16} />} titulo="Comprobante de pago">
        {e.doc_comprobante_pago_id ? (
          <button
            type="button"
            className="btn btn-ghost btn-xs -ml-2 gap-1 text-success"
            onClick={() => openDocumentById(e.doc_comprobante_pago_id)}
            title="Ver comprobante de pago"
          >
            <Eye size={14} />
            {e.comprobante_pago?.nombre ?? "Ver documento"}
          </button>
        ) : (
          <p className="text-sm text-base-content/60">Sin documento adjunto</p>
        )}
      </Dato>
      <Dato icono={<MapPin size={16} />} titulo="Lugar">
        <Texto title={lugar}>{lugar}</Texto>
      </Dato>

      {/* Predio */}
      <Dato icono={<Home size={16} />} titulo="Predio">
        <Texto title={e.nombre_predio}>{e.nombre_predio}</Texto>
      </Dato>
      <Dato icono={<ScrollText size={16} />} titulo="Matrícula inmobiliaria">
        <Texto>{e.matricula_inmobiliaria}</Texto>
      </Dato>
      <Dato icono={<MapIcon size={16} />} titulo="Código catastral">
        <Texto title={e.codigo_catastral}>{e.codigo_catastral}</Texto>
      </Dato>

      {/* Fuente */}
      <Dato icono={<Layers size={16} />} titulo="Tipo de fuente">
        <Texto>{e.tipo_fuente?.nombre}</Texto>
      </Dato>
      <Dato icono={<Waves size={16} />} titulo="Fuente">
        <Texto title={fuente}>{fuente}</Texto>
      </Dato>
      <Dato icono={<Droplets size={16} />} titulo="Usos del agua">
        {e.usos.length === 0 ? (
          <p className="text-sm text-base-content/60">Sin usos</p>
        ) : (
          <div className="flex flex-wrap gap-1 mt-0.5">
            {e.usos.map((u) => (
              <span key={u} className="badge badge-success text-white badge-sm">
                {u}
              </span>
            ))}
          </div>
        )}
      </Dato>
    </div>
  );
}
