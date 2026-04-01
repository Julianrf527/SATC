type Execution = {
  id?: number;
  cobro_coactivo: boolean;
  documento_cobro_coactivo_id: number | null;
  disposicion: boolean;
  ruia: boolean;
  documento_ruia_id: number | null;
  memorando: boolean;
  documento_memorando_id: number | null;
  auto_admin: string;
  fecha_auto: string | null;
  documento_auto_id: number | null;
  etapa_id: number;
};

type Props = {
  data: Execution | undefined;
  isLoading: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  onViewDocument: (documentId: number) => void;
  onFileChange: (
    e: React.ChangeEvent<HTMLInputElement>,
    fileType: "cobro_coactivo" | "ruia" | "memorando" | "auto",
  ) => void;
  autoTipo: string;
  autoNumero: string;
  onAutoTipoChange: (value: string) => void;
  onAutoNumeroChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  cobroCoactivoInputRef: React.RefObject<HTMLInputElement | null>;
  ruiaInputRef: React.RefObject<HTMLInputElement | null>;
  memorandoInputRef: React.RefObject<HTMLInputElement | null>;
  autoInputRef: React.RefObject<HTMLInputElement | null>;
  cobroCoactivoFile: File | null;
  ruiaFile: File | null;
  memorandoFile: File | null;
  autoFile: File | null;
};

