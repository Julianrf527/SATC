import type { SetToast } from "../types";
import RecursoWorkspace from "../manage/RecursoWorkspace";

/**
 * Pestaña Consulta (/recurso/consult, `recurso_consultar`): misma lista y
 * detalle en solo lectura + "Descargar expediente completo".
 */
export default function ConsultaRecursoLayout({ setToast }: { setToast: SetToast }) {
  return <RecursoWorkspace setToast={setToast} isEditable={false} />;
}
