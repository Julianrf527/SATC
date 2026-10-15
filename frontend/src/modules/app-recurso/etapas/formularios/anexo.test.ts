import { describe, expect, it } from "vitest";
import { bodyEditarAnexo, validarAnexo } from "./anexo";

const pdf = () => new File(["%PDF"], "anexo.pdf", { type: "application/pdf" });
const docx = () => new File(["x"], "anexo.docx", { type: "application/msword" });

describe("validarAnexo", () => {
  it("exige nombre siempre", () => {
    expect(validarAnexo("  ", pdf())).toBe("Escriba el nombre del documento");
    expect(validarAnexo("", null, { editar: true })).toBe("Escriba el nombre del documento");
  });
  it("al agregar el PDF es obligatorio", () => {
    expect(validarAnexo("Fotos", null)).toBe("Adjunte el documento (PDF)");
    expect(validarAnexo("Fotos", pdf())).toBeNull();
  });
  it("al editar el PDF es opcional, pero si viene debe ser PDF", () => {
    expect(validarAnexo("Fotos", null, { editar: true })).toBeNull();
    expect(validarAnexo("Fotos", pdf(), { editar: true })).toBeNull();
    expect(validarAnexo("Fotos", docx(), { editar: true })).toBe("El documento debe ser PDF");
  });
});

describe("bodyEditarAnexo", () => {
  it("solo nombre si no se reemplaza el archivo", () => {
    expect(bodyEditarAnexo(7, " Fotos ")).toEqual({ expediente_id: 7, nombre: "Fotos" });
  });
  it("incluye el nuevo PDF si se reemplaza", () => {
    expect(bodyEditarAnexo(7, "Fotos", 45)).toEqual({ expediente_id: 7, nombre: "Fotos", documento_anexo_id: 45 });
  });
});
