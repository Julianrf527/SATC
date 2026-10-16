// Tipos del módulo app-recurso (Concesiones de Aguas Superficiales).
// Contrato: app-recurso/API.md secciones A y B. No se agregan campos que el
// backend no documente.
import type { ProcesoDetalle } from "@features/proceso-revision";
import type { ModeloGenerico, Municipio } from "@shared/types/common";

export type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

/** Tono que manda el backend junto a cada estado. */
export type TonoRecurso = "info" | "success" | "warning" | "error" | "neutral";

// ─── A.1 Catálogos ──────────────────────────────────────────────────────────

/** Valor del enum `uso_agua` (GET /catalogos/usos). */
export type UsoAgua = string;

export type CatalogosRecurso = {
  municipios: Municipio[];
  tipos_fuente: ModeloGenerico[];
  fuentes: ModeloGenerico[];
  usos: UsoAgua[];
  tipos_notificacion: ModeloGenerico[];
};

// ─── A.2 Expedientes ────────────────────────────────────────────────────────

export type TipoVinculo = "SOLICITANTE" | "TERCERO_INTERVINIENTE";

/** Persona de app-involved. Si app-involved no responde llega solo `{ id }`. */
export type PersonaInvolucrada = {
  id: number;
  tipo_documento?: string;
  numero_documento?: number | string;
  digito_verificacion?: string | null;
  nombre?: string;
  celular?: number | string | null;
  correo?: string | null;
  direccion?: string | null;
};

/** Involucrado resumido que trae cada fila del listado. */
export type InvolucradoResumen = {
  involucrado_id: number;
  tipo_vinculo: TipoVinculo;
  nombre: string;
  tipo_documento: string;
  numero_documento: number | string;
};

/** Fila de GET /recurso/expedientes. */
export type ExpedienteResumen = {
  id: number;
  version: number;
  radicado: string;
  fecha_radicado: string;
  expediente: string;
  numero_vital: string;
  nombre_predio: string;
  nombre_fuente: string;
  fecha_creacion: string;
  vereda: ModeloGenerico | null;
  municipio: ModeloGenerico | null;
  tipo_fuente: ModeloGenerico | null;
  involucrados: InvolucradoResumen[];
};

export type ListaExpedientesResponse = {
  data: ExpedienteResumen[];
  page: number;
  limit: number;
  totalCount: number;
};

/** Códigos de acción por vínculo (A.2). */
export type AccionVinculo = "editar_representante" | "desvincular" | (string & {});

/** Vínculo expediente ↔ persona (solicitante o tercero interviniente). */
export type VinculoInvolucrado = {
  id: number;
  expediente_id: number;
  involucrado_id: number;
  tipo_vinculo: TipoVinculo;
  representante_id: number | null;
  acto_admin_id: number | null;
  fecha_vinculacion: string;
  version: number;
  involucrado: PersonaInvolucrada;
  representante: PersonaInvolucrada | null;
  /** `true` si la persona es NIT (V14). */
  requiere_representante: boolean;
  /** Solo en vínculos SOLICITANTE y si el usuario puede gestionar. */
  acciones_disponibles?: AccionVinculo[];
};

/** Códigos de acción del expediente (A.2). */
export type AccionExpediente =
  | "editar_informacion_base"
  | "vincular_solicitante"
  | "descargar_expediente"
  | (string & {});

// ─── C. Etapas (árbol de GET /expedientes/{id} → `etapas`, API.md C.2) ─────

/** Funcionario de app-users (`nombre` null si app-users no respondió). */
export type PersonaRef = { id: number; nombre: string | null };

