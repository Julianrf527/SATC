import type { RefObject } from "react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import type { Ejecucion, TipoArchivoEjecucion } from "../../types";
import AccionesFormulario from "../comun/AccionesFormulario";
import Icono from "../comun/Icono";
import { ICONOS, PDF_RELLENO_20 } from "../comun/iconos";
import type { EjecucionFormState } from "./useEjecucionForm";

type Props = {
  data: Ejecucion | undefined;
  form: EjecucionFormState;
  onCancel: () => void;
  onViewDocument: (documentId: number) => void;
};

type FilaProps = {
  nombre: "cobro_coactivo" | "ruia" | "memorando";
  etiqueta: string;
  icono: string;
  marcado: boolean | undefined;
  documentoId: number | null | undefined;
  /** Color del icono "ver actual". */
  claseVer: string;
  inputRef: RefObject<HTMLInputElement | null>;
  archivo: File | null;
  isLoading: boolean;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>, tipo: TipoArchivoEjecucion) => void;
  onViewDocument: (documentId: number) => void;
};

/** Fila "casilla + archivo PDF + ver actual" de un documento de ejecución. */
function FilaDocumento({
  nombre,
  etiqueta,
  icono,
  marcado,
  documentoId,
  claseVer,
  inputRef,
  archivo,
  isLoading,
  onFileChange,
  onViewDocument,
}: FilaProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center gap-4 pb-4 border-b border-base-300">
      <div className="flex items-center gap-3 min-w-[200px]">
        <Icono d={icono} className="w-5 h-5 text-base-content/60" />
        <label className="label cursor-pointer gap-2 p-0">
          <input
            type="checkbox"
            name={nombre}
            defaultChecked={marcado}
            className="checkbox checkbox-primary"
            disabled={isLoading}
          />
          <span className="text-sm text-base-content font-medium">{etiqueta}</span>
        </label>
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => onFileChange(e, nombre)}
            className="file-input file-input-sm flex-1"
            disabled={isLoading}
          />
          {archivo && <span className="badge badge-success badge-sm">Nuevo archivo</span>}
          {documentoId && (
            <button
              type="button"
              onClick={() => onViewDocument(documentoId)}
              className="btn btn-sm btn-ghost text-tono-info"
              title="Ver actual"
            >
              <svg className={`w-5 h-5 ${claseVer}`} fill="currentColor" viewBox="0 0 20 20">
                <path d={PDF_RELLENO_20} />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const ICONO_MONEDA =
  "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z";
const ICONO_MENSAJE =
  "M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z";
const ICONO_DISPOSICION =
  "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10";

export default function EjecucionForm({ data, form, onCancel, onViewDocument }: Props) {
  const { isLoading } = form;
  const fila = {
    isLoading,
    onFileChange: form.onFileChange,
    onViewDocument,
  };

  return (
    <form onSubmit={form.onSubmit} className="space-y-8">
      {/* Casillas con documentos */}
      <div className="bg-base-200/50 rounded-lg p-6 space-y-4">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <Icono d={ICONOS.documento} className="w-5 h-5 text-primary" />
          Documentos y Estado
        </h4>

        <FilaDocumento
          {...fila}
          nombre="cobro_coactivo"
          etiqueta="Cobro Coactivo"
          icono={ICONO_MONEDA}
          marcado={data?.cobro_coactivo}
          documentoId={data?.documento_cobro_id}
          claseVer="text-error"
          inputRef={form.inputRefs.cobro_coactivo}
          archivo={form.archivos.cobro_coactivo}
        />
        <FilaDocumento
          {...fila}
          nombre="ruia"
          etiqueta="RUIA"
          icono={ICONOS.documento}
          marcado={data?.ruia}
          documentoId={data?.documento_ruia_id}
          claseVer="text-tono-info"
          inputRef={form.inputRefs.ruia}
          archivo={form.archivos.ruia}
        />
        <FilaDocumento
          {...fila}
          nombre="memorando"
          etiqueta="Memorando"
          icono={ICONO_MENSAJE}
          marcado={data?.memorando}
          documentoId={data?.documento_memorando_id}
          claseVer="text-tono-info"
          inputRef={form.inputRefs.memorando}
          archivo={form.archivos.memorando}
        />

        {/* Disposición (sin documento) */}
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex items-center gap-3 min-w-[200px]">
            <Icono d={ICONO_DISPOSICION} className="w-5 h-5 text-base-content/60" />
            <label className="label cursor-pointer gap-2 p-0">
              <input
                type="checkbox"
                name="disposicion"
                defaultChecked={data?.disposicion}
                className="checkbox checkbox-primary"
                disabled={isLoading}
              />
              <span className="text-sm text-base-content font-medium">Disposición</span>
            </label>
          </div>
          <div className="flex-1">
            <p className="text-sm text-base-content/60 italic">Sin documento asociado</p>
          </div>
        </div>
      </div>

      {/* Acto Administrativo */}
      <div className="bg-base-200/50 rounded-lg p-6 space-y-4">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <Icono d={ICONOS.documento} className="w-5 h-5 text-primary" />
          Información del Acto Administrativo
          <span className="badge badge-error badge-sm text-white">Requerido</span>
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
                Tipo de Acto <span className="text-error">*</span>
              </span>
            </label>
            <CustomSelect
              hidePlaceholderOption
              value={form.autoTipo}
              onChange={form.setAutoTipo}
              disabled={isLoading}
              options={[
                { value: "AUTO", label: "AUTO" },
                { value: "RES", label: "RES" },
              ]}
            />
          </div>

          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
                Numerado (4 dígitos) <span className="text-error">*</span>
              </span>
            </label>
            <input
              type="text"
              value={form.autoNumero}
              onChange={form.onAutoNumeroChange}
              className="input w-full font-mono text-lg"
              placeholder="0000"
              maxLength={4}
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
                Fecha del Auto <span className="text-error">*</span>
              </span>
            </label>
            <CustomDateInput
              value={form.fechaAuto}
              onChange={form.setFechaAuto}
              max={new Date().toISOString().split("T")[0]}
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
                Documento del Auto (PDF) <span className="text-error">*</span>
              </span>
              {data?.documento_acto_administrativo_id && (
                <button
                  type="button"
                  onClick={() => onViewDocument(data.documento_acto_administrativo_id as number)}
                  className="text-xs text-error hover:underline flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d={PDF_RELLENO_20} />
                  </svg>
                  Ver actual
                </button>
              )}
            </label>
            <div className="flex items-center gap-2">
              <input
                ref={form.inputRefs.auto}
                type="file"
                accept=".pdf"
                onChange={(e) => form.onFileChange(e, "auto")}
                className="file-input w-full"
                disabled={isLoading}
              />
              {form.archivos.auto && <span className="badge badge-success badge-sm">Nuevo</span>}
            </div>
          </div>
        </div>
      </div>

      <AccionesFormulario
        onCancelar={data ? onCancel : undefined}
        textoGuardar={data ? "Guardar Cambios" : "Registrar Ejecución"}
        tono="primary"
        guardando={isLoading}
      />
    </form>
  );
}
