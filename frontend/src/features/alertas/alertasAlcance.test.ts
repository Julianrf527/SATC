import { describe, expect, it } from "vitest";
import {
  destinoAlerta,
  endpointConAlcance,
  opcionesAlcance,
  resolverDestino,
  textoRolesResponsables,
} from "./alertasAlcance";

const rutas = { gestion: "/x/manage", consulta: "/x/consult" };

describe("destinoAlerta", () => {
  it("lleva a Gestionar si el usuario es el responsable", () => {
    expect(destinoAlerta({ es_responsable: true }, rutas)).toEqual({ ruta: "/x/manage", accion: "Gestionar" });
  });

  it("lleva a Consultar si el expediente es de otro responsable", () => {
    expect(destinoAlerta({ es_responsable: false }, rutas)).toEqual({ ruta: "/x/consult", accion: "Consultar" });
  });

  it("sin es_responsable (backend anterior) se asume propio: Gestionar", () => {
    expect(destinoAlerta({}, rutas)).toEqual({ ruta: "/x/manage", accion: "Gestionar" });
  });
});

describe("resolverDestino", () => {
  const porRadicado = (a: { radicado: string }) => ({ radicadoToSelect: a.radicado });

  it("sin destino del módulo se comporta como siempre", () => {
    expect(resolverDestino({ es_responsable: true, radicado: "R1" }, rutas, porRadicado)).toEqual({
      ruta: "/x/manage",
      accion: "Gestionar",
      principal: true,
      title: "Expediente a su cargo",
      estado: { radicadoToSelect: "R1" },
    });
    expect(resolverDestino({ es_responsable: false, radicado: "R2" }, rutas, porRadicado)).toEqual({
      ruta: "/x/consult",
      accion: "Consultar",
      principal: false,
      title: "Expediente de otro responsable (solo lectura)",
      estado: { radicadoToSelect: "R2" },
    });
  });

  it("si el módulo devuelve null usa el destino de siempre", () => {
    const r = resolverDestino({ es_responsable: true, radicado: "R1" }, rutas, porRadicado, () => null);
    expect(r.ruta).toBe("/x/manage");
    expect(r.accion).toBe("Gestionar");
  });

  it("el destino del módulo manda en ruta, texto, estilo y estado", () => {
    const r = resolverDestino({ es_responsable: true, radicado: "R1" }, rutas, porRadicado, () => ({
      ruta: "/x/mine",
      accion: "Actuación",
      principal: true,
      title: "Abrir",
      estado: { procesoIdToSelect: 7 },
    }));
    expect(r).toEqual({
      ruta: "/x/mine",
      accion: "Actuación",
      principal: true,
      title: "Abrir",
      estado: { procesoIdToSelect: 7 },
    });
  });
});

describe("endpointConAlcance", () => {
  it("'mios' deja el endpoint igual que antes del filtro", () => {
    expect(endpointConAlcance("/svc/alertas/todas", "mios")).toBe("/svc/alertas/todas");
  });

  it("'todos' agrega el parámetro de query", () => {
    expect(endpointConAlcance("/svc/alertas/todas", "todos")).toBe("/svc/alertas/todas?alcance=todos");
  });

  it("respeta un query string existente", () => {
    expect(endpointConAlcance("/svc/a?x=1", "todos")).toBe("/svc/a?x=1&alcance=todos");
  });
});

describe("opcionesAlcance", () => {
  it("por defecto: Mis expedientes / Todos", () => {
    expect(opcionesAlcance().map((o) => o.label)).toEqual(["Mis expedientes", "Todos"]);
  });

  it("el módulo puede cambiar los textos", () => {
    expect(opcionesAlcance({ mios: "Mis alertas", todos: "Todas" })).toEqual([
      { value: "mios", label: "Mis alertas" },
      { value: "todos", label: "Todas" },
    ]);
  });
});

describe("textoRolesResponsables", () => {
  it("lista los roles responsables", () => {
    const roles = [{ permiso: "a", etiqueta: "Líder técnico" }, { permiso: "b", etiqueta: "SIG" }];
    expect(textoRolesResponsables({ roles_responsables: roles })).toBe("Pendiente: Líder técnico, SIG");
  });

  it("null si la alerta es del encargado", () => {
    expect(textoRolesResponsables({})).toBeNull();
    expect(textoRolesResponsables({ roles_responsables: [] })).toBeNull();
  });
});
