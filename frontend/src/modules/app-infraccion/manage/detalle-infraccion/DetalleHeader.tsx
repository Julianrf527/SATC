type Props = {
  radicado: string | null;
  /** Modo consulta: muestra la etiqueta y el botón de descarga. */
  mostrarDescarga: boolean;
  isDownloading: boolean;
  onDownload: () => void;
};

/** Cabecera del panel de detalle del expediente. */
export default function DetalleHeader({ radicado, mostrarDescarga, isDownloading, onDownload }: Props) {
  return (
    <div className="flex-shrink-0 bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <i className="bx bx-folder-open text-success text-xl"></i>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                {radicado !== null ? "Expediente Activo" : "Panel"}
              </p>
              <h1 className="text-lg font-bold text-base-content">
                {radicado !== null ? radicado : "Panel de Expedientes"}
              </h1>
            </div>
          </div>
          {mostrarDescarga && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-success/10 border border-success/30 rounded-lg">
                <i className="bx bx-show text-success text-base"></i>
                <span className="text-xs font-semibold text-success uppercase tracking-wide">Modo Consulta</span>
              </div>
              <button
                onClick={onDownload}
                disabled={isDownloading}
                className="btn btn-success gap-2 shadow-lg text-white font-medium hover:scale-105 transition-transform"
                title="Descargar todos los documentos del expediente"
              >
                {isDownloading ? (
                  <>
                    <span className="loading loading-spinner loading-sm"></span>
                    Generando PDF...
                  </>
                ) : (
                  <>
                    <i className="bx bx-download text-lg"></i>
                    Descargar Expediente
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
