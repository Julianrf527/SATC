import RoleManager from "../Role/RoleManager";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function RolesPermisosPage({ setToast }: Props) {
  return <RoleManager setToast={setToast} />;
}
