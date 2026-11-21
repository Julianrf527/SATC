import { describe, expect, it } from "vitest";
import type { AlertaPaginada } from "@features/alertas";
import { type AlertaInfraccion, destinoAlertaInfraccion, pestanaDeAlerta } from "./alertasInfraccion";

describe("pestanaDeAlerta", () => {
  it.each([
    ["respuesta_plazo", "respuesta"],
    ["medida_acto_proyectar", "respuesta"],
    ["visita_asignar", "visita"],
    ["visita_aprobacion", "visita"],
    ["concepto_acto_proyectar", "concepto"],
    ["concepto_termino", "concepto"],
    ["seguimiento_primera_version", "seguimiento"],
    ["concepto_seguimiento_acto_aprobacion", "concepto_seguimiento"],
    ["cierre_acto_proyectar", "cierre"],
  ])("%s → %s", (tipo, pestana) => {
    expect(pestanaDeAlerta(tipo)).toBe(pestana);
  });
});

function alerta(extra: Partial<AlertaInfraccion>): AlertaInfraccion {
  return {
    tipo: "respuesta_plazo",
    etapa: "Respuesta",
    accion_requerida: "",
    plazo_legal: "",
    msg: "",
    fecha_limite: "2026-12-01",
    semaforo: {} as AlertaPaginada["semaforo"],
    radicado: "R1",
    clave: "respuesta_plazo",
    es_responsable: true,
    roles_responsables: [],
    ...extra,
  };
}

const ASIGNAR = { permiso: "infraccion_asignar_informes", etiqueta: "Asignar informes" };
const LIDER = { permiso: "infraccion_lider_proyecto", etiqueta: "Líder de proyecto" };

describe("destinoAlertaInfraccion", () => {
  it("asignar visita → Asignar informes filtrado por radicado", () => {
    const d = destinoAlertaInfraccion(alerta({ tipo: "visita_asignar", roles_responsables: [ASIGNAR] }),
      ["infraccion_asignar_informes"]);
    expect(d.ruta).toBe("/infraction/reports");
    expect(d.estado).toEqual({ expedienteRadicadoToFilter: "R1" });
  });

  it("acto en revisión → proceso en Mis actuaciones", () => {
    const d = destinoAlertaInfraccion(
      alerta({ tipo: "concepto_acto_aprobacion", roles_responsables: [LIDER], proceso_id: 9 }),
      ["infraccion_lider_proyecto"]);
    expect(d.accion).toBe("Actuación");
    expect(d.estado).toEqual({ actoProcesoIdToSelect: "9" });
  });

  it("informe propio → informe en Mis actuaciones", () => {
    const d = destinoAlertaInfraccion(alerta({ tipo: "visita_primera_version", informe_id: 4 }), ["infraccion_tecnico"]);
    expect(d.ruta).toBe("/infraction/my-reports");
    expect(d.estado).toEqual({ informeIdToSelect: "4" });
  });

  it("alerta propia del abogado → Gestionar en la pestaña de la etapa", () => {
    const d = destinoAlertaInfraccion(alerta({ tipo: "cierre_acto_proyectar" }), ["infraccion_gestionar"]);
    expect(d).toMatchObject({ ruta: "/infraction/manage", accion: "Gestionar" });
    expect(d.estado).toEqual({ radicadoToSelect: "R1", etapaToSelect: "cierre" });
  });

  it("alerta ajena → Consultar", () => {
    const d = destinoAlertaInfraccion(alerta({ es_responsable: false, informe_id: 4 }),
      ["infraccion_gestionar", "infraccion_consultar"]);
    expect(d).toMatchObject({ ruta: "/infraction/consult", accion: "Consultar" });
  });
});
