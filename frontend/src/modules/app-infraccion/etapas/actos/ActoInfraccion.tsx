import { useState, type ComponentProps, type ReactNode } from "react";
import { BellRing, CheckCircle, FileSignature, Upload, User } from "lucide-react";
import { ActoAdmin } from "@features/acto-administrativo";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import { toastService } from "@shared/lib/toastService";
import { ETIQUETA_ETAPA_ACTO, useEstadoActoEtapa, useIniciarActoMutation, useInvalidarActos } from "../../api/actos";
import { detalleError } from "../../api/errors";
import type { EtapaActoTipo } from "../../types";
import BotonCargueDirecto from "../BotonCargueDirecto";
import { useEsSuperGestion } from "../useEsSuperGestion";
import ActoFinalModal from "./ActoFinalModal";
import ProcesoActoResumen, { EstadoProcesoActoBadge } from "./ProcesoActoResumen";
import ProcesoActoModal from "./ProcesoActoModal";
import SuperCargueActoModal from "./SuperCargueActoModal";
import TarjetaActo from "./TarjetaActo";

const ICONO_ETAPA: Record<EtapaActoTipo, string> = {
  medida_preventiva: "bx-shield-quarter",
  etapa_concepto: "bx-book-bookmark",
  etapa_cierre: "bx-check-circle",
};

type Props = Omit<
  ComponentProps<typeof ActoAdmin>,
  "allowCreate" | "allowDelete" | "allowDocumentChange" | "renderEmpty" | "renderModalCrear"
> & {
  etapaTipo: EtapaActoTipo;
  /** Id de la fila de etapa dueña del acto (medida, concepto o cierre). */
  refId: number;
  /**
   * Título del recuadro. Si el acto ES la etapa (cierre), el de la etapa con
   * su número ("Etapa 5 · Cierre Expediente"), como el nodo de recurso.
   */
  titulo?: string;
  /** Dentro de otra tarjeta (la medida preventiva). */
  anidada?: boolean;
  /** Resto de la etapa cuando el acto ES la etapa (archivar, en cierre). */
  children?: ReactNode;
};

/**
 * Acto administrativo de una etapa de infracciones, como `NodoActo` de
 * recurso: tarjeta con estado y botones en la cabecera ("Cargar versión
 * final", "Cargue directo"), abogado encargado, el bloque del documento
 * (paso / versión) con su botón al modal del proceso y, cuando existe, el acto (`ActoAdmin`)
 * con sus notificaciones / comunicaciones. Botones según lo que manda el
 * backend (GET /revision-actos/etapa/...). Solo super gestión carga directo,
 * cambia el PDF o elimina; el encargado corrige tipo, numerado y fecha.
 */
