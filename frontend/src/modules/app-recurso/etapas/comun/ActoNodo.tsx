import { ActoAdmin, type TipoActo } from "@features/acto-administrativo";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";
import { useInvalidarExpediente } from "../../api/invalidar";
import type { ActoEtapa, VinculoInvolucrado } from "../../types";
import { RECURSO_ACTO_ENDPOINTS, RECURSO_ACTO_ENDPOINTS_SOLO_NOTIFICACION } from "../actoAdminEndpoints";
import type { EntornoEtapa } from "../tipos";
import { actoParaFeature, claveActo, notificablesDe, seComunica } from "./actoFeature";
import { useEscritura } from "./useEscritura";

type Props = {
  entorno: EntornoEtapa;
  acto: ActoEtapa;
  /** Vínculos notificables (solicitantes + terceros intervinientes). */
  vinculos: VinculoInvolucrado[];
};

/**
 * Acto administrativo de un nodo con su comunicación y notificaciones, usando
 * `ActoAdmin` de la feature sin cambios. El acto lo crea "Cargar versión
 * final" de la etapa: aquí solo se corrige, comunica, notifica y (super
 * gestión) elimina. Editable solo si el backend manda `editar_acto`.
 * Comunicación o notificación lo decide el tipo del acto (`seComunica`).
 */
export default function ActoNodo({ entorno, acto, vinculos }: Props) {
  const { expediente, catalogos, setToast, isEditable } = entorno;
  const conComunicacion = seComunica(acto.tipo_acto);
  const tipoActo: TipoActo = conComunicacion ? "comunicacion" : "notificacion";
  const recargar = useInvalidarExpediente(expediente.id);
  const { ejecutar } = useEscritura(expediente.id, setToast);
  const editable = isEditable && acto.acciones_disponibles.includes("editar_acto");

  // La feature ofrece "Eliminar" a quien puede editar; el backend solo lo
  // permite a super gestión (`eliminar_acto`).
  const eliminar = async () => {
    if (!acto.acciones_disponibles.includes("eliminar_acto")) {
      setToast({
        id: Date.now(),
        message: "Solo super gestión puede eliminar el acto; para corregirlo use Editar",
        type: "error",
      });
      return;
    }
    ejecutar(
      {
        peticion: () => ({
          url: `${RECURSO_ENDPOINTS.RECURSO_ACTO_ADMIN_DELETE(acto.id)}?expediente_id=${expediente.id}`,
          method: "DELETE",
        }),
      },
      { exito: "Acto administrativo eliminado", error: "Error al eliminar el acto" },
    );
  };

  return (
    <ActoAdmin
      key={`${tipoActo}-${claveActo(acto)}`}
      expedienteId={expediente.id}
      actoAdmin={actoParaFeature(acto)}
      etapaId={acto.etapa_id}
      tipoActo={tipoActo}
      setToast={setToast}
      isEditable={editable}
      involucrados={notificablesDe(vinculos)}
      tiposNotificacion={catalogos.tipos_notificacion}
      onActoAdminUpdate={() => void recargar()}
      customDeleteHandler={eliminar}
      endpoints={conComunicacion ? RECURSO_ACTO_ENDPOINTS : RECURSO_ACTO_ENDPOINTS_SOLO_NOTIFICACION}
      embedded
    />
  );
}
