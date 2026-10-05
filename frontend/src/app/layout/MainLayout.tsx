import { memo, Suspense, useEffect, useMemo } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import Header from "./header/Header";
import Slider from "./slider/Slider";
import LoadingBar from "@shared/ui/LoadingBar";
import AuthContext from "@shared/context/AuthContext";
import { useMeQuery, useSetMe } from "../api/auth";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function MainLayout({ setToast }: Props) {
  const { data: user, isPending } = useMeQuery();
  const setUser = useSetMe();
  const navigate = useNavigate();

  // setToast se mantiene en la firma por compatibilidad con App (no se usa aquí).
  void setToast;

  useEffect(() => {
    if (!isPending && !user) {
      navigate("/login");
    }
  }, [isPending, user, navigate]);

  const authValue = useMemo(() => ({ user, setUser }), [user, setUser]);

  if (isPending) {
    return (
      <div className="min-h-screen bg-base-100 flex flex-col">
        <div className="fixed top-0 left-0 right-0 z-50">
          <LoadingBar />
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <AuthContext.Provider value={authValue}>
      <div className="drawer">
        <input id="my-drawer" type="checkbox" className="drawer-toggle" />

        <div className="drawer-content flex flex-col min-h-screen">
          <MemoHeader permission={user.permisos} />
          <div
            className="flex-1 bg-base-200 select-none focus:outline-none"
            tabIndex={-1}
          >
            {/* Pantallas cargadas con React.lazy (ver App.tsx) */}
            <Suspense fallback={<LoadingBar />}>
              <Outlet />
            </Suspense>
          </div>
        </div>

        <Slider permission={user.permisos} />
      </div>
    </AuthContext.Provider>
  );
}

// Evita re-renderizar el Header (y su stream SSE) en cada cambio del layout.
const MemoHeader = memo(Header);
