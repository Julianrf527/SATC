import { describe, expect, it } from "vitest";
import { ACTO_FINAL_VACIO, bodyActoFinal, validarActoFinal } from "./actoFinal";
import { decimal, entero, numeradoParaEnviar, numeradoValido } from "./comunes";
import {
  bodyConceptoFinal,
  camposConcepto,
  camposVisibles,
  conceptoFinalInicial,
  validarConceptoFinal,
} from "./conceptoFinal";
import { bodyRadicado, bodyRespuestaRequerimiento, validarRadicado } from "./radicado";

const pdf = () => new File(["%PDF"], "acto.pdf", { type: "application/pdf" });
const docx = () => new File(["x"], "acto.docx", { type: "application/msword" });

describe("comunes", () => {
  it("numerado de 1 a 4 dígitos, enviado con ceros", () => {
    expect(numeradoValido("12")).toBe(true);
    expect(numeradoValido("0")).toBe(false);
    expect(numeradoValido("12345")).toBe(false);
    expect(numeradoValido("1a")).toBe(false);
    expect(numeradoParaEnviar("12")).toBe("0012");
  });
  it("decimal acepta coma; entero solo dígitos", () => {
    expect(decimal("10,5")).toBe(10.5);
    expect(decimal("")).toBeNull();
    expect(decimal("-1")).toBeNull();
    expect(entero("3")).toBe(3);
    expect(entero("3.5")).toBeNull();
  });
});

describe("acto final", () => {
  const base = { ...ACTO_FINAL_VACIO, archivo: pdf(), clase_acto: "RES", numerado: "12", fecha_numerado: "2026-04-01" } as const;

  it("exige PDF, tipo de acto (AUTO/RES), numerado y fecha", () => {
    expect(validarActoFinal(ACTO_FINAL_VACIO, "simple")).toMatch(/Adjunte/);
    expect(validarActoFinal({ ...base, archivo: docx() }, "simple")).toMatch(/PDF/);
    expect(validarActoFinal({ ...base, clase_acto: "" }, "simple")).toMatch(/AUTO o RES/);
    expect(validarActoFinal({ ...base, numerado: "" }, "simple")).toMatch(/numerado/);
    expect(validarActoFinal(base, "simple")).toBeNull();
  });

  it("auto admite: técnico y fecha de visita", () => {
    expect(validarActoFinal(base, "admite")).toMatch(/técnico/);
    const ok = { ...base, tecnico_id: 32, fecha_visita_tecnica: "2026-05-02" } as const;
    expect(validarActoFinal(ok, "admite")).toBeNull();
    expect(bodyActoFinal(ok, "admite", 345)).toEqual({
      file_id: 345,
      clase_acto: "RES",
      numerado: "0012",
      fecha_numerado: "2026-04-01",
      tecnico_id: 32,
      fecha_visita_tecnica: "2026-05-02",
    });
  });

  it("decisión: requiere_memorias solo si OTORGADA (V8)", () => {
    expect(validarActoFinal({ ...base, decision: "OTORGADA" }, "decision")).toMatch(/memorias/);
    expect(bodyActoFinal({ ...base, decision: "OTORGADA", requiere_memorias: false }, "decision", 1)).toMatchObject({
      decision: "OTORGADA",
      requiere_memorias: false,
    });
    const negada = bodyActoFinal({ ...base, decision: "NEGADA", requiere_memorias: true }, "decision", 1);
    expect(negada).not.toHaveProperty("requiere_memorias");
  });

  it("recurso: resultado obligatorio", () => {
    expect(validarActoFinal(base, "recurso")).toMatch(/resultado/);
    expect(bodyActoFinal({ ...base, resultado: "CONFIRMA" }, "recurso", 1)).toMatchObject({ resultado: "CONFIRMA" });
  });
});

describe("concepto final (C.4)", () => {
  it("campos por tipo como el backend", () => {
    expect(camposVisibles(camposConcepto("etapa2"))).toEqual([
      "fecha_aceptacion",
      "caudal_fuente",
      "caudal_disponible",
      "caudal_otorgado",
      "num_usuarios",
    ]);
    expect(camposConcepto("adicional").obligatorios).toEqual(["file_id", "fecha_aceptacion"]);
    expect(camposConcepto("memorias").obligatorios).toContain("cumple");
    expect(camposConcepto("obras_segundo").obligatorios).toEqual(["file_id", "fecha_aceptacion", "cumple", "fecha_visita_tecnica"]);
  });

  it("valida obligatorios y arma el body solo con campos del tipo", () => {
    const campos = camposConcepto("etapa2");
    const f = { ...conceptoFinalInicial({ fecha_visita_tecnica: "2026-05-02" }), archivo: pdf(), fecha_aceptacion: "2026-05-20" };
    expect(validarConceptoFinal(f, campos)).toMatch(/Caudal fuente/);
    const lleno = { ...f, caudal_fuente: "10,5", caudal_disponible: "8", caudal_otorgado: "1.2", num_usuarios: "3" };
    expect(validarConceptoFinal(lleno, campos)).toBeNull();
    expect(bodyConceptoFinal(lleno, campos, 400)).toEqual({
      file_id: 400,
      fecha_aceptacion: "2026-05-20",
      caudal_fuente: 10.5,
      caudal_disponible: 8,
      caudal_otorgado: 1.2,
      num_usuarios: 3,
    });
  });

  it("cumple obligatorio en memorias; valores inválidos se rechazan", () => {
    const campos = camposConcepto("memorias");
    const f = { ...conceptoFinalInicial(), archivo: pdf(), fecha_aceptacion: "2026-05-20" };
    expect(validarConceptoFinal(f, campos)).toMatch(/Cumple/);
    expect(bodyConceptoFinal({ ...f, cumple: false }, campos, 1)).toEqual({
      file_id: 1,
      fecha_aceptacion: "2026-05-20",
      cumple: false,
    });
    const adicional = camposConcepto("adicional");
    expect(validarConceptoFinal({ ...f, caudal_fuente: "abc" }, adicional)).toMatch(/inválido/);
  });

  it("toma los datos que ya tiene el concepto", () => {
    expect(conceptoFinalInicial({ caudal_fuente: 2.5, cumple: true })).toMatchObject({ caudal_fuente: "2.5", cumple: true });
  });
});

describe("radicado", () => {
  it("valida y arma bodies de Radicado y respuesta", () => {
    const f = { radicado: " 2026ER1 ", fecha_radicado: "2026-06-01", archivo: pdf() };
    expect(validarRadicado({ ...f, radicado: "" })).toMatch(/radicado/);
    expect(validarRadicado({ ...f, radicado: "1234567890123456" })).toMatch(/máximo/);
    expect(validarRadicado(f)).toBeNull();
    expect(bodyRadicado(f, 9)).toEqual({ radicado: "2026ER1", fecha_radicado: "2026-06-01", file_id: 9 });
    expect(bodyRespuestaRequerimiento(f, 9, 4)).toEqual({
      version: 4,
      radicado_oficio_entrada: "2026ER1",
      fecha_oficio_entrada: "2026-06-01",
      doc_oficio_entrada_id: 9,
    });
  });
});