/** Resumen del proceso de revisión vigente de un nodo (forma de B.2 sin expediente). */
export type ResumenProceso = {
  proceso_id: number | null;
  tipo_documento: string | null;
  tipo_documento_etiqueta: string | null;
  estado_proceso: EstadoProcesoRecurso | null;
  proceso_activo: boolean;
  paso_actual: number | null;
  total_pasos: number;
  permisos_pendientes: { permiso: string; etiqueta: string }[];
  numero_devoluciones: number;
  version_actual: number;
  encargado_id: number | null;
  soy_encargado: boolean;
  puedo_revisar: boolean;
  requiere_mi_accion: boolean;
};

/** Códigos estables de `acciones_disponibles` de un nodo (tabla de C.2). */
export type AccionEtapa =
  | "asignarme"
  | "subir_version"
  | "revisar"
  | "cargar_version_final"
  | "seleccionar_tecnico"
  | "cargar_oficio_alcaldia"
  | "cargar_fijacion_aviso"
  | "cargar_constancia_fijacion"
  | "registrar_respuesta"
  | "registrar_ejecutoria"
  | "crear_recurso"
  | "registrar_planos"
  | "registrar_subsanacion"
  | "registrar_informe_usuario"
  | "registrar_nuevo_informe"
  | "vincular_tercero"
  | "editar_representante"
  | "desvincular"
  | "gestionar_anexos"
  | "super_cargar"
  | (string & {});

/** Códigos de acción del acto (B.3). */
export type AccionActo =
  | "editar_acto"
  | "eliminar_acto"
  | "crear_comunicacion"
  | "editar_comunicacion"
  | "eliminar_comunicacion"
  | "crear_notificacion"
  | "editar_notificacion"
  | "eliminar_notificacion"
  | (string & {});

/** Notificación de una persona (forma `InvolucradoNotificacion` + `version`). */
export type NotificacionActoRecurso = {
  id: number;
  acto_administrativo_id?: number;
  acto_admin_id?: number;
  involucrado_id: number;
  numerado: number | string;
  fecha_numerado: string;
  fecha_envio_citacion: string;
  fecha_constancia_citacion: string | null;
  documento_citacion_id: number;
  notificacion_exitosa: boolean;
  tipo_notificacion_id: number | null;
  documento_notificacion_id: number | null;
  fecha_notificacion: string | null;
  fecha_creacion: string | null;
  version?: number;
};

/** Acto del nodo (forma de GET /actos/administrativos/{id} sin notificables). */
export type ActoEtapa = {
  id: number;
  /** Clase interna según la etapa (AUTO_ADMITE, DECISION…). */
  tipo_acto: string;
  /** Lo que se muestra: Auto o Resolución. `null` en actos cargados antes de existir el dato. */
  clase_acto: "AUTO" | "RES" | null;
  numerado: number | string;
  fecha_numerado: string;
  documento_acto_administrativo_id: number;
  documento_acto_id?: number;
  fecha_creacion: string | null;
  etapa_tipo: string;
  etapa_id: number;
  comunicacion: {
    id: number;
    acto_administrativo_id?: number;
    numerado: number | string;
    fecha_numerado: string;
    fecha_envio: string;
    documento_comunicacion_id: number;
    fecha_creacion: string | null;
  } | null;
  notificacion: { id: number; fecha_creacion: string | null; involucrados: NotificacionActoRecurso[] } | null;
  /** Regla provisional de B: ≥1 notificación y todas exitosas. */
  notificado: boolean;
  acciones_disponibles: AccionActo[];
};

/** Documento anexo de un nodo (C.11). */
export type AnexoEtapa = {
  id: number;
  etapa_tipo: string;
  etapa_ref_id: number;
  nombre: string;
  documento_anexo_id: number;
  fecha_subida: string | null;
};

/** Nodo del árbol: todas las etapas y sub-procesos traen las mismas claves (C.2). */
export type NodoEtapa<D = Record<string, unknown>> = {
  codigo: string;
  etiqueta: string;
  etapa_tipo: string;
  id: number | null;
  version: number | null;
  existe: boolean;
  /** Existe o se puede crear. */
  habilitada: boolean;
  /** Textos de §6 cuando no está habilitada. */
  motivos_bloqueo: string[];
  encargado: PersonaRef | null;
  tecnico: PersonaRef | null;
  datos: D;
  proceso: ResumenProceso | null;
  acto: ActoEtapa | null;
  anexos: AnexoEtapa[];
  acciones_disponibles: AccionEtapa[];
};

