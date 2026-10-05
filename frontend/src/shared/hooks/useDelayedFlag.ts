import { useEffect, useState } from "react";

/**
 * Devuelve `true` solo si `active` lleva al menos `delayMs` encendido.
 * Evita el parpadeo de un spinner en cargas rápidas:
 *
 *   const showSpinner = useDelayedFlag(isPending, 300);
 *   if (showSpinner) return <Spinner />;
 *   if (isPending) return <div className="min-h-[200px]" />; // hueco sin spinner
 */
export function useDelayedFlag(active: boolean, delayMs = 300): boolean {
  const [delayed, setDelayed] = useState(false);

  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => setDelayed(true), delayMs);
    return () => {
      clearTimeout(timer);
      setDelayed(false);
    };
  }, [active, delayMs]);

  return active && delayed;
}
