import { type ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

type Props = {
  required: string | string[];
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

  const requiredList = (Array.isArray(required) ? required : [required]).map(norm);

  const hasPermission = (user.permisos ?? []).some((p) =>
    requiredList.includes(norm(p?.name)),
  );

  if (!hasPermission) {
    return <Navigate to="/" replace />;
  }

  return children;
}