export type TipoConcepto = "etapa2" | "adicional" | "memorias" | "subsanacion" | "obras" | "obras_segundo";
export type AmbitoRequerimiento = "etapa3" | "memorias" | "obras";
export type TipoDecision = "OTORGADA" | "NEGADA" | "DESISTIDA";
export type ResultadoRecurso = "REPONE" | "CONFIRMA" | "MODIFICA" | "ADICIONA";

export type DatosAdmite = {
  doc_oficio_alcaldia_id: number | null;
  doc_fijacion_aviso_id: number | null;
  doc_constancia_fijacion_aviso_id: number | null;
};

export type DatosConcepto = {
  fecha_visita_tecnica: string | null;
  fecha_aceptacion: string | null;
  caudal_fuente: number | null;
  caudal_disponible: number | null;
  caudal_otorgado: number | null;
  num_usuarios: number | null;
  cumple: boolean | null;
  doc_concepto_tecnico_id: number | null;
};

export type DatosRespuestaRequerimiento = {
  radicado_oficio_entrada: string | null;
  fecha_oficio_entrada: string | null;
  doc_oficio_entrada_id: number | null;
};

export type DatosDecision = {
  decision: TipoDecision | null;
  requiere_memorias: boolean | null;
  fecha_ejecutoria: string | null;
};

export type DatosRecurso = {
  radicado: string | null;
  fecha_radicado: string | null;
  doc_recurso_id: number | null;
  resultado: ResultadoRecurso | null;
};

/** Datos de un documento radicado por el usuario (planos, subsanación, informe). */
export type DatosRadicado = {
  radicado: string | null;
  fecha_radicado: string | null;
  doc_planos_id?: number | null;
  doc_planos_ajustados_id?: number | null;
  doc_informe_usuario_id?: number | null;
  informe_usuario_id?: number | null;
};

// Los nodos sin `datos` propios (actos de aprobación) llegan con `{}`.
type SinDatos = Record<string, never>;

/** Tipo de dato de un campo del concepto (cómo se pinta y se convierte). */
export type TipoCampoConcepto = "fecha" | "decimal" | "entero" | "si_no";

/** Un dato que pide el concepto (backend: `definicion_campos_concepto`, API.md C.4). */
export type CampoConceptoDef = { campo: string; tipo: TipoCampoConcepto; etiqueta: string; obligatorio: boolean };

/**
 * Campos que pide un tipo de concepto. `obligatorios` / `opcionales` incluyen
 * `file_id` (el PDF firmado); `campos` son solo los datos, en orden de pantalla.
 * Una sola fuente: el backend (nodo de concepto del árbol y GET /etapas/conceptos/{id}).
 */
export type CamposConcepto = { obligatorios: string[]; opcionales: string[]; campos: CampoConceptoDef[] };

export type NodoConcepto = NodoEtapa<DatosConcepto | SinDatos> & { tipo: TipoConcepto; campos: CamposConcepto };
export type NodoRequerimiento<D = SinDatos> = NodoEtapa<D> & { ambito: AmbitoRequerimiento };
export type NodoAdmite = NodoEtapa<DatosAdmite>;
export type NodoRequerimientoEtapa3 = NodoRequerimiento<DatosRespuestaRequerimiento> & {
  concepto_adicional: NodoConcepto;
};
export type NodoRecurso = NodoEtapa<DatosRecurso>;
export type NodoDecision = NodoEtapa<DatosDecision> & { recurso: NodoRecurso };
export type NodoRadicado = NodoEtapa<DatosRadicado>;
export type NodoAprobacion = NodoEtapa<SinDatos>;
export type NodoMemorias = NodoRadicado & {
  concepto: NodoConcepto;
  requerimiento: NodoRequerimiento;
  subsanacion: NodoRadicado & { concepto: NodoConcepto };
  aprobacion: NodoAprobacion;
};
export type NodoObras = NodoRadicado & {
  informe: NodoRadicado;
  concepto: NodoConcepto;
  requerimiento: NodoRequerimiento;
  nuevo_informe: NodoRadicado;
  concepto_segundo: NodoConcepto;
  aprobacion: NodoAprobacion;
};

