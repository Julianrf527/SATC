import { useEffect, useState } from "react";

/** Devuelve `valor` después de `ms` sin cambios (búsqueda mientras se escribe). */
export function useValorDiferido<T>(valor: T, ms = 350): T {
  const [diferido, setDiferido] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setDiferido(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return diferido;
}
