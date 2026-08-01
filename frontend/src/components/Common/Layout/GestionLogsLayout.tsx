import GestionLogsManager from "./GestionLogsManager.tsx";

type Props = {
  title: string;
  body?: string;
  endpoint: string;
  moduleName?: string;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function GestionLogsLayout(props: Props) {
  return <GestionLogsManager {...props} />;
}
