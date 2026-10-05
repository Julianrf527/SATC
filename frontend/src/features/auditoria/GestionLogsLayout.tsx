import GestionLogsManager from "./GestionLogsManager";
import type { AuditLogConfig, SetToast } from "./types";

type Props = {
  title: string;
  /** @deprecated No se usa; se conserva por compatibilidad. */
  body?: string;
  endpoint: string;
  moduleName?: string;
  setToast: SetToast;
  /** Config del módulo: param de documento, radicado y catálogos. */
  config: AuditLogConfig;
};

export default function GestionLogsLayout(props: Props) {
  return <GestionLogsManager {...props} />;
}
