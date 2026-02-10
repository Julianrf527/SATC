import { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { apiCall, API_CONFIG } from "../utils/api";
import React from "react";
import Header from "../components/Header/Header";
import Slider from "../components/Slider/Slider";
import LoadingBar from "../components/LoadingBar";
import AuthContext, { type User } from "../context/AuthContext";

type Props = {
  setTheme: (theme: "emerald" | "dark") => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function MainLayout({ setTheme }: Props) {
  const [loading, setLoading] = useState(true);
  // undefined = cargando, null = no autenticado, User = autenticado
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const navigate = useNavigate();

  useEffect(() => {
    async function verifyToken() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_ME, {
          method: "GET",
        });

        if (res.ok) {
          setUser(res.usuario);
        } else {
          setUser(null);
        }
      } catch (error) {
        console.error("Error al hacer fetch:", error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    verifyToken();
  }, []);

  useEffect(() => {
    if (!loading && user === null) {
      navigate("/login");
    }
  }, [loading, user, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-base-100 flex flex-col">
        <div className="fixed top-0 left-0 right-0 z-50">
          <LoadingBar />
        </div>
      </div>
    );
  }

  // Si no hay usuario (null o undefined), no renderiza nada
  if (!user) {
    return null;
  }

  // En este punto TypeScript sabe que user es de tipo User
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      <div className="drawer">
        <input id="my-drawer" type="checkbox" className="drawer-toggle" />

        <div className="drawer-content flex flex-col min-h-screen">
          <HeaderWrapper
            userId={user.id}
            setTheme={setTheme}
            permission={user.permisos}
          />
          <div
            className="flex-1 bg-base-200 select-none focus:outline-none"
            tabIndex={-1}
          >
            <Outlet />
          </div>
        </div>

        <Slider permission={user.permisos} />
      </div>
    </AuthContext.Provider>
  );
}

// Wrapper para evitar renderizado innecesario del Header
const HeaderWrapper = React.memo(
  ({
    userId,
    setTheme,
    permission,
  }: {
    userId: number;
    setTheme: (theme: "emerald" | "dark") => void;
    permission: { name: string; path: string }[];
  }) => {
    return (
      <Header userId={userId} setTheme={setTheme} permission={permission} />
    );
  }
);
