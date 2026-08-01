import { useState, useEffect } from "react";
import webmDia from "../assets/video_dia.webm";
import webmNoche from "../assets/video_noche.webm";
import logo from "../assets/logo.png";

type Props = {
  theme: "emerald" | "dark";
};

export default function WelcomeLayout({ theme }: Props) {
  // Solo se ve un tema a la vez: el video del tema inactivo ni se monta hasta
  // que el usuario cambie de tema alguna vez (evita la descarga que dispara
  // un <video> aunque esté con opacity: 0).
  const [temasVistos, setTemasVistos] = useState<Set<Props["theme"]>>(
    () => new Set([theme])
  );

  useEffect(() => {
    setTemasVistos((prev) =>
      prev.has(theme) ? prev : new Set(prev).add(theme)
    );
  }, [theme]);

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
              {temasVistos.has("emerald") && (
                <video
                  src={webmDia}
                  className="w-full h-full object-cover select-none pointer-events-none"
                  autoPlay
                  loop
                  muted
                  playsInline
                  disablePictureInPicture
                  aria-label="Colibrí día"
                />
              )}
            </div>

            {/* Animación noche */}
            <div
              className={`absolute inset-0 transition-opacity duration-2000 ${
                theme === "dark"
                  ? "opacity-100"
                  : "opacity-0 pointer-events-none"
              }`}
            >
              {temasVistos.has("dark") && (
                <video
                  src={webmNoche}
                  className="w-full h-full object-cover select-none pointer-events-none"
                  autoPlay
                  loop
                  muted
                  playsInline
                  disablePictureInPicture
                  aria-label="Colibrí noche"
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
