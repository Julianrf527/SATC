import { describe, expect, it } from "vitest";
import { ACTO_FINAL_VACIO, bodyActoFinal, validarActoFinal } from "./actoFinal";
import { bodyRequierePruebas, validarRequierePruebas, validarRespuestaPruebas } from "./requierePruebas";
import { seccionesSuper } from "./superCargue";

describe("¿Requiere práctica de pruebas?", () => {
  it("es obligatoria al crear el recurso", () => {
    expect(validarRespuestaPruebas(null)).toMatch(/práctica de pruebas/);
    expect(validarRespuestaPruebas(false)).toBeNull();
    expect(validarRespuestaPruebas(true)).toBeNull();
  });

  it("al cambiarla exige otro valor y confirmar si elimina la práctica", () => {
    expect(validarRequierePruebas(true, true, false, false)).toMatch(/distinto/);
    expect(validarRequierePruebas(true, false, true, false)).toMatch(/Confirme/);
    expect(validarRequierePruebas(true, false, true, true)).toBeNull();
    expect(validarRequierePruebas(false, true, false, false)).toBeNull();
  });

  it("body con versión y la confirmación solo si aplica", () => {
    expect(bodyRequierePruebas(3, true, false)).toEqual({ version: 3, requiere_pruebas: true });
    expect(bodyRequierePruebas(3, false, true)).toEqual({ version: 3, requiere_pruebas: false, confirmar_eliminar_pruebas: true });
  });
});

describe("auto que admite y decreta práctica de pruebas", () => {
  const base = { ...ACTO_FINAL_VACIO, archivo: new File(["x"], "a.pdf", { type: "application/pdf" }), clase_acto: "AUTO" as const, numerado: "12", fecha_numerado: "2026-06-15" };

  it("pide técnico y fecha de visita y los envía", () => {
    expect(validarActoFinal(base, "pruebas")).toMatch(/técnico/);
    expect(validarActoFinal({ ...base, tecnico_id: 5 }, "pruebas")).toMatch(/visita/);
    const completo = { ...base, tecnico_id: 5, fecha_visita_tecnica: "2026-06-20" };
    expect(validarActoFinal(completo, "pruebas")).toBeNull();
    expect(bodyActoFinal(completo, "pruebas", 9)).toMatchObject({ file_id: 9, tecnico_id: 5, fecha_visita_tecnica: "2026-06-20" });
  });

  it("super gestión: técnico y visita sin aviso de plazo", () => {
    const s = seccionesSuper({ clase: "pruebas" }, false);
    expect(s).toMatchObject({ acto: true, encargado: true, tecnicoVisita: { avisoVisita: false } });
    expect(seccionesSuper({ clase: "admite" }, false).tecnicoVisita?.avisoVisita).toBe(true);
  });
});
