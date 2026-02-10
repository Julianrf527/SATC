import { type ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

type Props = {
  required: string;
  children: ReactElement;
};

function norm(v?: string) {
  return (v ?? "").trim().toLowerCase();
}

export default function RequirePermission({ required, children }: Props) {
  const { user } = useAuth();
  const location = useLocation();

  if (user === undefined) {
    return null;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const requiredNorm = norm(required);
  const isAdmin = user.rol === "admin";

  const hasPermission =
    isAdmin ||
    (user.permisos ?? []).some((p) => {
      const permisoName = norm(p?.name);
      return permisoName === requiredNorm;
    });

  if (!hasPermission) {
    return <Navigate to="/" replace />;
  }

  return children;
}
