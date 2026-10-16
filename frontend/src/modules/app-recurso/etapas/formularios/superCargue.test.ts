import { describe, expect, it } from "vitest";
import type { CamposConcepto } from "../../types";
import { archivosSuper, bodySuper, seccionesSuper, SUPER_VACIO, superVacio, validarSuper } from "./superCargue";

const pdf = () => new File(["%PDF"], "doc.pdf", { type: "application/pdf" });

// Definición que trae el nodo de concepto del árbol (backend).
const CAMPOS_ETAPA2: CamposConcepto = {
  obligatorios: ["file_id", "fecha_aceptacion", "caudal_fuente"],
  opcionales: [],
  campos: [
    { campo: "fecha_aceptacion", tipo: "fecha", etiqueta: "Fecha del concepto (firma)", obligatorio: true },
    { campo: "caudal_fuente", tipo: "decimal", etiqueta: "Caudal fuente (L/s)", obligatorio: true },
  ],
};

describe("seccionesSuper (C.9)", () => {
  it("cada nodo lleva sus secciones", () => {
    const admite = seccionesSuper({ clase: "admite" }, false);
    expect(admite).toMatchObject({ acto: true, docsAdmite: true, tecnicoVisita: true });
    expect(seccionesSuper({ clase: "admite" }, true).acto).toBe(false);
    expect(seccionesSuper({ clase: "requerimiento", ambito: "etapa3" }, false).respuesta).toBe(true);
    expect(seccionesSuper({ clase: "requerimiento", ambito: "obras" }, false).respuesta).toBe(false);
    expect(seccionesSuper({ clase: "recurso" }, false)).toMatchObject({ radicado: "Escrito del recurso", resultado: true });
    expect(seccionesSuper({ clase: "tercero", vinculoId: 1 }, false)).toMatchObject({ actoObligatorio: true, version: false });
    expect(seccionesSuper({ clase: "subsanacion" }, false).version).toBe(false);
  });
});

describe("validarSuper / bodySuper", () => {
  it("crear con radicado exige los tres datos; al actualizar son opcionales", () => {
    const s = seccionesSuper({ clase: "memorias" }, false);
    expect(validarSuper(s, SUPER_VACIO, false)).toMatch(/^Planos:/);
    expect(validarSuper(s, SUPER_VACIO, true)).toBeNull();
  });

  it("acto: si se toca, debe estar completo; obligatorio en aprobaciones", () => {
    const s = seccionesSuper({ clase: "decision" }, false);
    const f = { ...SUPER_VACIO, acto: { archivo: null, clase_acto: "" as const, numerado: "5", fecha_numerado: "" } };
    expect(validarSuper(s, f, true)).toMatch(/acto/);
    const aprob = seccionesSuper({ clase: "aprobacion_memorias" }, false);
    expect(validarSuper(aprob, SUPER_VACIO, true)).toMatch(/acto/);
    expect(validarSuper(seccionesSuper({ clase: "aprobacion_obras" }, true), SUPER_VACIO, true)).toMatch(/ya tiene acto/);
  });

  it("concepto: técnico obligatorio para crearlo", () => {
    const s = seccionesSuper({ clase: "concepto", tipo: "memorias" }, false);
    expect(validarSuper(s, SUPER_VACIO, false)).toMatch(/técnico/);
    expect(validarSuper(s, { ...SUPER_VACIO, tecnico_encargado_id: 3 }, false)).toBeNull();
  });

  it("solo envía campos con valor, acto anidado y version si aplica", () => {
    const s = seccionesSuper({ clase: "decision" }, false);
    const f = {
      ...SUPER_VACIO,
      acto: { archivo: pdf(), clase_acto: "AUTO" as const, numerado: "7", fecha_numerado: "2020-01-02" },
      decision: "OTORGADA" as const,
      requiere_memorias: true,
    };
    expect(validarSuper(s, f, true)).toBeNull();
    expect(archivosSuper(s, f).acto).toBeInstanceOf(File);
    expect(bodySuper(s, f, { acto: 50 }, 3)).toEqual({
      version: 3,
      acto: { clase_acto: "AUTO", numerado: "0007", fecha_numerado: "2020-01-02", file_id: 50 },
      decision: "OTORGADA",
      requiere_memorias: true,
    });
  });

  it("concepto: datos numéricos convertidos y file_id del concepto", () => {
    const s = seccionesSuper({ clase: "concepto", tipo: "etapa2" }, false, CAMPOS_ETAPA2);
    expect(s.concepto).toBe(CAMPOS_ETAPA2);
    const f = {
      ...SUPER_VACIO,
      tecnico_encargado_id: 4 as const,
      concepto: { ...SUPER_VACIO.concepto, caudal_fuente: "1,5", fecha_aceptacion: "2020-03-03" },
    };
    expect(bodySuper(s, f, { concepto: 8 }, null)).toEqual({
      tecnico_encargado_id: 4,
      fecha_aceptacion: "2020-03-03",
      caudal_fuente: 1.5,
      file_id: 8,
    });
    // En el cargue directo todo es opcional aunque el backend lo marque obligatorio.
    expect(validarSuper(s, { ...SUPER_VACIO, tecnico_encargado_id: 4 }, false)).toBeNull();
    expect(validarSuper(s, { ...f, concepto: { ...f.concepto, caudal_fuente: "x" } }, false)).toBe(
      "Valor inválido: Caudal fuente (L/s)",
    );
  });

  it("abogado encargado: opcional, solo en etapas con encargado", () => {
    const decision = seccionesSuper({ clase: "decision" }, false);
    expect(decision.encargado).toBe(true);
    expect(seccionesSuper({ clase: "admite" }, false).encargado).toBe(true);
    expect(seccionesSuper({ clase: "requerimiento", ambito: "memorias" }, false).encargado).toBe(true);
    expect(seccionesSuper({ clase: "aprobacion_obras" }, false).encargado).toBe(true);
    expect(seccionesSuper({ clase: "tercero", vinculoId: 1 }, false).encargado).toBe(false);
    expect(seccionesSuper({ clase: "concepto", tipo: "etapa2" }, false).encargado).toBe(false);
    expect(seccionesSuper({ clase: "memorias" }, false).encargado).toBe(false);
    // Sin elegir: no se envía (la etapa nueva queda sin encargado) y no es error.
    expect(validarSuper(decision, SUPER_VACIO, false)).toBeNull();
    expect(bodySuper(decision, SUPER_VACIO, {}, null)).toEqual({});
    const f = { ...SUPER_VACIO, encargado_acto_id: 30 };
    expect(bodySuper(decision, f, {}, 2)).toEqual({ version: 2, encargado_acto_id: 30 });
    expect(superVacio(bodySuper(decision, f, {}, 2))).toBe(false);
    // En nodos sin encargado se ignora aunque el formulario lo traiga.
    expect(bodySuper(seccionesSuper({ clase: "memorias" }, false), f, {}, null)).not.toHaveProperty("encargado_acto_id");
  });

  it("superVacio ignora version", () => {
    expect(superVacio({ version: 2 })).toBe(true);
    expect(superVacio({ version: 2, radicado: "X" })).toBe(false);
  });
});
