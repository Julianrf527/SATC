import { describe, expect, it } from "vitest";
import { pestanaDeAlerta, rutaExpedienteAlertas } from "./alertasRecurso";

describe("pestanaDeAlerta", () => {
  it.each([
    ["admite_revision", "auto-admite"],
    ["concepto_primera_version", "concepto"],
    ["concepto_adicional_tecnico", "requerimiento"],
    ["concepto_adicional_version_final", "requerimiento"],
    ["requerimiento_primera_version", "requerimiento"],
    ["decision_revision", "decision"],
    ["recurso_acto", "decision"],
    ["recurso_concepto_pruebas", "decision"],
    ["otra_cosa", "info"],
  ])("%s → %s", (tipo, pestana) => {
    expect(pestanaDeAlerta(tipo)).toBe(pestana);
  });
});

describe("rutaExpedienteAlertas", () => {
  it("gestionar va a Gestionar; solo consultar va a Consulta", () => {
    expect(rutaExpedienteAlertas(["recurso_gestionar", "recurso_consultar"])).toBe("/recurso/manage");
    expect(rutaExpedienteAlertas(["recurso_consultar", "recurso_tecnico"])).toBe("/recurso/consult");
  });
});
