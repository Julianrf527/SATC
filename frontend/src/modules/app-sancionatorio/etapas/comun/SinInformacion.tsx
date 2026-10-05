import Icono from "./Icono";

type Props = {
  icono: string;
  titulo: string;
  texto: string;
  /** Variante con fondo y borde punteado. */
  punteado?: boolean;
};

/** Estado vacío de solo lectura ("Sin X registrada"). */
export default function SinInformacion({ icono, titulo, texto, punteado = false }: Props) {
  return (
    <div
      className={
        punteado
          ? "text-center py-8 bg-base-200 rounded-lg border-2 border-dashed border-base-300"
          : "text-center py-12"
      }
    >
      <div
        className={`w-16 h-16 ${punteado ? "bg-base-300" : "bg-base-200"} rounded-full flex items-center justify-center mb-4 mx-auto`}
      >
        <Icono d={icono} className="w-8 h-8 text-base-content/40" />
      </div>
      <h3 className="text-lg font-medium text-base-content/70 mb-2">{titulo}</h3>
      <p className="text-base-content/60">{texto}</p>
    </div>
  );
}
