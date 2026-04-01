import { createContext, useContext } from "react";

export type User = {
  user_id: number;
  primer_nombre: string;
  segundo_nombre: string;
  primer_apellido: string;
  segundo_apellido: string;
  correo: string;
  permisos: { name: string; path: string }[];
};

type AuthContextType = {
  user: User | null | undefined;
  setUser: (user: User | null) => void;
};

const AuthContext = createContext<AuthContextType>({
  user: undefined,
  setUser: () => {},
});

export const useAuth = () => useContext(AuthContext);

export default AuthContext;