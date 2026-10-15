type Props = {
  /** Número de expediente (CA 001-26) o `null` sin selección. */
  titulo: string | null;
  subtitulo?: string | null;
  /** Modo consulta: etiqueta "Modo Consulta". */
  modoConsulta: boolean;
  /** Botón "Descargar expediente completo" (según `acciones_disponibles`). */
  mostrarDescarga: boolean;
  isDownloading: boolean;
  onDownload: () => void;
};

/**
 * Cabecera del panel de detalle. Réplica de la de infraction
 * (manage/detalle-infraccion/DetalleHeader.tsx) con el número de expediente
 * y el radicado.
 */
export default function DetalleHeader({
  titulo,
  subtitulo,
  modoConsulta,
  mostrarDescarga,
  isDownloading,
  onDownload,
}: Props) {
  return (
    <div className="flex-shrink-0 bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <i className="bx bx-water text-success text-xl"></i>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                {titulo !== null ? "Concesión de aguas" : "Panel"}
              </p>
              <h1 className="text-lg font-bold text-base-content">
                {titulo !== null ? titulo : "Panel de Expedientes"}
                {titulo !== null && subtitulo && (
                  <span className="ml-2 text-sm font-medium text-base-content/60">· {subtitulo}</span>
                )}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {modoConsulta && titulo !== null && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-success/10 border border-success/30 rounded-lg">
                <i className="bx bx-show text-success text-base"></i>
                <span className="text-xs font-semibold text-success uppercase tracking-wide">Modo Consulta</span>
              </div>
            )}
            {mostrarDescarga && (
              <button
                type="button"
                onClick={onDownload}
                disabled={isDownloading}
                className="btn btn-success gap-2 shadow-lg text-white font-medium hover:scale-105 transition-transform"
                title="Descargar todos los documentos del expediente en un PDF"
              >
                {isDownloading ? (
                  <>
                    <span className="loading loading-spinner loading-sm"></span>
                    Generando PDF...
                  </>
                ) : (
                  <>
                    <i className="bx bx-download text-lg"></i>
                    Descargar expediente completo
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
