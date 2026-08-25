import { Shield } from "lucide-react";
import RoleManager from "../Role/RoleManager";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function RolesPermisosPage({ setToast }: Props) {
  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <Shield className="text-primary" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  Módulo de Usuarios
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Gestión de Roles y Permisos
                </h1>
                <p className="text-xs text-base-content/50 hidden sm:block">
                  Administra los roles y los permisos asignados a cada uno
                </p>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2">
              <div className="badge badge-primary badge-outline gap-1 py-3 px-3">
                <Shield size={12} />
                <span className="text-xs font-semibold">Control de acceso</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <RoleManager setToast={setToast} />
    </>
  );
}
