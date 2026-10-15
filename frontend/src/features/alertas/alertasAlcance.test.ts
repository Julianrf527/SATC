import { describe, expect, it } from "vitest";
import { destinoAlerta, endpointConAlcance } from "./alertasAlcance";

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
