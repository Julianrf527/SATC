import { describe, expect, it } from "vitest";
import { PERSONA_VACIA } from "../../api/personaForm";
import { documentoBuscable, documentoPersona, formDesdePersona, nombrePersona, validarPersona } from "./personaForm";

describe("documentoBuscable", () => {
  it("exige 7 dígitos y DV si es NIT", () => {
    expect(documentoBuscable({ ...PERSONA_VACIA, numero_documento: "123456" })).toBe(false);
    expect(documentoBuscable({ ...PERSONA_VACIA, numero_documento: "1234567" })).toBe(true);
    expect(documentoBuscable({ ...PERSONA_VACIA, tipo_documento: "NIT", numero_documento: "900123456" })).toBe(false);
    expect(
      documentoBuscable({ ...PERSONA_VACIA, tipo_documento: "NIT", numero_documento: "900123456", digito_verificacion: "3" }),
    ).toBe(true);
  });
});

describe("validarPersona", () => {
  it("si la persona ya existe no pide más datos", () => {
    expect(validarPersona(PERSONA_VACIA, { id: 1 }, "solicitante")).toBeNull();
  });

  it("para crearla exige documento y nombre", () => {
    expect(validarPersona(PERSONA_VACIA, null, "solicitante")).toBe("Ingrese el documento del solicitante");
    expect(validarPersona({ ...PERSONA_VACIA, numero_documento: "1234567" }, null, "representante legal")).toBe(
      "Ingrese el nombre del representante legal",
    );
  });

  it("NIT sin DV", () => {
    expect(
      validarPersona({ ...PERSONA_VACIA, tipo_documento: "NIT", numero_documento: "900123456", nombre: "X" }, null, "solicitante"),
    ).toMatch(/dígito de verificación/);
  });
});

describe("presentación", () => {
  it("tolera personas que app-involved no resolvió", () => {
    expect(nombrePersona({ id: 20 })).toBe("Persona #20");
    expect(documentoPersona({ id: 20 })).toBe("");
  });

  it("formatea el documento con DV", () => {
    expect(documentoPersona({ id: 1, tipo_documento: "NIT", numero_documento: 900123456, digito_verificacion: "3" })).toBe(
      "NIT 900123456-3",
    );
  });

  it("formDesdePersona convierte números a texto", () => {
    expect(formDesdePersona({ id: 1, tipo_documento: "CC", numero_documento: 1020304050, nombre: "Ana", celular: 300 })).toMatchObject({
      numero_documento: "1020304050",
      celular: "300",
      correo: "",
    });
  });
});
