import { describe, expect, it } from "vitest";
import type { AlertaPaginada } from "@features/alertas";
import { destinoAlertaRecurso, pestanaDeAlerta } from "./alertasRecurso";

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

function alerta(extra: Partial<AlertaPaginada>): AlertaPaginada {
  return {
    tipo: "concepto_primera_version",
    etapa: "Concepto técnico",
    accion_requerida: "",
    plazo_legal: "",
    msg: "",
    fecha_limite: "2026-12-01",
    semaforo: {} as AlertaPaginada["semaforo"],
    radicado: "R1",
    clave: "concepto_primera_version",
    es_responsable: true,
    expediente_id: 5,
    proceso_id: 9,
    ...extra,
  };
}

const expediente = { expedienteIdToSelect: 5, pestanaToSelect: "concepto" };
const TECNICO = ["recurso_consultar", "recurso_tecnico"];
const GESTOR = ["recurso_consultar", "recurso_gestionar"];

describe("destinoAlertaRecurso", () => {
  it("técnico con tarea suya y proceso: Actuación en Mis actuaciones", () => {
    expect(destinoAlertaRecurso(alerta({}), TECNICO)).toMatchObject({
      ruta: "/recurso/my-reports",
      accion: "Actuación",
      principal: true,
      estado: { procesoIdToSelect: 9 },
    });
  });

  it("técnico sin proceso o con tarea ajena: Consulta del expediente", () => {
    for (const a of [alerta({ proceso_id: null }), alerta({ proceso_id: undefined }), alerta({ es_responsable: false })]) {
      expect(destinoAlertaRecurso(a, TECNICO)).toEqual({ ruta: "/recurso/consult", accion: "Consultar", estado: expediente });
    }
  });

  it("si un rol tuviera técnico y gestionar, manda técnico", () => {
    expect(destinoAlertaRecurso(alerta({}), [...TECNICO, "recurso_gestionar"]).ruta).toBe("/recurso/my-reports");
  });

  it("gestionar: Gestionar (o Consultar si es ajena) en la pantalla de gestión", () => {
    expect(destinoAlertaRecurso(alerta({}), GESTOR)).toEqual({ ruta: "/recurso/manage", accion: "Gestionar", estado: expediente });
    expect(destinoAlertaRecurso(alerta({ es_responsable: false }), GESTOR)).toEqual({
      ruta: "/recurso/manage", accion: "Consultar", estado: expediente,
    });
  });

  it("revisor de turno (alerta por rol suya con proceso): Actuación en Mis actuaciones", () => {
    const roles = [{ permiso: "recurso_lider_tecnico", etiqueta: "Líder técnico" }];
    expect(destinoAlertaRecurso(alerta({ roles_responsables: roles }), ["recurso_consultar", "recurso_lider_tecnico"]))
      .toMatchObject({ ruta: "/recurso/my-reports", accion: "Actuación", estado: { procesoIdToSelect: 9 } });
    // El encargado (técnico) ya no es el responsable mientras revisan: Consulta.
    expect(destinoAlertaRecurso(alerta({ roles_responsables: roles, es_responsable: false }), TECNICO).ruta)
      .toBe("/recurso/consult");
  });

  it("solo consultar: Consulta del expediente", () => {
    expect(destinoAlertaRecurso(alerta({}), ["recurso_consultar", "recurso_revisor_tecnico"])).toEqual({
      ruta: "/recurso/consult", accion: "Consultar", estado: expediente,
    });
  });
});
