import { describe, expect, it } from "vitest";
import {
  construirQueryLista,
  contarFiltrosActivos,
  FILTROS_LISTA_INICIALES,
  totalPaginas,
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

describe("contarFiltrosActivos / totalPaginas", () => {
  it("cuenta solo filtros con valor", () => {
    expect(contarFiltrosActivos(FILTROS_LISTA_INICIALES)).toBe(0);
    expect(contarFiltrosActivos({ ...FILTROS_LISTA_INICIALES, radicado: "x", vereda_id: 2, page: 5 })).toBe(2);
  });

  it("calcula páginas con mínimo 1", () => {
    expect(totalPaginas(0, 20)).toBe(1);
    expect(totalPaginas(41, 20)).toBe(3);
  });
});