export default function ActoInfraccion({
  etapaTipo,
  refId,
  titulo: tituloRecuadro,
  anidada,
  children,
  isEditable = true,
  onActoAdminUpdate,
  ...props
}: Props) {
  const esSuper = useEsSuperGestion();
  const invalidarActos = useInvalidarActos();
  const { data, isPending, isError } = useEstadoActoEtapa(etapaTipo, refId);
  const iniciar = useIniciarActoMutation();
  const [procesoAbierto, setProcesoAbierto] = useState<number | null>(null);
  const [cargarFinal, setCargarFinal] = useState(false);

  const titulo = tituloRecuadro ?? ETIQUETA_ETAPA_ACTO[etapaTipo];
  const acto = "id" in props.actoAdmin ? props.actoAdmin : null;
  const proceso = acto ? null : (data?.proceso ?? null);

  const actoAdmin = (renderEmpty?: (abrirCrear: () => void) => ReactNode) => (
    <ActoAdmin
      // ActoAdmin solo lee `actoAdmin` al montar: al aparecer (versión final,
      // cargue directo) o desaparecer el acto se vuelve a montar.
      key={acto?.id ?? "sin-acto"}
      {...props}
      isEditable={isEditable}
      allowCreate={esSuper}
      allowDelete={esSuper}
      allowDocumentChange={esSuper}
      embedded
      onActoAdminUpdate={(a) => {
        // Cargue directo / eliminación cierran o liberan el proceso del acto.
        void invalidarActos();
        onActoAdminUpdate?.(a);
      }}
      renderEmpty={renderEmpty}
      // Cargue directo con la estética de recurso (no el modal genérico).
      renderModalCrear={({ onSave, onClose }) => (
        <SuperCargueActoModal
          titulo={ETIQUETA_ETAPA_ACTO[etapaTipo]}
          conProceso={!!proceso && proceso.estado.codigo !== "aprobado" && proceso.estado.codigo !== "finalizado"}
          onSave={onSave}
          onClose={onClose}
        />
      )}
    />
  );

  const documento = ETIQUETA_ETAPA_ACTO[etapaTipo];
  const puedeSubir = isEditable && !!data?.puede_proyectar;

  const tarjeta = (abrirCargueDirecto: (() => void) | null, cuerpo: ReactNode) => {
    const botones = isEditable && !acto && (
      <>
        {proceso?.puede_cargar_version_final && (
          <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={() => setCargarFinal(true)}>
            <FileSignature size={14} />
            Cargar versión final
          </button>
        )}
        {data?.puede_cargue_directo && abrirCargueDirecto && <BotonCargueDirecto onClick={abrirCargueDirecto} />}
      </>
    );

    // Sin proceso todavía el acto está "pendiente de carga" (como recurso).
    const estado = acto ? (
      <EstadoBadge etiqueta="Acto expedido" tono="success" size="md" icono={<CheckCircle size={14} />} />
    ) : proceso ? (
      <EstadoProcesoActoBadge proceso={proceso} />
    ) : data ? (
      <>
        <EstadoBadge etiqueta="Pendiente de carga" tono="neutral" size="md" />
        {puedeSubir && <EstadoBadge etiqueta="Tu turno" tono="info" icono={<BellRing size={11} />} title="Requiere tu acción" />}
      </>
    ) : null;

    return (
      <TarjetaActo
        titulo={titulo}
        subtitulo={acto ? `${acto.tipo_acto} No. ${acto.numerado} del ${formatDate(acto.fecha_numerado)}` : undefined}
        icono={ICONO_ETAPA[etapaTipo]}
        tono={acto ? "success" : "info"}
        estado={estado}
        acciones={botones || undefined}
        anidada={anidada}
      >
        <div className="space-y-4">
          {cuerpo}
          {children}
        </div>

        <ProcesoActoModal procesoId={procesoAbierto} onClose={() => setProcesoAbierto(null)} />
        {cargarFinal && proceso && <ActoFinalModal procesoId={proceso.id} titulo={documento} onClose={() => setCargarFinal(false)} />}
      </TarjetaActo>
    );
  };

  if (acto) return tarjeta(null, actoAdmin(() => null));

  const encargado = proceso?.encargado_nombre ?? data?.encargado_nombre ?? null;

  // Como recurso: "Subir versión" abre el modal del proceso (se crea en
  // "pendiente de carga" si aún no existe) y la versión se sube desde ahí.
  const abrirProceso = () =>
    iniciar.mutate(
      { etapaTipo, refId },
      {
        onSuccess: (res) => setProcesoAbierto(res.proceso_id),
        onError: (err) =>
          toastService.showToast({ id: Date.now(), message: detalleError(err) ?? "No se pudo abrir el proceso", type: "error" }),
      },
    );

  const sinActo = isPending ? (
    <div className="flex justify-center py-6">
      <span className="loading loading-spinner text-primary" />
    </div>
  ) : isError ? (
    <p role="alert" className="text-error text-sm">
      No se pudo consultar el proceso del acto
    </p>
  ) : (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="flex items-start gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 bg-base-200 text-base-content/70">
            <User size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Abogado encargado</p>
            <div className="text-sm font-semibold break-words">
              {encargado ?? <span className="text-base-content/60 italic font-normal">Sin asignar</span>}
            </div>
          </div>
        </div>
      </div>
      {proceso ? (
        <ProcesoActoResumen proceso={proceso} documento={documento} soloLectura={!isEditable} />
      ) : (
        // Aún sin proceso: versión 0, el encargado sube la primera versión.
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-base-200/50 rounded-lg border border-base-300">
          <div className="text-sm space-y-0.5">
            <p className="font-medium">
              {documento}
              <span className="text-base-content/60 font-normal"> · paso 1 de 1</span>
            </p>
            <p className="text-xs text-base-content/60">
              Versión 0{!puedeSubir && " · pendiente de carga del abogado encargado"}
            </p>
          </div>
          {puedeSubir && (
            <button
              type="button"
              className="btn btn-sm gap-2 btn-info text-white"
              onClick={abrirProceso}
              disabled={iniciar.isPending}
            >
              {iniciar.isPending ? <span className="loading loading-spinner loading-xs" /> : <Upload size={14} />}
              Subir versión
            </button>
          )}
        </div>
      )}
    </>
  );

  return actoAdmin((abrirCrear) => tarjeta(abrirCrear, sinActo));
}
