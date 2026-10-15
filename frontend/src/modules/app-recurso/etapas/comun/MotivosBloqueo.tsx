import { Lock } from "lucide-react";

/** Motivos (§6) por los que un sub-proceso aún no se puede crear. Solo pinta lo que manda el backend. */
export default function MotivosBloqueo({ motivos }: { motivos: string[] }) {
  if (motivos.length === 0) return null;
  return (
    <div className="bg-warning/10 border border-warning/30 rounded-lg p-3">
      <ul className="space-y-1">
        {motivos.map((m) => (
          <li key={m} className="text-sm flex items-start gap-2">
            <Lock size={14} className="text-tono-warning mt-0.5 shrink-0" aria-hidden />
            <span>{m}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
