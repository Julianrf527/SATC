# Arquitectura del frontend SATC

Feature-Sliced liviano. React 19 + TS + Vite + Tailwind 4/daisyUI 5 + react-router 7 + TanStack Query 5.

```
src/
  main.tsx        entrada (index.html) → <AppProviders><App/></AppProviders>
  app/            App.tsx (rutas), router/ (RequirePermission), providers/ (Theme, QueryClient),
                  layout/ (MainLayout, WelcomeLayout, header/, slider/), index.css
  shared/         sin dominio: ui/, lib/ (api, format, toast, archivos), hooks/, context/, types/, assets/
  features/       piezas de dominio reutilizadas por varios módulos; API pública = index.ts
  modules/        app-documentos, app-infraccion, app-sancionatorio, app-involved, app-users
```

## Capas y reglas de import (ESLint las hace cumplir)

| Desde \ hacia | app | modules | features | shared |
|---|---|---|---|---|
| **app**      | ✓ | ✓ | ✓ (solo `@features/<x>`) | ✓ |
| **modules**  | ✗ | solo el propio (relativo) | ✓ (solo `@features/<x>`) | ✓ |
| **features** | ✗ | ✗ | solo la propia (relativo) | ✓ |
| **shared**   | ✗ | ✗ | ✗ | ✓ |

- **Alias**: `@app/*`, `@shared/*`, `@features/*`, `@modules/*` (tsconfig.app.json + vite.config.ts).
- **Dentro de un slice** (`modules/app-x`, `features/x`, `shared/ui`, `shared/lib`...) → rutas relativas.
  **Entre slices** → siempre alias. Un relativo que sale del slice (`../../otra-cosa`) es error de lint.
- Las features se importan **solo por su `index.ts`**: `import { ActoAdmin } from "@features/acto-administrativo"`.
- `features/proceso-revision`: prohibido referenciar flujos concretos (`informe_tecnico`, `origen`, `esInformeTecnico`...) — regla `no-restricted-syntax`.

## Convenciones de nombres

- Carpetas: **kebab-case en minúscula** (`etapas/`, `asignar-informes/`, `role-form/`, `acto-administrativo/`).
- Componentes: `PascalCase.tsx`, un componente principal por archivo. Hooks: `useCamelCase.ts`. Utilidades/config: `camelCase.ts`.
- Tipos del módulo en `modules/<x>/types.ts`. Tipos compartidos entre módulos en `shared/types/` (hoy: `common`, `involucrado`, `sancionatorio`).
- Tests unitarios `*.test.ts` junto al archivo (`npm run test:unit`); stories `*.stories.tsx` junto al componente.

Estructura sugerida de un módulo:
```
modules/app-x/
  api/          queryKeys.ts + hooks react-query (useXxxQuery / useXxxMutation)
  types.ts
  layout/       pantallas enrutadas (las que importa app/App.tsx)
  manage/ etapas/ table/ modal/ ...   (subcarpetas por área, kebab-case)
```

## features vs modules vs shared

- **shared**: no sabe qué es un expediente. Si el componente sirve en cualquier app (Modal, Badge, select, formatDate) → `shared`.
- **features**: tiene dominio SATC y lo usan **2+ módulos** (acto administrativo, involucrados de un expediente, alertas, auditoría, gestión de encargado, proceso de revisión). Una feature no importa otra feature; si dos comparten algo, eso baja a `shared`.
- **modules**: pantallas y lógica de un solo servicio/flujo. Si otro módulo lo necesita, se sube a `features` (no se importa entre módulos).

### Regla anti-banderas
Los componentes compartidos (`shared`, `features`) **no reciben booleanos por flujo o módulo** (`esInfraccion`, `esInformeTecnico`, `modo="sancionatorio"`...). Lo específico entra por:
- **slots/children** (`footer`, `acciones`, `renderExtra`),
- **adapters/config** inyectados por el módulo (endpoints, mapeos de estado → `{ etiqueta, tono }`, como `ActoAdminEndpoints` en `acto-administrativo`).

Las props booleanas de *comportamiento genérico* (`closeOnEsc`, `readOnly`) sí están bien.

