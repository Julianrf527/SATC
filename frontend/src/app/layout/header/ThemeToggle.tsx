import { useTheme } from "@shared/hooks/useTheme";

// Rayos del sol: [x1, y1, x2, y2]
const SUN_RAYS = [
  [12, 1, 12, 3],
  [12, 21, 12, 23],
  [4.22, 4.22, 5.64, 5.64],
  [18.36, 18.36, 19.78, 19.78],
  [1, 12, 3, 12],
  [21, 12, 23, 12],
  [4.22, 19.78, 5.64, 18.36],
  [18.36, 5.64, 19.78, 4.22],
];

/** Interruptor claro/oscuro. El tema (y su persistencia) vive en ThemeProvider. */
export default function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className="tooltip tooltip-bottom" data-tip={isDark ? "Modo claro" : "Modo oscuro"}>
      <label className="swap swap-rotate btn btn-ghost btn-circle btn-sm">
        <input
          type="checkbox"
          checked={isDark}
          onChange={toggleTheme}
          aria-label="Cambiar tema"
        />

        {/* Sun icon */}
        <svg className="swap-off w-5 h-5 fill-warning" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="5" />
          {SUN_RAYS.map(([x1, y1, x2, y2]) => (
            <line
              key={`${x1}-${y1}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="currentColor"
              strokeWidth="2"
            />
          ))}
        </svg>

        {/* Moon icon */}
        <svg className="swap-on w-5 h-5 fill-info" viewBox="0 0 24 24">
          <path d="M21.64 13a9 9 0 11-9.64-9.64A7 7 0 0021.64 13z" />
        </svg>
      </label>
    </div>
  );
}