export default function ExecutionForm({
  data,
  isLoading,
  onSubmit,
  onCancel,
  onViewDocument,
  onFileChange,
  autoTipo,
  autoNumero,
  onAutoTipoChange,
  onAutoNumeroChange,
  cobroCoactivoInputRef,
  ruiaInputRef,
  memorandoInputRef,
  autoInputRef,
  cobroCoactivoFile,
  ruiaFile,
  memorandoFile,
  autoFile,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-8">
      {/* Checkboxes con documentos */}
      <div className="bg-base-200/50 rounded-lg p-6 space-y-4">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-primary"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Documentos y Estado
        </h4>

        {/* Cobro Coactivo */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 pb-4 border-b border-base-300">
          <div className="flex items-center gap-3 min-w-[200px]">
            <svg
              className="w-5 h-5 text-base-content/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <label className="label cursor-pointer gap-2 p-0">
              <input
                type="checkbox"
                name="cobro_coactivo"
                defaultChecked={data?.cobro_coactivo}
                className="checkbox checkbox-primary"
                disabled={isLoading}
              />
              <span className="label-text font-medium">Cobro Coactivo</span>
            </label>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <input
                ref={cobroCoactivoInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => onFileChange(e, "cobro_coactivo")}
                className="file-input file-input-sm file-input-bordered flex-1"
                disabled={isLoading}
              />
              {cobroCoactivoFile && (
                <span className="badge badge-success badge-sm">
                  Nuevo archivo
                </span>
              )}
              {data?.documento_cobro_coactivo_id && (
                <button
                  type="button"
                  onClick={() =>
                    onViewDocument(data.documento_cobro_coactivo_id!)
                  }
                  className="btn btn-sm btn-ghost text-info"
                  title="Ver actual"
                >
                  <svg
                    className="w-5 h-5 text-error"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* RUIA */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 pb-4 border-b border-base-300">
          <div className="flex items-center gap-3 min-w-[200px]">
            <svg
              className="w-5 h-5 text-base-content/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <label className="label cursor-pointer gap-2 p-0">
              <input
                type="checkbox"
                name="ruia"
                defaultChecked={data?.ruia}
                className="checkbox checkbox-primary"
                disabled={isLoading}
              />
              <span className="label-text font-medium">RUIA</span>
            </label>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <input
                ref={ruiaInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => onFileChange(e, "ruia")}
                className="file-input file-input-sm file-input-bordered flex-1"
                disabled={isLoading}
              />
              {ruiaFile && (
                <span className="badge badge-success badge-sm">
                  Nuevo archivo
                </span>
              )}
              {data?.documento_ruia_id && (
                <button
                  type="button"
                  onClick={() => onViewDocument(data.documento_ruia_id!)}
                  className="btn btn-sm btn-ghost text-info"
                  title="Ver actual"
                >
                  <svg
                    className="w-5 h-5 text-info"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Memorando */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 pb-4 border-b border-base-300">
          <div className="flex items-center gap-3 min-w-[200px]">
            <svg
              className="w-5 h-5 text-base-content/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
              />
            </svg>
            <label className="label cursor-pointer gap-2 p-0">
              <input
                type="checkbox"
                name="memorando"
                defaultChecked={data?.memorando}
                className="checkbox checkbox-primary"
                disabled={isLoading}
              />
              <span className="label-text font-medium">Memorando</span>
            </label>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <input
                ref={memorandoInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => onFileChange(e, "memorando")}
                className="file-input file-input-sm file-input-bordered flex-1"
                disabled={isLoading}
              />
              {memorandoFile && (
                <span className="badge badge-success badge-sm">
                  Nuevo archivo
                </span>
              )}
              {data?.documento_memorando_id && (
                <button
                  type="button"
                  onClick={() => onViewDocument(data.documento_memorando_id!)}
                  className="btn btn-sm btn-ghost text-info"
                  title="Ver actual"
                >
                  <svg
                    className="w-5 h-5 text-info"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Disposición */}
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex items-center gap-3 min-w-[200px]">
            <svg
              className="w-5 h-5 text-base-content/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
            <label className="label cursor-pointer gap-2 p-0">
              <input
                type="checkbox"
                name="disposicion"
                defaultChecked={data?.disposicion}
                className="checkbox checkbox-primary"
                disabled={isLoading}
              />
              <span className="label-text font-medium">Disposición</span>
            </label>
          </div>
          <div className="flex-1">
            <p className="text-sm text-base-content/60 italic">
              Sin documento asociado
            </p>
          </div>
        </div>
      </div>

      {/* Acto Administrativo */}
      <div className="bg-base-200/50 rounded-lg p-6 space-y-4">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-primary"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Información del Acto Administrativo
          <span className="badge badge-error badge-sm text-white">
            Requerido
          </span>
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Tipo de Acto <span className="text-error">*</span>
              </span>
            </label>
            <select
              value={autoTipo}
              onChange={(e) => onAutoTipoChange(e.target.value)}
              className="select select-bordered w-full"
              disabled={isLoading}
              required
            >
              <option value="AUTO">AUTO</option>
              <option value="RES">RES</option>
            </select>
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Numerado (4 dígitos) <span className="text-error">*</span>
              </span>
            </label>
            <input
              type="text"
              value={autoNumero}
              onChange={onAutoNumeroChange}
              className="input input-bordered w-full font-mono text-lg"
              placeholder="0000"
              maxLength={4}
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Fecha del Auto <span className="text-error">*</span>
              </span>
            </label>
            <input
              type="date"
              name="fecha_auto"
              defaultValue={data?.fecha_auto || ""}
              className="input input-bordered w-full"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Documento del Auto (PDF) <span className="text-error">*</span>
              </span>
              {data?.documento_auto_id && (
                <button
                  type="button"
                  onClick={() => onViewDocument(data.documento_auto_id!)}
                  className="label-text-alt text-error hover:underline flex items-center gap-1"
                >
                  <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                  </svg>
                  Ver actual
                </button>
              )}
            </label>
            <div className="flex items-center gap-2">
              <input
                ref={autoInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => onFileChange(e, "auto")}
                className="file-input file-input-bordered w-full"
                disabled={isLoading}
              />
              {autoFile && (
                <span className="badge badge-success badge-sm">Nuevo</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Botones */}
      <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
        {data && (
          <button
            type="button"
            onClick={onCancel}
            className="btn btn-outline"
            disabled={isLoading}
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          className="btn btn-primary text-white gap-2"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="loading loading-spinner loading-sm"></span>
              Guardando...
            </>
          ) : (
            <>
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {data ? "Guardar Cambios" : "Registrar Ejecución"}
            </>
          )}
        </button>
      </div>
    </form>
  );
}
