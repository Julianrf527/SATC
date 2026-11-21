import { useEffect, useRef, useState } from "react";

/**
 * Devuelve `valor` después de `ms` sin cambios (búsqueda mientras se escribe).
 * Con `diferir`, solo espera cuando `diferir(anterior, nuevo)` es true; si no,
 * aplica el cambio de inmediato (p. ej. cambiar de página o de municipio).
 */
export function useValorDiferido<T>(valor: T, ms = 350, diferir?: (anterior: T, nuevo: T) => boolean): T {
  const [diferido, setDiferido] = useState(valor);
  const actual = useRef(diferido);
  const diferirRef = useRef(diferir);
  diferirRef.current = diferir;

  useEffect(() => {
    const aplicar = () => {
      actual.current = valor;
      setDiferido(valor);
    };
    if (diferirRef.current && !diferirRef.current(actual.current, valor)) {
      aplicar();
      return;
    }
    const t = setTimeout(aplicar, ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return diferido;
}
