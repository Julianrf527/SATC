// Cargue directo de super gestión (C.9): documento final + datos de la etapa,
// sin asignación, revisión ni validaciones §6. Qué secciones lleva cada nodo y
// cómo se arma el body (solo campos con valor: el backend actualiza los no nulos).
import type { ResultadoRecurso, TipoConcepto, TipoDecision } from "../../types";
import type { RefNodo } from "../nodos";
import { type ClaseActo, esPdf, fechaValida, numeradoParaEnviar, numeradoValido } from "./comunes";
import {
  bodyConceptoFinal,
  camposConcepto,
  conceptoFinalInicial,
  validarCamposConcepto,
  type ConceptoFinalForm,
} from "./conceptoFinal";
import { MAX_RADICADO, RADICADO_VACIO, validarRadicado, type RadicadoForm } from "./radicado";

export type SeccionesSuper = {
  /** Acto administrativo (numerado, fecha, PDF). Se omite si el nodo ya tiene acto (409). */
  acto: boolean;
  /** El acto es lo único que se carga (aprobaciones y tercero). */
  actoObligatorio: boolean;
  /** Documento radicado por el usuario: su nombre, o `null` si no aplica. */
  radicado: string | null;
  /** Oficio a la Alcaldía, fijación del aviso y constancia (auto admite). */
  docsAdmite: boolean;
  /** Técnico y fecha de visita del auto admite (con técnico nace el concepto de la etapa 2). */
  tecnicoVisita: boolean;
  concepto: TipoConcepto | null;
  decision: boolean;
  resultado: boolean;
  /** Respuesta del usuario al requerimiento de la etapa 3. */
  respuesta: boolean;
  /** El body admite `version` (la fila del endpoint es la del nodo). */
  version: boolean;
  /**
   * Abogado encargado opcional (`encargado_acto_id`): etapas con acto y
   * columna de encargado. Sin elegir, la etapa nueva queda sin encargado
   * (expedientes viejos) y la existente conserva el suyo.
   */
  encargado: boolean;
};

const NINGUNA: SeccionesSuper = {
  acto: false,
  actoObligatorio: false,
  radicado: null,
  docsAdmite: false,
  tecnicoVisita: false,
  concepto: null,
  decision: false,
  resultado: false,
  respuesta: false,
  version: true,
  encargado: false,
};

export function seccionesSuper(ref: RefNodo, tieneActo: boolean): SeccionesSuper {
  const acto = !tieneActo;
  switch (ref.clase) {
    case "admite":
      return { ...NINGUNA, acto, docsAdmite: true, tecnicoVisita: true, encargado: true };
    case "concepto":
      return { ...NINGUNA, concepto: ref.tipo };
    case "requerimiento":
      return { ...NINGUNA, acto, respuesta: ref.ambito === "etapa3", encargado: true };
    case "decision":
      return { ...NINGUNA, acto, decision: true, encargado: true };
    case "recurso":
      return { ...NINGUNA, acto, radicado: "Escrito del recurso", resultado: true, encargado: true };
    case "memorias":
      return { ...NINGUNA, radicado: "Planos" };
    case "subsanacion":
      return { ...NINGUNA, radicado: "Planos ajustados", version: false };
    case "obras":
      return { ...NINGUNA, radicado: "Informe del usuario" };
    case "informe":
      return { ...NINGUNA, radicado: "Informe del usuario", version: false };
    case "nuevo_informe":
      return { ...NINGUNA, radicado: "Nuevo informe del usuario", version: false };
    case "aprobacion_memorias":
    case "aprobacion_obras":
      return { ...NINGUNA, acto, actoObligatorio: true, encargado: true };
    case "tercero":
      return { ...NINGUNA, acto, actoObligatorio: true, version: false };
  }
}

export type ActoSuperForm = { archivo: File | null; clase_acto: ClaseActo | ""; numerado: string; fecha_numerado: string };

