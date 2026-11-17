import type { SetToast } from "../types";
import RecursoWorkspace from "../manage/RecursoWorkspace";

/** Pestaña Gestionar (/recurso/manage): `recurso_gestionar` o `recurso_super_gestion`. */
export default function GestionRecursoLayout({ setToast }: { setToast: SetToast }) {
  return <RecursoWorkspace setToast={setToast} isEditable />;
}
