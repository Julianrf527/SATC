import type { InformeTecnico } from "../../../../types/infraccionApp";

// ── Helpers de semáforo ──────────────────────────────────────────────────────

function calcFechaLimiteHabiles(start: Date, dias: number): Date {
  const colombiaHolidays = new Set([
    "01-01","01-06","03-19","04-17","04-18","05-01","05-29","06-19","06-30",
    "07-04","07-20","08-07","08-18","10-13","11-03","11-17","12-08","12-25",
  ]);
  let count = 0;
  const current = new Date(start);
  while (count < dias) {
    current.setDate(current.getDate() + 1);
    const dow = current.getDay();
    const mmdd = `${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`;
    if (dow !== 0 && dow !== 6 && !colombiaHolidays.has(mmdd)) count++;
  }
  return current;
}

type SemaforoColor = "verde" | "amarillo" | "rojo";

function calcSemaforo(
  inicio: Date,
  limite: Date,
  hoy: Date = new Date(),
): { color: SemaforoColor; pct: number; diasRestantes: number; vencido: boolean } {
  const total = Math.max((limite.getTime() - inicio.getTime()) / 86400000, 1);
  const transcurridos = (hoy.getTime() - inicio.getTime()) / 86400000;
  const pct = Math.min((transcurridos / total) * 100, 100);
  const diasRestantes = Math.max(Math.ceil((limite.getTime() - hoy.getTime()) / 86400000), 0);
  const vencido = hoy > limite;
  const color: SemaforoColor = vencido || pct >= 80 ? "rojo" : pct >= 50 ? "amarillo" : "verde";
  return { color, pct, diasRestantes, vencido };
}

const SEMAFORO_DOT: Record<SemaforoColor, string> = {
  verde: "bg-success",
  amarillo: "bg-warning",
  rojo: "bg-error",
};

const SEMAFORO_TEXT: Record<SemaforoColor, string> = {
  verde: "text-success",
  amarillo: "text-warning",
  rojo: "text-error",
};

/**
 * Celda "Prioridad": muestra hasta dos semáforos (asignación y revisión).
 */
export default function PrioridadCell({ informe }: { informe: InformeTecnico }) {
  const hoy = new Date();
  const inicio = new Date(informe.fecha_creacion);
  const items: React.ReactNode[] = [];

  // 1. Semáforo asignación: 25 días hábiles para asignar profesional
  if (!informe.profesional_asignado_id && !informe.aceptado) {
    const limite = calcFechaLimiteHabiles(inicio, 25);
    const s = calcSemaforo(inicio, limite, hoy);
    items.push(
      <div key="asig" className="flex items-center gap-1" title={`Asignar profesional: ${s.diasRestantes}d restantes`}>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${SEMAFORO_DOT[s.color]}`} />
        <span className={`text-[10px] font-medium ${SEMAFORO_TEXT[s.color]}`}>
          {s.vencido ? "¡Asig. vencida!" : `Asignar ${s.diasRestantes}d`}
        </span>
      </div>
    );
  }

  // 2. Semáforo revisión: 30 días calendario desde fecha_creacion cuando proceso_activo
  if (informe.proceso_activo && !informe.aceptado) {
    const limite30 = new Date(inicio);
    limite30.setDate(limite30.getDate() + 30);
    const s = calcSemaforo(inicio, limite30, hoy);
    items.push(
      <div key="rev" className="flex items-center gap-1" title={`Revisión doc: ${s.diasRestantes}d restantes (30 días)`}>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${SEMAFORO_DOT[s.color]}`} />
        <span className={`text-[10px] font-medium ${SEMAFORO_TEXT[s.color]}`}>
          {s.vencido ? "¡Revisión vencida!" : `Revisar ${s.diasRestantes}d`}
        </span>
      </div>
    );
  }

  return items.length > 0
    ? <div className="flex flex-col gap-1">{items}</div>
    : <span className="text-[10px] text-base-content/30">—</span>;
}
