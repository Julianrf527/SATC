import { Link } from "react-router-dom";

type SubMenu = {
  name: string;
  url: string;
};

type Props = {
  iconName: string;
  title: string;
  subMenu: SubMenu[];
};

export default function ItemSlider({ iconName, title, subMenu }: Props) {
  const cerrarDrawer = () => {
    const drawerCheckbox = document.getElementById(
      "my-drawer",
    ) as HTMLInputElement;
    if (drawerCheckbox) drawerCheckbox.checked = false;
  };

  return (
    <li>
      <details className="group">
        <summary className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-base-200 transition-colors cursor-pointer list-none [&::-webkit-details-marker]:hidden [&::marker]:hidden [&::after]:hidden">
          {/* Icono */}
          <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center group-hover:bg-success/10 transition-colors">
            <div
              className="w-5 h-5 bg-base-content/70 group-hover:bg-base-content transition-colors"
              style={{
                WebkitMask: `url(/icons/${iconName}.png) no-repeat center`,
                WebkitMaskSize: "contain",
                mask: `url(/icons/${iconName}.png) no-repeat center`,
                maskSize: "contain",
              }}
            ></div>
          </div>

          {/* Título */}
          <span className="flex-1 font-semibold text-sm">{title}</span>

          {/* Badge contador */}
          <span className="badge badge-sm badge-ghost">{subMenu.length}</span>

          {/* Indicador de expansión personalizado */}
          <svg
            className="w-4 h-4 transition-transform group-open:rotate-90 text-base-content/50"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l6 7-6 7"
            />
          </svg>
        </summary>

        {/* Submenú */}
        <ul className="mt-2 ml-4 space-y-1 border-l-2 border-base-300 pl-4">
          {subMenu.map((item, idx) => (
            <li key={idx}>
              <Link
                to={item.url}
                onClick={cerrarDrawer}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm hover:bg-base-200 hover:text-success transition-colors group/link"
              >
                {/* Indicador visual */}
                <div className="w-1.5 h-1.5 rounded-full bg-base-content/30 group-hover/link:bg-success transition-colors"></div>

                {/* Nombre del submenú */}
                <span className="text-base-content/80 group-hover/link:text-base-content group-hover/link:font-medium transition-all">
                  {item.name}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}
