import ItemSlider from "./ItemSlider";

type Props = {
  permission: { name: string; path: string }[];
};

const menuBase = [
  { iconName: "contact-book", title: "Administracion", prefix: "admin_" },
  { iconName: "user-circle", title: "Involucrados", prefix: "involucrado_" },
  { iconName: "file-detail", title: "Expedientes", prefix: "expediente_" },
  { iconName: "book-alt", title: "Documentos", prefix: "documento_" },
  { iconName: "calendar-alt", title: "Auditoría", prefix: "auditoria_" },
];

// Orden específico para el submenú de Expedientes
const ordenExpedientes = [
  "gestionar",
  "consultar",
  "alertas",
  "asignar",
  "involucrados",
];

export default function Slider({ permission }: Props) {
  const menuFiltrado = menuBase
    .map((cat) => {
      const subMenuPermitido = permission
        .filter((p) => p.name.startsWith(cat.prefix))
        .filter((p) => p.path && p.path.trim() !== "") // Excluir permisos sin menu_path
        .map((p) => ({
          name: formatearNombre(p.name, cat.prefix),
          url: p.path,
          originalName: p.name,
        }));

      // Aplicar orden específico para Expedientes
      if (cat.prefix === "expediente_") {
        subMenuPermitido.sort((a, b) => {
          const nombreA = a.name.toLowerCase();
          const nombreB = b.name.toLowerCase();
          const indexA = ordenExpedientes.indexOf(nombreA);
          const indexB = ordenExpedientes.indexOf(nombreB);

          // Si ambos están en el orden definido, comparar por índice
          if (indexA !== -1 && indexB !== -1) {
            return indexA - indexB;
          }
          // Si solo A está en el orden, A va primero
          if (indexA !== -1) return -1;
          // Si solo B está en el orden, B va primero
          if (indexB !== -1) return 1;
          // Si ninguno está en el orden, mantener orden original
          return 0;
        });
      }

      return { ...cat, subMenu: subMenuPermitido };
    })
    .filter((cat) => cat.subMenu.length > 0);

  return (
    <>
      {/* CSS optimizado para animaciones ultrarrápidas */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
          .slider-content {
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
          }
        `,
        }}
      />

      <div className="drawer-side transition-all duration-100 ease-out z-[9999]">
        <label htmlFor="my-drawer" className="drawer-overlay"></label>
        <div className="bg-base-100 text-base-content h-full w-72 shadow-xl border-r border-base-300 transform transition-transform duration-100 ease-out">
          {/* Header del menú */}
          <div className="sticky top-0 bg-base-100/95 backdrop-blur-sm border-b border-base-300 px-6 py-5 z-10">
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
