import { describe, expect, it } from "vitest";
import {
  accionesNodo,
  urlAsignarme,
  urlRegistrarRadicado,
  urlSeleccionarTecnico,
  urlSuperCargue,
  urlVersionFinal,
} from "./nodos";

describe("rutas de acciones por nodo (C.3–C.10)", () => {
  it("asignarme en actos y terceros; nunca en conceptos", () => {
    expect(urlAsignarme(7, { clase: "admite" })).toBe("/recurso/etapas/7/admite/asignarme");
    expect(urlAsignarme(7, { clase: "requerimiento", ambito: "memorias" })).toBe(
      "/recurso/etapas/7/requerimientos/memorias/asignarme",
    );
    expect(urlAsignarme(7, { clase: "aprobacion_obras" })).toBe("/recurso/etapas/7/obras/aprobacion/asignarme");
    expect(urlAsignarme(7, { clase: "tercero", vinculoId: 16 })).toBe("/recurso/terceros/16/asignarme");
    expect(urlAsignarme(7, { clase: "concepto", tipo: "memorias" })).toBeNull();
    expect(urlAsignarme(7, { clase: "subsanacion" })).toBeNull();
  });

  it("versión final de actos, conceptos y terceros", () => {
    expect(urlVersionFinal(7, { clase: "decision" })).toBe("/recurso/etapas/7/decision/version-final");
    expect(urlVersionFinal(7, { clase: "recurso" })).toBe("/recurso/etapas/7/recurso/version-final");
    expect(urlVersionFinal(7, { clase: "concepto", tipo: "obras_segundo" })).toBe(
      "/recurso/etapas/7/conceptos/obras_segundo/version-final",
    );
    expect(urlVersionFinal(7, { clase: "aprobacion_memorias" })).toBe("/recurso/etapas/7/memorias/aprobacion/version-final");
    expect(urlVersionFinal(7, { clase: "tercero", vinculoId: 3 })).toBe("/recurso/terceros/3/version-final");
    expect(urlVersionFinal(7, { clase: "memorias" })).toBeNull();
  });

  it("seleccionar técnico no aplica a la etapa 2", () => {
    expect(urlSeleccionarTecnico(7, "etapa2")).toBeNull();
    expect(urlSeleccionarTecnico(7, "adicional")).toBe("/recurso/etapas/7/conceptos/adicional/tecnico");
  });

  it("registrar radicados del usuario", () => {
    expect(urlRegistrarRadicado(7, { clase: "recurso" })).toBe("/recurso/etapas/7/recurso");
    expect(urlRegistrarRadicado(7, { clase: "memorias" })).toBe("/recurso/etapas/7/memorias");
    expect(urlRegistrarRadicado(7, { clase: "subsanacion" })).toBe("/recurso/etapas/7/memorias/subsanacion");
    expect(urlRegistrarRadicado(7, { clase: "obras" })).toBe("/recurso/etapas/7/obras");
    expect(urlRegistrarRadicado(7, { clase: "nuevo_informe" })).toBe("/recurso/etapas/7/obras/nuevo-informe");
    expect(urlRegistrarRadicado(7, { clase: "decision" })).toBeNull();
  });

  it("super gestión: aprobaciones e informe usan la ruta de su etapa", () => {
    expect(urlSuperCargue(7, { clase: "admite" })).toBe("/recurso/super-gestion/7/admite");
    expect(urlSuperCargue(7, { clase: "concepto", tipo: "etapa2" })).toBe("/recurso/super-gestion/7/conceptos/etapa2");
    expect(urlSuperCargue(7, { clase: "requerimiento", ambito: "etapa3" })).toBe(
      "/recurso/super-gestion/7/requerimientos/etapa3",
    );
    expect(urlSuperCargue(7, { clase: "aprobacion_memorias" })).toBe("/recurso/super-gestion/7/memorias");
    expect(urlSuperCargue(7, { clase: "aprobacion_obras" })).toBe("/recurso/super-gestion/7/obras");
    expect(urlSuperCargue(7, { clase: "informe" })).toBe("/recurso/super-gestion/7/obras");
    expect(urlSuperCargue(7, { clase: "subsanacion" })).toBe("/recurso/super-gestion/7/memorias/subsanacion");
    expect(urlSuperCargue(7, { clase: "nuevo_informe" })).toBe("/recurso/super-gestion/7/obras/nuevo-informe");
    expect(urlSuperCargue(7, { clase: "tercero", vinculoId: 9 })).toBe("/recurso/super-gestion/terceros/9/acto");
  });
});

describe("accionesNodo", () => {
  it("solo pinta lo que manda el backend, y nada en Consulta", () => {
    const nodo = { acciones_disponibles: ["asignarme", "super_cargar"] };
    expect(accionesNodo(nodo, true)("asignarme")).toBe(true);
    expect(accionesNodo(nodo, true)("cargar_version_final")).toBe(false);
    expect(accionesNodo(nodo, false)("asignarme")).toBe(false);
    expect(accionesNodo(null, true)("asignarme")).toBe(false);
  });
});
