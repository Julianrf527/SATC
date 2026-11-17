import { describe, expect, it } from "vitest";
import type { ExpedienteDetalle } from "../../types";
import {
  alternar,
  construirExpedienteDatos,
  esPdf,
  FORM_VACIO,
  formDesdeDetalle,
  validarExpedienteForm,
  type ExpedienteFormState,
} from "./expedienteForm";

const pdf = { name: "comprobante.pdf", type: "application/pdf" } as File;

const COMPLETO: ExpedienteFormState = {
  ...FORM_VACIO,
  radicado: " 2026ER00012 ",
  fecha_radicado: "2026-03-10",
  expediente: "CA 001-26",
  numero_vital: "VITAL-123",
  nombre_predio: "La Esperanza",
  matricula_inmobiliaria: "078-12345",
  codigo_catastral: "15001000100020003",
  radicado_oficio_entrada: "2026ER90012",
  fecha_oficio_entrada: "2026-03-01",
  municipio_id: 1,
  vereda_id: 2,
  tipo_fuente_id: 1,
  nombre_fuente: "Juancho Castro",
  fuente_ids: [2, 3, 2],
  usos: ["DOMESTICO", "RIEGO", "DOMESTICO"],
  comprobante: pdf,
};

describe("validarExpedienteForm", () => {
  it("acepta un formulario completo", () => {
    expect(validarExpedienteForm(COMPLETO)).toBeNull();
  });

  it("exige textos obligatorios (no solo espacios)", () => {
    expect(validarExpedienteForm({ ...COMPLETO, numero_vital: "   " })).toBe("Ingrese el número VITAL");
  });

  it("respeta las longitudes del backend", () => {
    expect(validarExpedienteForm({ ...COMPLETO, expediente: "CA 0001-266" })).toMatch(/máximo 9/);
  });

  it("exige fuentes, usos y comprobante", () => {
    expect(validarExpedienteForm({ ...COMPLETO, fuente_ids: [] })).toBe("Seleccione al menos una fuente");
    expect(validarExpedienteForm({ ...COMPLETO, usos: [] })).toBe("Seleccione al menos un uso del agua");
    expect(validarExpedienteForm({ ...COMPLETO, comprobante: null })).toMatch(/comprobante/);
  });

  it("en edición basta el comprobante ya guardado", () => {
    expect(validarExpedienteForm({ ...COMPLETO, comprobante: null, doc_comprobante_pago_id: 101 })).toBeNull();
  });

  it("rechaza comprobantes que no son PDF", () => {
    const docx = { name: "a.docx", type: "application/msword" } as File;
    expect(validarExpedienteForm({ ...COMPLETO, comprobante: docx })).toBe("El comprobante de pago debe ser un PDF");
  });
});

describe("construirExpedienteDatos", () => {
  it("recorta textos y quita repetidos", () => {
    const datos = construirExpedienteDatos(COMPLETO, 101);
    expect(datos.radicado).toBe("2026ER00012");
    expect(datos.fuente_ids).toEqual([2, 3]);
    expect(datos.usos).toEqual(["DOMESTICO", "RIEGO"]);
    expect(datos.doc_comprobante_pago_id).toBe(101);
    expect(datos).not.toHaveProperty("municipio_id");
    expect(datos).not.toHaveProperty("comprobante");
  });
});

describe("formDesdeDetalle", () => {
  it("toma ids de catálogos y listas del detalle", () => {
    const detalle = {
      radicado: "R",
      fecha_radicado: "2026-03-10",
      expediente: "CA 001-26",
      numero_vital: "V",
      nombre_predio: "P",
      matricula_inmobiliaria: "M",
      codigo_catastral: "C",
      radicado_oficio_entrada: "O",
      fecha_oficio_entrada: "2026-03-01",
      doc_comprobante_pago_id: 101,
      vereda: { id: 4, nombre: "Belen" },
      municipio: { id: 1, nombre: "Almeida" },
      tipo_fuente: { id: 2, nombre: "LÓTICO" },
      nombre_fuente: "F",
      fuentes: [{ id: 7, nombre: "RÍO" }],
      usos: ["RIEGO"],
    } as ExpedienteDetalle;
    const f = formDesdeDetalle(detalle);
    expect(f).toMatchObject({ municipio_id: 1, vereda_id: 4, tipo_fuente_id: 2, fuente_ids: [7], usos: ["RIEGO"] });
    expect(f.doc_comprobante_pago_id).toBe(101);
    expect(f.comprobante).toBeNull();
  });
});

describe("utilidades", () => {
  it("alternar agrega y quita", () => {
    expect(alternar([1, 2], 2)).toEqual([1]);
    expect(alternar([1], 2)).toEqual([1, 2]);
  });

  it("esPdf mira tipo o extensión", () => {
    expect(esPdf({ name: "X.PDF", type: "" })).toBe(true);
    expect(esPdf({ name: "x.png", type: "image/png" })).toBe(false);
  });
});
