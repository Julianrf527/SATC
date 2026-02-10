import gifDia from "../assets/video_dia.gif";
import gifNoche from "../assets/video_noche.gif";
import logo from "../assets/logo.png";

type Props = {
  theme: "emerald" | "dark";
};

export default function WelcomeLayout({ theme }: Props) {
  return (
    <section className="w-full min-h-[calc(100vh-4rem)] bg-base-100 flex items-center justify-center overflow-hidden relative">
      {/* Logo como marca de agua */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <img
          src={logo}
          alt="Logo Corpochivor"
          className="w-[100%] h-[100%] object-contain opacity-10 select-none"
          draggable="false"
        />
      </div>

      <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between h-full relative z-10">
        <div className="md:w-1/2 flex flex-col justify-center h-full">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-base-content mb-6 leading-tight">
            Bienvenido a <span className="text-success">SATC</span>
          </h1>
          <p className="text-base md:text-lg text-base-content/80 mb-4">
            <span className="font-semibold text-success">Sistema de Administración de Trámites de Corpochivor</span>
          </p>
          <p className="text-base md:text-lg text-base-content/80">
            Plataforma que centraliza y optimiza la gestión de los diferentes trámites que ofrece la 
            Corporación Autónoma Regional de Chivor - CORPOCHIVOR.
          </p>
        </div>

        <div className="md:w-1/2 flex justify-center items-center h-full mt-10 md:mt-0 relative md:pl-8">
          <div className="w-[22rem] h-[22rem] md:w-[36rem] md:h-[36rem] relative select-none">
            {/* Animación día */}
            <div
              className={`absolute inset-0 transition-opacity duration-2000 ${
                theme === "emerald"
                  ? "opacity-100"
                  : "opacity-0 pointer-events-none"
              }`}
            >
              <img
                src={gifDia}
                alt="Colibri día"
                className="w-full h-full object-cover select-none pointer-events-none"
                draggable="false"
              />
            </div>

            {/* Animación noche */}
            <div
              className={`absolute inset-0 transition-opacity duration-2000 ${
                theme === "dark"
                  ? "opacity-100"
                  : "opacity-0 pointer-events-none"
              }`}
            >
              <img
                src={gifNoche}
                alt="Colibri noche"
                className="w-full h-full object-cover select-none pointer-events-none"
                draggable="false"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
