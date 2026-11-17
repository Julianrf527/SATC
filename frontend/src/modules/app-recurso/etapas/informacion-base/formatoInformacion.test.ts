import { describe, expect, it } from "vitest";
import { capitalizar, textoFuente } from "./formatoInformacion";

describe("capitalizar", () => {
  it("pasa de mayúsculas a nombre propio con conectores en minúscula", () => {
    expect(capitalizar("SAN ANTONIO")).toBe("San Antonio");
    expect(capitalizar("OJO DE AGUA")).toBe("Ojo de Agua");
    expect(capitalizar("  RÍO  ")).toBe("Río");
    expect(capitalizar(null)).toBe("");
  });
});

describe("textoFuente", () => {
  it("una clase y nombre", () => {
    expect(textoFuente(["QUEBRADA"], "SAN ANTONIO")).toBe("Quebrada, San Antonio");
  });
  it("varias clases se unen con 'y'", () => {
    expect(textoFuente(["QUEBRADA", "NACIMIENTO"], "EL ALIZAL")).toBe("Quebrada y Nacimiento, El Alizal");
    expect(textoFuente(["RÍO", "CAÑO", "LAGO"], "X")).toBe("Río, Caño y Lago, X");
  });
  it("sin nombre o sin clases", () => {
    expect(textoFuente(["QUEBRADA"], "")).toBe("Quebrada");
    expect(textoFuente([], "SAN ANTONIO")).toBe("San Antonio");
    expect(textoFuente([], null)).toBe("");
  });
});