## Piezas base (`shared`)

```ts
// tema reactivo (reemplaza MutationObserver sobre data-theme)
import { useTheme } from "@shared/hooks/useTheme";
const { theme, setTheme, toggleTheme, isDark } = useTheme();

// formato es-CO
import { formatDate, formatDateTime, formatFileSize } from "@shared/lib/format";
formatDate("2026-01-05")                      // "05/01/2026"
formatDate(v, { style: "long" })              // "5 de enero de 2026"
formatDate(null, { fallback: "No registrada" })
formatDateTime(iso, { seconds: true })        // "05/01/2026, 02:30:15 p. m."
formatFileSize(1536)                          // "1.5 KB"

// UI
import { Modal, EstadoBadge } from "@shared/ui";
<Modal isOpen onClose title="..." subtitle icon={<Upload size={20}/>} footer={<>...</>}
       size="md|sm|lg|xl|2xl|4xl|full" closeOnEsc closeOnBackdrop initialFocusRef>...</Modal>
<EstadoBadge etiqueta="Aceptado" tono="success|info|warning|error|neutral" icono={<CheckCircle size={12}/>} />

// API
import { apiCall, apiRequest, ApiError, API_CONFIG, INFRACTION_ENDPOINTS } from "@shared/lib/api";
```
`Modal` ya aplica `data-theme`, portal, Esc/fondo, foco + trampa de Tab, bloqueo de scroll y anidamiento (Esc cierra solo el de arriba).

## Capa de datos (react-query)

`QueryClient` en `app/providers/queryClient.ts` (staleTime 30 s, sin refetch al enfocar, sin reintentos en 4xx). Devtools solo en `npm run dev`.

`apiCall` **no lanza** en errores HTTP (devuelve `{ ok:false, detail }`); para react-query usa **`apiRequest<T>()`**, que lanza `ApiError(status, detail)` y conserva el manejo global de 401/403 y toasts.

Ejemplo real: `modules/app-users/api/roles.ts` (usado por `role/RolList.tsx`):
```ts
// modules/app-x/api/queryKeys.ts
export const usersKeys = { all: ["app-users"] as const, roles: () => [...usersKeys.all, "roles"] as const };

// modules/app-x/api/roles.ts
export function useRolesQuery() {
  return useQuery({
    queryKey: usersKeys.roles(),
    queryFn: async () => (await apiRequest<{ data?: RolResumen[] }>(USERS_ENDPOINTS.ROL_LIST)).data ?? [],
  });
}
export function useDeleteRolMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number | string) => apiRequest(USERS_ENDPOINTS.ROL_DELETE(id), { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: usersKeys.roles() }),
  });
}

// componente
const { data = [], isPending, error } = useRolesQuery();
```
Reglas: un archivo por recurso en `api/`; claves jerárquicas en `queryKeys.ts` empezando por el nombre del módulo; los componentes no llaman `apiCall` en `useEffect`; las mutaciones invalidan claves en vez de parchear estado local; toasts de éxito en el `onSuccess` del `mutate` del componente.

## Checklist de migración de un módulo

- [ ] `MutationObserver` / listener `themeChange` → `useTheme()` (o directamente `Modal`).
- [ ] `formatDate`/`formatFileSize` locales → `@shared/lib/format` (revisar `fallback` que usaba cada uno).
- [ ] `createPortal` + backdrop a mano → `Modal` de `@shared/ui`.
- [ ] Badges de estado a mano → `EstadoBadge` + mapa estado → `{ etiqueta, tono }` en el módulo.
- [ ] Tipos sueltos/inline → `modules/<x>/types.ts` (lo compartido, en `shared/types`).
- [ ] Componentes > 400 líneas partidos (vista / formulario / hook de lógica / subcomponentes).
- [ ] `apiCall` en `useEffect` → hooks `useXxxQuery`/`useXxxMutation` en `modules/<x>/api/`.
- [ ] Sin imports entre módulos ni rutas internas de features; sin banderas por flujo en lo compartido.
- [ ] `npx tsc -b`, `npm run build` y `npm run lint` sin errores nuevos.