/** Tercero interviniente: vínculo (A.4) + claves de nodo (sin `datos` ni `tecnico`). */
export type NodoTercero = Omit<VinculoInvolucrado, "acciones_disponibles"> &
  Pick<
    NodoEtapa,
    | "codigo"
    | "etiqueta"
    | "etapa_tipo"
    | "existe"
    | "habilitada"
    | "motivos_bloqueo"
    | "encargado"
    | "proceso"
    | "acto"
    | "anexos"
    | "acciones_disponibles"
  >;

export type CodigoEtapa = "admite" | "concepto" | "requerimiento" | "decision" | "memorias" | "obras";

/** Árbol de etapas (GET /etapas/{exp} o clave `etapas` de GET /expedientes/{id}). */
export type EtapasExpediente = {
  etapa_actual: CodigoEtapa | null;
  etapa_actual_etiqueta: string | null;
  orden: CodigoEtapa[];
  /** `vincular_tercero` (gestión). */
  acciones_disponibles: AccionEtapa[];
  admite: NodoAdmite;
  concepto: NodoConcepto;
  requerimiento: NodoRequerimientoEtapa3;
  decision: NodoDecision;
  memorias: NodoMemorias;
  obras: NodoObras;
  terceros: NodoTercero[];
};

/** Técnico seleccionable (GET /etapas/tecnicos). */
export type TecnicoRecurso = { id: number; nombre: string | null; correo: string | null };

/** GET /etapas/conceptos/{id}: lo que necesita el técnico desde Mis informes (C.4). */
export type ConceptoParaTecnico = {
  id: number;
  version: number;
  tipo: TipoConcepto;
  etiqueta: string;
  expediente: { id: number; expediente: string; radicado: string; nombre_predio: string; nombre_fuente: string };
  tecnico: PersonaRef;
  datos: DatosConcepto;
  campos: CamposConcepto;
  proceso: ResumenProceso | null;
  acciones_disponibles: AccionEtapa[];
};

/** Contexto de etapa en Mis informes y en el detalle del proceso (C.12). */
export type ContextoEtapa = {
  etapa_padre?: string | null;
  etapa_padre_etiqueta?: string | null;
  sub_proceso?: string | null;
};

/** GET /recurso/expedientes/{id} → `data`. */
export type ExpedienteDetalle = {
  id: number;
  version: number;
  radicado: string;
  fecha_radicado: string;
  expediente: string;
  numero_vital: string;
  nombre_predio: string;
  matricula_inmobiliaria: string;
  codigo_catastral: string;
  radicado_oficio_entrada: string;
  fecha_oficio_entrada: string;
  doc_comprobante_pago_id: number;
  comprobante_pago: { file_id: number; nombre: string } | null;
  vereda: ModeloGenerico | null;
  municipio: ModeloGenerico | null;
  tipo_fuente: ModeloGenerico | null;
  nombre_fuente: string;
  fuentes: ModeloGenerico[];
  usos: UsoAgua[];
  fecha_creacion: string;
  involucrados: VinculoInvolucrado[];
  acciones_disponibles: AccionExpediente[];
  etapas: EtapasExpediente;
};

// ─── A.3 Crear / editar ─────────────────────────────────────────────────────

