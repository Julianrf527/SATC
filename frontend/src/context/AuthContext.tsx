import { createContext, useContext } from "react";

export type User = {
  id: number;
  rol: string;
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