export type SuperCargueForm = {
  acto: ActoSuperForm;
  radicado: RadicadoForm;
  respuesta: RadicadoForm;
  oficio: File | null;
  fijacion: File | null;
  constancia: File | null;
  tecnico_id: number | "";
  fecha_visita_tecnica: string;
  concepto: ConceptoFinalForm;
  /** Técnico del concepto (obligatorio para crearlo). */
  tecnico_encargado_id: number | "";
  decision: TipoDecision | "";
  requiere_memorias: boolean | null;
  fecha_ejecutoria: string;
  resultado: ResultadoRecurso | "";
  /** Abogado encargado (opcional, "" = sin encargado / conservar el actual). */
  encargado_acto_id: number | "";
};

export const SUPER_VACIO: SuperCargueForm = {
  acto: { archivo: null, clase_acto: "", numerado: "", fecha_numerado: "" },
  radicado: RADICADO_VACIO,
  respuesta: RADICADO_VACIO,
  oficio: null,
  fijacion: null,
  constancia: null,
  tecnico_id: "",
  fecha_visita_tecnica: "",
  concepto: conceptoFinalInicial(),
  tecnico_encargado_id: "",
  decision: "",
  requiere_memorias: null,
  fecha_ejecutoria: "",
  resultado: "",
  encargado_acto_id: "",
};

/** Archivos a subir a app-docs antes de enviar (clave → archivo). */
export function archivosSuper(s: SeccionesSuper, f: SuperCargueForm): Record<string, File | null> {
  return {
    acto: s.acto ? f.acto.archivo : null,
    radicado: s.radicado ? f.radicado.archivo : null,
    respuesta: s.respuesta ? f.respuesta.archivo : null,
    oficio: s.docsAdmite ? f.oficio : null,
    fijacion: s.docsAdmite ? f.fijacion : null,
    constancia: s.docsAdmite ? f.constancia : null,
    concepto: s.concepto ? f.concepto.archivo : null,
  };
}

const actoTocado = (a: ActoSuperForm) => !!(a.archivo || a.clase_acto || a.numerado.trim() || a.fecha_numerado);
const radicadoTocado = (r: RadicadoForm) => !!(r.archivo || r.radicado.trim() || r.fecha_radicado);

function validarRadicadoParcial(r: RadicadoForm, nombre: string): string | null {
  if (r.radicado.trim().length > MAX_RADICADO) return `${nombre}: el radicado admite máximo ${MAX_RADICADO} caracteres`;
  if (r.archivo && !esPdf(r.archivo)) return `${nombre}: el documento debe ser PDF`;
  return null;
}

/**
 * Primer error del formulario. `existe`: la fila del nodo ya existe (si no,
 * los datos obligatorios para crearla son requeridos, como en el backend).
 */
export function validarSuper(s: SeccionesSuper, f: SuperCargueForm, existe: boolean): string | null {
  if (s.acto && (s.actoObligatorio || actoTocado(f.acto))) {
    if (!f.acto.archivo) return "Adjunte el acto administrativo firmado (PDF)";
    if (!esPdf(f.acto.archivo)) return "El acto administrativo debe ser PDF";
    if (!f.acto.clase_acto) return "Seleccione el tipo de acto (AUTO o RES)";
    if (!numeradoValido(f.acto.numerado)) return "El numerado del acto debe ser un número de 1 a 4 dígitos";
    if (!fechaValida(f.acto.fecha_numerado)) return "Indique la fecha de numerado del acto";
  }
  if (s.actoObligatorio && !s.acto) return "Esta etapa ya tiene acto administrativo; corríjalo desde el acto";
  if (s.radicado) {
    const error = existe
      ? validarRadicadoParcial(f.radicado, s.radicado)
      : validarRadicado(f.radicado);
    if (error) return existe ? error : `${s.radicado}: ${error.charAt(0).toLowerCase()}${error.slice(1)}`;
  }
  if (s.respuesta && radicadoTocado(f.respuesta)) {
    const error = validarRadicado(f.respuesta);
    if (error) return `Respuesta del usuario: ${error.charAt(0).toLowerCase()}${error.slice(1)}`;
  }
  for (const [archivo, nombre] of [
    [f.oficio, "Oficio a la Alcaldía"],
    [f.fijacion, "Fijación del aviso"],
    [f.constancia, "Constancia de fijación"],
  ] as const) {
    if (s.docsAdmite && archivo && !esPdf(archivo)) return `${nombre}: debe ser PDF`;
  }
  if (s.tecnicoVisita && f.fecha_visita_tecnica && !f.tecnico_id) {
    return "Para registrar la fecha de visita seleccione también el técnico";
  }
  if (s.concepto) {
    if (!existe && !f.tecnico_encargado_id) return "Seleccione el técnico encargado del concepto";
    if (f.concepto.archivo && !esPdf(f.concepto.archivo)) return "El concepto firmado debe ser PDF";
    const error = validarCamposConcepto(f.concepto, { obligatorios: [], opcionales: todosCampos(s.concepto) });
    if (error) return error;
  }
  if (s.decision && f.decision === "OTORGADA" && f.requiere_memorias === null && !existe) {
    return "Indique si la decisión exige memorias de cálculo (planos)";
  }
  return null;
}

