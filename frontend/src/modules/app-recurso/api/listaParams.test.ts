import { describe, expect, it } from "vitest";
import {
  construirQueryLista,
  contarFiltrosActivos,
  cambioDeTexto,
  FILTROS_LISTA_INICIALES,
} from "./listaParams";

describe("construirQueryLista", () => {
  it("solo manda paginación cuando no hay filtros", () => {
    expect(construirQueryLista(FILTROS_LISTA_INICIALES)).toBe("page=1&limit=20");
  });

  it("recorta textos, omite vacíos y ceros", () => {
    const q = construirQueryLista({
      ...FILTROS_LISTA_INICIALES,
      radicado: "  2026ER ",
      expediente: "   ",
      numero_vital: "VITAL",
      municipio_id: 3,
      vereda_id: 0,
      involucrado_id: 20,
      page: 2,
    });
    expect(q).toBe("page=2&limit=20&radicado=2026ER&numero_vital=VITAL&municipio_id=3&involucrado_id=20");
  });

  it("acota página y límite al rango del backend", () => {
    expect(construirQueryLista({ ...FILTROS_LISTA_INICIALES, page: 0, limit: 500 })).toBe("page=1&limit=200");
  });

  it("codifica espacios del número de expediente", () => {
    expect(construirQueryLista({ ...FILTROS_LISTA_INICIALES, expediente: "CA 001" })).toContain("expediente=CA+001");
  });
});

describe("contarFiltrosActivos / cambioDeTexto", () => {
  it("cuenta solo filtros con valor", () => {
    expect(contarFiltrosActivos(FILTROS_LISTA_INICIALES)).toBe(0);
    expect(contarFiltrosActivos({ ...FILTROS_LISTA_INICIALES, radicado: "x", vereda_id: 2, page: 5 })).toBe(2);
  });

  it("solo los textos esperan; página y selectores se aplican de inmediato", () => {
    const base = FILTROS_LISTA_INICIALES;
    expect(cambioDeTexto(base, { ...base, radicado: "2026" })).toBe(true);
    expect(cambioDeTexto(base, { ...base, numero_vital: "V" })).toBe(true);
    expect(cambioDeTexto(base, { ...base, page: 3 })).toBe(false);
    expect(cambioDeTexto(base, { ...base, municipio_id: 2, vereda_id: 5 })).toBe(false);
  });
});
