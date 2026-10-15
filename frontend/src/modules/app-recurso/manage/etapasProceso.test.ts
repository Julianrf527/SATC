import { describe, expect, it } from "vitest";
import type { EtapasExpediente } from "../types";
import { esPestana, ETAPAS_RECURSO, pestanaConDatos, pestanaDeDocumento } from "./etapasProceso";

describe("ETAPAS_RECURSO", () => {
  it("sigue el orden del plan §4", () => {
    expect(ETAPAS_RECURSO.map((e) => e.id)).toEqual([
      "info",
      "auto-admite",
      "concepto",
      "requerimiento",
      "decision",
      "memorias",
      "obras",
    ]);
  });
});

describe("pestanaDeDocumento", () => {
  it("usa la etapa_tipo del backend", () => {
    expect(pestanaDeDocumento("acto_admite", "AUTO_ADMITE")).toBe("auto-admite");
    expect(pestanaDeDocumento("recurso_reposicion", "RECURSO")).toBe("decision");
    expect(pestanaDeDocumento("expediente_involucrado")).toBe("info");
  });

  it("el tipo de documento distingue los conceptos técnicos", () => {
    expect(pestanaDeDocumento("concepto_tecnico", "CONCEPTO_ETAPA2")).toBe("concepto");
    expect(pestanaDeDocumento("concepto_tecnico", "CONCEPTO_ADICIONAL")).toBe("requerimiento");
    expect(pestanaDeDocumento("concepto_tecnico", "CONCEPTO_SUBSANACION")).toBe("memorias");
    expect(pestanaDeDocumento("concepto_tecnico", "CONCEPTO_OBRAS_SEGUNDO")).toBe("obras");
  });

  it("cae a Información base si no reconoce la etapa", () => {
    expect(pestanaDeDocumento("otra")).toBe("info");
    expect(pestanaDeDocumento(null)).toBe("info");
  });

  it("esPestana valida ids de navegación", () => {
    expect(esPestana("decision")).toBe(true);
    expect(esPestana("cierre")).toBe(false);
  });
});

describe("pestanaDeDocumento con etapa_padre (C.12)", () => {
  it("etapa_padre manda sobre etapa_tipo", () => {
    expect(pestanaDeDocumento("requerimiento", "REQUERIMIENTO", "memorias_calculo")).toBe("memorias");
    expect(pestanaDeDocumento("requerimiento", "REQUERIMIENTO", "recibo_satisfaccion_obras")).toBe("obras");
    expect(pestanaDeDocumento("expediente_involucrado", "RECONOCE_TERCERO", "tercero_interviniente")).toBe("info");
    expect(pestanaDeDocumento("concepto_tecnico", "CONCEPTO_ADICIONAL", "requerimiento")).toBe("requerimiento");
  });
});

describe("pestanaConDatos", () => {
  const etapas = {
    admite: { existe: true },
    concepto: { existe: false },
    requerimiento: { existe: false },
    decision: { existe: false },
    memorias: { existe: false },
    obras: { existe: false },
    terceros: [],
  } as unknown as EtapasExpediente;
  it("solo etapas existentes (Consulta)", () => {
    expect(pestanaConDatos("info", null)).toBe(true);
    expect(pestanaConDatos("auto-admite", etapas)).toBe(true);
    expect(pestanaConDatos("concepto", etapas)).toBe(false);
  });
});
