import { useState, useEffect } from "react";

type Props = {
  message: string | { detail?: string; message?: string } | null | undefined;
  type?: "success" | "error";
  duration?: number;
  id: number; 
};

export default function Toast({
  message,
  type = "success",
  duration = 4000,
  id,
}: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!message) return;
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), duration);
    return () => clearTimeout(timer);
    // Depende de id y no de message: dos toasts con el mismo texto deben re-mostrarse.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, duration]);

  if (!visible) return null;

  const displayMessage = typeof message === 'string' 
    ? message 
    : message?.detail || message?.message || JSON.stringify(message);

  return (
    <div className="toast fixed z-50">
      <div
        className={`alert ${type === "error" ? "alert-error" : "alert-success"}`}
      >
        <span>{displayMessage}</span>
      </div>
    </div>
  );
}