/** Body `ExpedienteDatos` (todos obligatorios). */
export type ExpedienteDatos = {
  radicado: string;
  fecha_radicado: string;
  expediente: string;
  numero_vital: string;
  nombre_predio: string;
  matricula_inmobiliaria: string;
  codigo_catastral: string;
  radicado_oficio_entrada: string;
  fecha_oficio_entrada: string;
  doc_comprobante_pago_id: number;
  vereda_id: number;
  tipo_fuente_id: number;
  nombre_fuente: string;
  fuente_ids: number[];
  usos: UsoAgua[];
};

// ─── B.1 Revisión ───────────────────────────────────────────────────────────

export type PasoPermiso = {
  permiso: string;
  etiqueta: string;
  revisado: boolean;
  revisor_id?: number | null;
  revisor_nombre?: string | null;
  accion?: string | null;
  fecha_revision?: string | null;
};

export type PasoRevision = {
  numero: number;
  estado: "completado" | "actual" | "pendiente";
  permisos: PasoPermiso[];
};

/** `ProcesoDetalle` + campos propios de app-recurso (B.1). */
export type ProcesoDocumentoDetalle = ProcesoDetalle & ContextoEtapa & {
  expediente_id: number;
  expediente_radicado: string | null;
  expediente_codigo: string | null;
  tipo_documento: string;
  tipo_documento_etiqueta: string;
  etapa_tipo: string;
  etapa_etiqueta: string;
  etapa_ref_id: number;
  activo: boolean;
  encargado_id: number | null;
  encargado_nombre: string | null;
  paso_actual: number;
  total_pasos: number;
  pasos: PasoRevision[];
};

// ─── B.2 Mis informes ───────────────────────────────────────────────────────

export type EstadoProcesoRecurso = { codigo: string; etiqueta: string; tono: TonoRecurso };

export type MiDocumento = ContextoEtapa & {
  proceso_id: number;
  /** Rol principal (encargado primero). */
  rol: RolMiDocumento;
  /** Una sola fila si soy encargado y revisor del mismo proceso. */
  roles: RolMiDocumento[];
  /** `null` si no requiere mi acción. */
  accion_pendiente: string | null;
  tipo_documento: string;
  tipo_documento_etiqueta: string;
  estado_proceso: EstadoProcesoRecurso;
  proceso_activo: boolean;
  paso_actual: number;
  total_pasos: number;
  permisos_pendientes: { permiso: string; etiqueta: string }[];
  numero_devoluciones: number;
  version_actual: number;
  encargado_id: number | null;
  soy_encargado: boolean;
  puedo_revisar: boolean;
  requiere_mi_accion: boolean;
  expediente_id: number;
  expediente_radicado: string | null;
  expediente_codigo: string | null;
  etapa_tipo: string;
  etapa_etiqueta: string;
  etapa_ref_id: number;
  nombre: string;
  fecha_creacion: string;
  fecha_ultima_actualizacion: string;
};

export type RolMiDocumento = "encargado" | "revisor";

export type FiltrosMisDocumentosOpciones = {
  tipos_documento: { codigo: string; etiqueta: string }[];
  estados: EstadoProcesoRecurso[];
  roles: { codigo: RolMiDocumento; etiqueta: string }[];
};

/** B.2: una lista paginada; `conteos` es de todo el conjunto filtrado. */
export type MisDocumentosResponse = {
  data: {
    documentos: MiDocumento[];
    conteos: { total: number; requieren_accion: number };
    filtros: FiltrosMisDocumentosOpciones;
  };
  total: number;
  page: number;
  limit: number;
  total_pages: number;
};

// ─── Navegación entre pestañas ──────────────────────────────────────────────

/**
 * `location.state` para abrir un expediente (y opcionalmente una etapa) en
 * Gestionar / Consulta desde otra pantalla (Mis informes, notificaciones).
 */
export type NavegacionExpediente = {
  expedienteIdToSelect?: number;
  /** Id de pestaña del detalle (`manage/etapasProceso.ts`). */
  pestanaToSelect?: string;
};
