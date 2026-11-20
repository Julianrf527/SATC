import { useState } from "react";
import { AlertTriangle, DatabaseZap, Undo2 } from "lucide-react";
import { getErrorMessage } from "@shared/lib/api";
import { uploadFileToDocuments } from "@shared/lib/fileUpload";
import { Modal } from "@shared/ui";
import { detalleError } from "../api/errors";
import {
  useCambiarModoMutation,
  useCargueManualMutation,
  useDisponiblesQuery,
  useImpactoCambioModoQuery,
} from "../api/informes";
import { CampoFecha, CampoOpciones, CampoPdf, Seccion } from "../etapas/campos/Campos";
import ModalFormulario from "../etapas/ModalFormulario";
import type { InformeTecnico } from "../types";
import ImpactoCascada from "./ImpactoCascada";
import MatrizRecursosEditor from "./MatrizRecursosEditor";
import { errorMatriz, matrizInicial, normalizarMatriz } from "./recursos";

type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

type Props = {
  informe: InformeTecnico;
  /** Nombre del documento ("Informe técnico de visita"...). */
  titulo: string;
  setToast: SetToast;
  onClose: () => void;
};

/**
 * Cargue directo del informe técnico (como `SuperCargueModal` de recurso):
 * informe ya aceptado fuera del sistema (expedientes históricos), sin
 * asignación ni revisión. Si el informe está en el flujo normal, al cargar
 * pasa a modo MANUAL (PUT .../cambiar-modo): se descarta lo del flujo y se
 * eliminan en cascada las etapas posteriores, que se listan antes. Luego
 * POST .../cargue-manual. En VISITA la matriz de recursos es obligatoria.
 */
export default function SuperCargueInformeModal({ informe, titulo, setToast, onClose }: Props) {
  const esFlujo = informe.modo === "FLUJO";
  const yaCargado = !esFlujo && !!informe.documento_informe_id;
  const disponibles = useDisponiblesQuery(true);
  const cargue = useCargueManualMutation(informe.id);
  const cambiarModo = useCambiarModoMutation(informe.id, informe.expediente_id);
  const impacto = useImpactoCambioModoQuery(informe.id, esFlujo);

  const [archivo, setArchivo] = useState<File | null>(null);
  const [fechaRecibido, setFechaRecibido] = useState(yaCargado ? (informe.fecha_recibido_informe ?? "") : "");
  const [fechaAceptacion, setFechaAceptacion] = useState(yaCargado ? (informe.fecha_aceptacion_informe ?? "") : "");
  const [fechaProgramacion, setFechaProgramacion] = useState(yaCargado ? (informe.fecha_programacion_visita ?? "") : "");
  const [profesionalId, setProfesionalId] = useState<number | "">(yaCargado ? (informe.profesional_asignado_id ?? "") : "");
  const [revisorId, setRevisorId] = useState<number | "">(yaCargado ? (informe.revisor_asignado_id ?? "") : "");
  const conMatriz = informe.tipo_informe?.toUpperCase() === "VISITA";
  const [filas, setFilas] = useState(() => matrizInicial(yaCargado ? informe.recursos_afectados : null));
  const [error, setError] = useState<string | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [volverFlujo, setVolverFlujo] = useState(false);
  const ocupado = subiendo || cargue.isPending || cambiarModo.isPending;

  const guardar = async () => {
    if (!archivo && !yaCargado) return setError("Seleccione el informe aceptado (PDF)");
    if (archivo && !/\.pdf$/i.test(archivo.name)) return setError("El informe técnico debe cargarse en PDF");
    if (!fechaRecibido || !fechaAceptacion) return setError("Complete la fecha de recibido y de aceptación");
    if (fechaAceptacion < fechaRecibido) return setError("La fecha de aceptación no puede ser anterior a la de recibido");
    if (profesionalId && profesionalId === revisorId) return setError("El técnico y el líder técnico deben ser personas distintas");
    const matrizInvalida = conMatriz ? errorMatriz(filas) : null;
    if (matrizInvalida) return setError(matrizInvalida);
    if (esFlujo && (impacto.isPending || impacto.isError)) {
      return setError("Espere a conocer qué etapas posteriores se eliminarán");
    }
    setError(null);

    let fileId = informe.documento_informe_id ?? 0;
    setSubiendo(true);
    try {
      if (archivo) fileId = await uploadFileToDocuments(archivo, archivo.name);
      // Del flujo normal a cargue manual (descarta el flujo y la cascada listada).
      if (esFlujo) await cambiarModo.mutateAsync("MANUAL");
      await cargue.mutateAsync({
        file_id: fileId,
        fecha_recibido: fechaRecibido,
        fecha_aceptacion: fechaAceptacion,
        ...(fechaProgramacion ? { fecha_programacion_visita: fechaProgramacion } : {}),
        ...(profesionalId ? { profesional_id: profesionalId } : {}),
        ...(revisorId ? { revisor_id: revisorId } : {}),
        ...(conMatriz ? { recursos_afectados: normalizarMatriz(filas) } : {}),
      });
      setToast({ id: Date.now(), message: "Cargue directo realizado", type: "success" });
      onClose();
    } catch (e) {
      setError(detalleError(e) ?? getErrorMessage(e, "Error en el cargue directo"));
    } finally {
      setSubiendo(false);
    }
  };

  const profesionales = disponibles.data?.profesionales ?? [];
  const revisores = disponibles.data?.revisores ?? [];

  return (
    <>
      <ModalFormulario
        titulo="Cargue directo (super gestión)"
        subtitulo={titulo}
        icono={<DatabaseZap size={20} />}
        ocupado={ocupado}
        error={error}
        textoGuardar="Cargar"
        onGuardar={() => void guardar()}
        onClose={onClose}
        size="4xl"
      >
        <p className="text-sm text-base-content/70">
          Cargue de expedientes históricos: informe ya aceptado fuera del sistema. No pasa por asignación ni revisión.
          {yaCargado && " Solo se actualizan los datos que modifique."}
        </p>

        {esFlujo && (
          <div className="space-y-3">
            <div role="alert" className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
              <AlertTriangle size={16} className="text-tono-warning shrink-0 mt-0.5" aria-hidden />
              <p className="text-base-content/80">
                El informe está en el <span className="font-semibold text-base-content">flujo normal</span>: al cargar
                pasa a cargue manual y se descarta lo del flujo (técnico y líder asignados, fechas y el proceso de
                revisión). No se puede deshacer.
              </p>
            </div>
            <ImpactoCascada
              cargando={impacto.isPending}
              error={impacto.isError ? (detalleError(impacto.error) ?? "No se pudo calcular qué más se eliminaría") : null}
              etapas={impacto.data ?? []}
            />
          </div>
        )}

        <Seccion titulo="Informe aceptado">
          <CampoPdf
            etiqueta="Informe técnico (PDF)"
            archivo={archivo}
            onChange={(a) => {
              setArchivo(a);
              setError(null);
            }}
            requerido={!yaCargado}
            actualId={yaCargado ? informe.documento_informe_id : null}
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CampoFecha etiqueta="Fecha de recibido" valor={fechaRecibido} onChange={setFechaRecibido} requerido />
            <CampoFecha etiqueta="Fecha de aceptación" valor={fechaAceptacion} onChange={setFechaAceptacion} requerido />
            <CampoFecha etiqueta="Programación de visita" valor={fechaProgramacion} onChange={setFechaProgramacion} />
          </div>
        </Seccion>

        <Seccion titulo="Técnico y líder técnico (opcional)">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CampoOpciones
              etiqueta="Técnico que cargó"
              valor={profesionalId}
              opciones={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
              onChange={setProfesionalId}
              placeholder="Sin asignar"
            />
            <CampoOpciones
              etiqueta="Líder técnico"
              valor={revisorId}
              opciones={revisores.map((r) => ({ value: r.id, label: r.nombre }))}
              onChange={setRevisorId}
              placeholder="Sin asignar"
            />
          </div>
        </Seccion>

        {conMatriz && (
          <Seccion titulo="Recursos afectados">
            <p className="text-xs text-base-content/60">
              Obligatoria. Marque la magnitud del recurso afectado y su reversibilidad. Los recursos sin magnitud quedan
              como "No existe".
            </p>
            <MatrizRecursosEditor filas={filas} onChange={setFilas} disabled={ocupado} />
          </Seccion>
        )}

        {!esFlujo && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-base-300">
            <p className="text-xs text-base-content/60">El informe está en cargue manual.</p>
            <button type="button" className="btn btn-ghost btn-xs gap-1" onClick={() => setVolverFlujo(true)}>
              <Undo2 size={12} />
              Volver al flujo normal
            </button>
          </div>
        )}
      </ModalFormulario>

      {volverFlujo && (
        <VolverFlujoModal
          informe={informe}
          setToast={setToast}
          onClose={() => setVolverFlujo(false)}
          onHecho={onClose}
        />
      )}
    </>
  );
}

