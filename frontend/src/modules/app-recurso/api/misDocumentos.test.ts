import { describe, expect, it } from "vitest";
import {
  construirQueryMisDocumentos,
  etiquetaRol,
  FILTROS_MIS_DOCUMENTOS,
  hayFiltrosActivos,
  paginasVisibles,
} from "./misDocumentosParams";

describe("construirQueryMisDocumentos", () => {
  it("sin filtros solo pide la página", () => {
    expect(construirQueryMisDocumentos(FILTROS_MIS_DOCUMENTOS)).toBe("page=1&limit=20");
  });

  it("agrega solo los filtros con valor, el rol y la casilla", () => {
    expect(
      construirQueryMisDocumentos(
        { expediente: " CA 012 ", tipo_documento: "DECISION", rol: "revisor", estado: "", soloAccion: true },
        3,
      ),
    ).toBe("page=3&limit=20&expediente=CA+012&tipo_documento=DECISION&rol=revisor&solo_accion=true");
  });
});

describe("hayFiltrosActivos", () => {
  it("detecta cada filtro", () => {
    expect(hayFiltrosActivos(FILTROS_MIS_DOCUMENTOS)).toBe(false);
    expect(hayFiltrosActivos({ ...FILTROS_MIS_DOCUMENTOS, expediente: "  " })).toBe(false);
    expect(hayFiltrosActivos({ ...FILTROS_MIS_DOCUMENTOS, rol: "encargado" })).toBe(true);
    expect(hayFiltrosActivos({ ...FILTROS_MIS_DOCUMENTOS, soloAccion: true })).toBe(true);
  });
});

describe("paginasVisibles", () => {
  it("muestra todas si caben", () => {
    expect(paginasVisibles(1, 1)).toEqual([1]);
    expect(paginasVisibles(2, 4)).toEqual([1, 2, 3, 4]);
  });

  it("mueve la ventana alrededor de la página actual", () => {
    expect(paginasVisibles(1, 20)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(paginasVisibles(10, 20)).toEqual([7, 8, 9, 10, 11, 12, 13]);
    expect(paginasVisibles(20, 20)).toEqual([14, 15, 16, 17, 18, 19, 20]);
  });
});

describe("etiquetaRol", () => {
  it("traduce los roles conocidos", () => {
    expect(etiquetaRol("encargado")).toBe("Encargado");
    expect(etiquetaRol("revisor")).toBe("Revisor");
    expect(etiquetaRol("otro")).toBe("otro");
  });
});
