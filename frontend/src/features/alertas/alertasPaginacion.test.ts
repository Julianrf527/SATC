import { describe, expect, it } from "vitest";
import {
  ALERTAS_POR_PAGINA,
  paginasVisibles,
  textoMostrando,
  urlAlertasPaginadas,
  type FiltrosAlertas,
} from "./alertasPaginacion";

const base: FiltrosAlertas = {
  alcance: "mios",
  page: 1,
  limit: ALERTAS_POR_PAGINA,
  radicado: "",
  estado: "all",
  tipo: "all",
};

describe("urlAlertasPaginadas", () => {
  it("sin filtros: solo página y límite (alcance mios no se envía)", () => {
    expect(urlAlertasPaginadas("/svc/alertas/todas", base)).toBe("/svc/alertas/todas?page=1&limit=10");
  });

  it("alcance todos + página", () => {
    expect(urlAlertasPaginadas("/svc/alertas/todas", { ...base, alcance: "todos", page: 3 })).toBe(
      "/svc/alertas/todas?alcance=todos&page=3&limit=10",
    );
  });

  it("filtros: radicado recortado y codificado, estado y tipo", () => {
    const url = urlAlertasPaginadas("/svc/a", {
      ...base,
      radicado: "  2024 ER/1 ",
      estado: "rojo",
      tipo: "decision_fondo",
    });
    const params = new URL(url, "http://x").searchParams;
    expect(params.get("radicado")).toBe("2024 ER/1");
    expect(params.get("estado")).toBe("rojo");
    expect(params.get("tipo")).toBe("decision_fondo");
    expect(params.has("alcance")).toBe(false);
  });

  it("radicado en blanco, estado y tipo 'all' no se envían", () => {
    const url = urlAlertasPaginadas("/svc/a", { ...base, radicado: "   " });
    expect(url).toBe("/svc/a?page=1&limit=10");
  });

  it("respeta un endpoint que ya trae query string", () => {
    expect(urlAlertasPaginadas("/svc/a?x=1", { ...base, alcance: "todos" })).toBe(
      "/svc/a?x=1&alcance=todos&page=1&limit=10",
    );
  });
});

describe("paginación", () => {
  it("paginasVisibles nunca baja de 1", () => {
    expect(paginasVisibles(undefined)).toBe(1);
    expect(paginasVisibles(0)).toBe(1);
    expect(paginasVisibles(7)).toBe(7);
  });

  it("textoMostrando con singular y plural", () => {
    expect(textoMostrando(1, 1)).toBe("Mostrando 1 de 1 alerta");
    expect(textoMostrando(10, 23)).toBe("Mostrando 10 de 23 alertas");
    expect(textoMostrando(0, 0)).toBe("Mostrando 0 de 0 alertas");
  });
});
