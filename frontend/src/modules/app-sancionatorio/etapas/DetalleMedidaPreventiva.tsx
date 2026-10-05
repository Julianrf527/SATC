import {
  useImportarMedidaMutation,
  useMigracionMedidaQuery,
  useTiposMedidaQuery,
} from "../api/etapas";
import type { EtapaMedida, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import Icono from "./comun/Icono";
import { ICONOS } from "./comun/iconos";
import MedidaPreventivaData from "./medida-preventiva/MedidaPreventivaData";

type Props = {
  expedienteId: number;
  radicado?: string;
  setToast: SetToast;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "DETALLE MEDIDA PREVENTIVA";
const TIPOS_DOCUMENTO = ["Informe Tecnico", "Solicitud Revocatoria Directa"];

export default function DetalleMedidaPreventiva({
  expedienteId,
  radicado,
  setToast,
  onStageUpdate,
  isEditable = true,
}: Props) {
  const { data: tiposMedidaList = [] } = useTiposMedidaQuery();
  const etapa = useEtapaSancionatoria<EtapaMedida>({
    etapa: "medida",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al obtener la medida preventiva.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "avisar",
  });
  const datos = etapa.datos;

  // Si la etapa aún no existe, buscar datos migrables desde infracciones.
  const migracionQuery = useMigracionMedidaQuery(
    radicado,
    !etapa.cargando && !etapa.etapaExiste && !!expedienteId,
  );
  const migracion = migracionQuery.data ?? null;
  const importar = useImportarMedidaMutation(expedienteId);

  const handleImportar = () => {
    if (!migracion || !expedienteId) return;
    importar.mutate(migracion, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Datos importados desde infracciones exitosamente", type: "success" });
        onStageUpdate(STAGE_NAME);
      },
      onError: (e) =>
        setToast({
          id: Date.now(),
          message: e.message || "Error al importar datos desde infracciones",
          type: "error",
        }),
    });
  };

  const panelMigracion = migracion && isEditable && (
    <div className="mt-4 rounded-xl border border-info/30 bg-info/5 overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="w-8 h-8 rounded-lg bg-info/15 flex items-center justify-center flex-shrink-0">
          <Icono d={ICONOS.info} className="w-4 h-4 text-info" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-base-content">
            Datos disponibles desde el proceso de Infracciones
          </p>
          <p className="text-xs text-base-content/60 mt-0.5 leading-relaxed">
            Se encontró una medida preventiva registrada en el expediente de infracciones con el mismo radicado.
            {migracion.informe_tecnico_documento_id && " También se adjuntará el informe técnico de visita aprobado."}
          </p>
        </div>
      </div>
      <div className="border-t border-info/20 px-4 py-2.5 flex justify-end bg-info/5">
        <button
          className="btn btn-info btn-sm text-white gap-2"
          onClick={handleImportar}
          disabled={importar.isPending || etapa.creando}
        >
          {importar.isPending ? (
            <>
              <span className="loading loading-spinner loading-xs" />
              Importando...
            </>
          ) : (
            <>
              <Icono d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              Importar desde Infracciones
            </>
          )}
        </button>
      </div>
    </div>
  );

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la medida preventiva"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar la medida preventiva correspondiente."
      icono={ICONOS.escudo}
      isEditable={isEditable}
      cargando={etapa.cargando}
      mostrarCarga={etapa.mostrarCarga}
      etapaExiste={etapa.etapaExiste}
      creable={etapa.creable}
      creando={etapa.creando}
      onCrear={etapa.crearEtapa}
      extraCrear={panelMigracion}
    >
      <EtapaActoDocumentos
        expedienteId={expedienteId}
        etapaId={etapa.etapaId ?? 0}
        tipoEtapa="etapa_medida_preventiva"
        tipoBinding="etapa_san_medida_preventiva"
        tipoActo="comunicacion"
        acto={datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={etapa.setDocumentos}
        setToast={setToast}
        isEditable={isEditable}
        avisoSinActo={{
          titulo: "Información y documentos no disponibles",
          texto: "Debe crear un acto administrativo antes de registrar información o subir documentos.",
        }}
        informacion={
          <MedidaPreventivaData
            data={
              datos?.etapa_id
                ? {
                    id: datos.etapa_id,
                    tipo_medida_id: datos.tipo_medida_id ?? undefined,
                    cantidad: datos.cantidad ?? undefined,
                    especie: datos.especie ?? undefined,
                    estado_medida: datos.estado_medida ?? null,
                  }
                : null
            }
            tipoMedida={tiposMedidaList}
            setToast={setToast}
            etapaId={etapa.etapaId ?? 0}
            expedienteId={expedienteId}
            isEditable={isEditable}
          />
        }
      />
    </EtapaContenedor>
  );
}