type VolverProps = {
  informe: InformeTecnico;
  setToast: SetToast;
  onClose: () => void;
  /** Tras volver al flujo (cierra también el cargue directo). */
  onHecho: () => void;
};

/** Confirmación de volver al flujo normal: borra lo cargado y la cascada listada. */
function VolverFlujoModal({ informe, setToast, onClose, onHecho }: VolverProps) {
  const cambiarModo = useCambiarModoMutation(informe.id, informe.expediente_id);
  const impacto = useImpactoCambioModoQuery(informe.id, true);

  const confirmar = () =>
    cambiarModo.mutate("FLUJO", {
      onSuccess: (res) => {
        const eliminadas = (res.etapas_eliminadas ?? []).map((e) => e.etiqueta);
        setToast({
          id: Date.now(),
          message: eliminadas.length
            ? `Cambiado a flujo normal. También se eliminó: ${eliminadas.join(", ")}`
            : "Cambiado a flujo normal",
          type: "success",
        });
        onClose();
        onHecho();
      },
      onError: (e) => setToast({ id: Date.now(), message: detalleError(e) ?? "Error al cambiar el modo", type: "error" }),
    });

  return (
    <Modal
      isOpen
      onClose={onClose}
      size="md"
      icon={<Undo2 size={20} />}
      title="Volver al flujo normal"
      closeOnEsc={!cambiarModo.isPending}
      closeOnBackdrop={!cambiarModo.isPending}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={cambiarModo.isPending}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-warning btn-sm text-white"
            onClick={confirmar}
            disabled={cambiarModo.isPending || impacto.isPending || impacto.isError}
          >
            {cambiarModo.isPending && <span className="loading loading-spinner loading-xs" />}
            Sí, volver al flujo
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-base-content/70">
          Se elimina lo cargado manualmente (archivo, fechas, técnico y líder) y el informe vuelve a asignarse y revisarse
          por el flujo normal. No se puede deshacer. ¿Continuar?
        </p>
        <ImpactoCascada
          cargando={impacto.isPending}
          error={impacto.isError ? (detalleError(impacto.error) ?? "No se pudo calcular qué más se eliminaría") : null}
          etapas={impacto.data ?? []}
        />
      </div>
    </Modal>
  );
}
