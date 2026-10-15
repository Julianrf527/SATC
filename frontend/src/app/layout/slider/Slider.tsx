import ItemSlider from "./ItemSlider";

type Props = {
  permission: { name: string; path: string }[];
};

const menuBase = [
  { iconName: "contact-book", title: "Administracion", prefix: "admin_" },
  { iconName: "file-detail", title: "Sancionatorio", prefix: "sancionatorio_" },
  { iconName: "gavel", title: "Infracciones", prefix: "infraccion_" },
  { iconName: "water", title: "Concesiones de Aguas", prefix: "recurso_" },
  { iconName: "book-alt", title: "Documentos", prefix: "documento_" },
  { iconName: "user-circle", title: "Involucrados", prefix: "involucrado_" },
  { iconName: "calendar-alt", title: "Auditoría", prefix: "auditoria_" },
];

// Orden específico para el submenú de Sancionatorio
const ordenSancionatorio = [
  "gestionar",
  "consultar",
  "alertas",
  "asignar",
  "involucrados",
];

const ordenInfracciones = [
  "gestionar",
  "consultar",
  "alertas",
  "asignar",
  "asignar informes",
  "mis informes",
  "involucrados",
];

// informes_subir e informes_revisar apuntan al mismo path (/infraction/my-reports)
// — si el usuario tiene ambos, deben colapsar en una sola entrada "Mis Informes".
const NOMBRES_MIS_INFORMES = ["informes subir", "informes revisar"];

// Concesiones de Aguas: los permisos de revisor y técnico apuntan todos a
// /recurso/my-reports (una sola entrada "Mis Informes"); recurso_gestionar
// también ve Mis Informes y recurso_super_gestion (sin menu_path) entra a
// Gestionar.
const RECURSO_RUTAS = {
  gestionar: "/recurso/manage",
  consultar: "/recurso/consult",
  misInformes: "/recurso/my-reports",
};

function menuRecurso(permission: { name: string; path: string }[]) {
  const nombres = new Set(permission.map((p) => p.name));
  const urls = new Set(
    permission.filter((p) => p.name.startsWith("recurso_") && p.path?.trim()).map((p) => p.path.trim()),
  );
  const gestiona = nombres.has("recurso_gestionar") || nombres.has("recurso_super_gestion");
  const items: { name: string; url: string; originalName: string }[] = [];
  if (gestiona || urls.has(RECURSO_RUTAS.gestionar))
    items.push({ name: "Gestionar", url: RECURSO_RUTAS.gestionar, originalName: "recurso_gestionar" });
  if (urls.has(RECURSO_RUTAS.consultar))
    items.push({ name: "Consultar", url: RECURSO_RUTAS.consultar, originalName: "recurso_consultar" });
  if (nombres.has("recurso_gestionar") || urls.has(RECURSO_RUTAS.misInformes))
    items.push({ name: "Mis Informes", url: RECURSO_RUTAS.misInformes, originalName: "recurso_mis_informes" });
  return items;
}

export default function Slider({ permission = [] }: Props) {
  const menuFiltrado = menuBase
    .map((cat) => {
      if (cat.prefix === "recurso_") return { ...cat, subMenu: menuRecurso(permission) };
      const subMenuPermitido = permission
        .filter((p) => p.name.startsWith(cat.prefix))
        .filter((p) => p.path && p.path.trim() !== "") // Excluir permisos sin menu_path
        .map((p) => ({
          name: formatearNombre(p.name, cat.prefix),
          url: p.path,
          originalName: p.name,
        }));

      if (cat.prefix === "sancionatorio_") {
        subMenuPermitido.sort((a, b) => {
          const nombreA = a.name.toLowerCase();
          const nombreB = b.name.toLowerCase();
          const indexA = ordenSancionatorio.indexOf(nombreA);
          const indexB = ordenSancionatorio.indexOf(nombreB);

          if (indexA !== -1 && indexB !== -1) {
            return indexA - indexB;
          }
          if (indexA !== -1) return -1;
          if (indexB !== -1) return 1;
          return 0;
        });
      }

      if (cat.prefix === "infraccion_") {
        const renombrado = subMenuPermitido.map((item) =>
          NOMBRES_MIS_INFORMES.includes(item.name.toLowerCase())
            ? { ...item, name: "Mis Informes" }
            : item,
        );
        const seen = new Set<string>();
        const sinDuplicados = renombrado.filter((item) => {
          if (item.name !== "Mis Informes") return true;
          if (seen.has(item.url)) return false;
          seen.add(item.url);
          return true;
        });
        sinDuplicados.sort((a, b) => {
          const nombreA = a.name.toLowerCase();
          const nombreB = b.name.toLowerCase();
          const indexA = ordenInfracciones.indexOf(nombreA);
          const indexB = ordenInfracciones.indexOf(nombreB);

          if (indexA !== -1 && indexB !== -1) {
            return indexA - indexB;
          }
          if (indexA !== -1) return -1;
          if (indexB !== -1) return 1;
          return 0;
        });
        return { ...cat, subMenu: sinDuplicados };
      }

      return { ...cat, subMenu: subMenuPermitido };
    })
    .filter((cat) => cat.subMenu.length > 0);

  return (
    <>
      {/* CSS optimizado para animaciones ultrarrápidas */}
      <style>{`
        .slider-content {
          scroll-behavior: smooth;
          -webkit-overflow-scrolling: touch;
        }
      `}</style>

      <div className="drawer-side transition-all duration-100 ease-out z-[9999]">
        <label htmlFor="my-drawer" className="drawer-overlay"></label>
        <div className="bg-base-100 text-base-content h-full w-72 shadow-xl border-r border-base-300 transform transition-transform duration-100 ease-out">
          {/* Header del menú */}
          <div className="sticky top-0 bg-base-100 border-b border-base-300 px-6 py-5 z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-bold">Menú de opciones</h2>
                <p className="text-xs text-base-content/60">
                  Navegación principal
                </p>
              </div>
            </div>
          </div>

          {/* Contenido del menú */}
          <div className="overflow-y-auto h-[calc(100%-88px)] overscroll-contain slider-content">
            <ul className="menu p-4 space-y-2">
              {menuFiltrado.length > 0 ? (
                menuFiltrado.map((cat) => (
                  <div key={cat.title}>
                    <ItemSlider
                      title={cat.title}
                      iconName={cat.iconName}
                      subMenu={cat.subMenu}
                    />
                  </div>
                ))
              ) : (
                <div className="text-center py-12 px-4">
                  <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
                    <svg
                      className="w-8 h-8 text-base-content/40"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-sm font-semibold text-base-content/70 mb-2">
                    Sin permisos
                  </h3>
                  <p className="text-xs text-base-content/60">
                    No cuenta con permisos asignados. Comuníquese con un
                    administrador.
                  </p>
                </div>
              )}
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}

function formatearNombre(nombre: string, prefix: string) {
  return nombre
    .replace(prefix, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}