const todosCampos = (tipo: TipoConcepto) => {
  const c = camposConcepto(tipo);
  return [...c.obligatorios, ...c.opcionales].filter((x) => x !== "file_id");
};

/** Body del POST de super gestión. `ids`: file_id de cada archivo subido (clave de `archivosSuper`). */
export function bodySuper(
  s: SeccionesSuper,
  f: SuperCargueForm,
  ids: Record<string, number>,
  version: number | null,
): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  const poner = (clave: string, valor: unknown) => {
    if (valor !== null && valor !== undefined && valor !== "") body[clave] = valor;
  };
  if (s.version && version) body.version = version;
  if (s.encargado) poner("encargado_acto_id", f.encargado_acto_id);
  if (s.acto && ids.acto) {
    body.acto = {
      clase_acto: f.acto.clase_acto,
      numerado: numeradoParaEnviar(f.acto.numerado),
      fecha_numerado: f.acto.fecha_numerado,
      file_id: ids.acto,
    };
  }
  if (s.radicado) {
    poner("radicado", f.radicado.radicado.trim());
    poner("fecha_radicado", f.radicado.fecha_radicado);
    poner("file_id", ids.radicado);
  }
  if (s.respuesta && ids.respuesta) {
    poner("radicado_oficio_entrada", f.respuesta.radicado.trim());
    poner("fecha_oficio_entrada", f.respuesta.fecha_radicado);
    poner("doc_oficio_entrada_id", ids.respuesta);
  }
  if (s.docsAdmite) {
    poner("doc_oficio_alcaldia_id", ids.oficio);
    poner("doc_fijacion_aviso_id", ids.fijacion);
    poner("doc_constancia_fijacion_aviso_id", ids.constancia);
  }
  if (s.tecnicoVisita) {
    poner("tecnico_id", f.tecnico_id);
    poner("fecha_visita_tecnica", f.fecha_visita_tecnica);
  }
  if (s.concepto) {
    poner("tecnico_encargado_id", f.tecnico_encargado_id);
    const campos = { obligatorios: [], opcionales: todosCampos(s.concepto) };
    const { file_id: _sinArchivo, ...datos } = bodyConceptoFinal(f.concepto, campos, 0);
    void _sinArchivo;
    Object.entries(datos).forEach(([k, v]) => poner(k, v));
    poner("file_id", ids.concepto);
  }
  if (s.decision) {
    poner("decision", f.decision);
    if (f.decision === "OTORGADA") poner("requiere_memorias", f.requiere_memorias);
    poner("fecha_ejecutoria", f.fecha_ejecutoria);
  }
  if (s.resultado) poner("resultado", f.resultado);
  return body;
}

/** `true` si el body no carga nada (solo `version`). */
export function superVacio(body: Record<string, unknown>): boolean {
  return Object.keys(body).filter((k) => k !== "version").length === 0;
}
