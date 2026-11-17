-- ============================================================
-- infracciones_db — esquema y datos iniciales de app-infraction
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb infracciones_db && psql -U postgres -d infracciones_db -f infracciones_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict jspgYDdbGdTODsRsx4Q4RsCDmjBNYbpTyQttdFBD5U3bfkzFWzDkVdVEedZEWYB


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acto_administrativo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acto_administrativo (
    id integer NOT NULL,
    tipo_acto character varying(15),
    numerado integer,
    fecha_numerado date,
    fecha_asigncion_juridica date,
    documento_acto_administrativo_id integer,
    fecha_creacion timestamp with time zone NOT NULL
);


--
-- Name: acto_administrativo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acto_administrativo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acto_administrativo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acto_administrativo_id_seq OWNED BY public.acto_administrativo.id;


--
-- Name: auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auditoria (
    id integer NOT NULL,
    expediente_id integer,
    expediente_radicado character varying(15),
    usuario_id integer,
    tipo_evento character varying(30) NOT NULL,
    resultado character varying(10) NOT NULL,
    ip_address character varying(50),
    user_agent text,
    fecha timestamp with time zone NOT NULL,
    detalle text,
    datos_anteriores json,
    datos_nuevos json
);


--
-- Name: auditoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auditoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auditoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auditoria_id_seq OWNED BY public.auditoria.id;


--
-- Name: comunicacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comunicacion (
    id integer NOT NULL,
    numerado integer,
    fecha_numerado date,
    fecha_envio date,
    acto_administrativo_id integer,
    documento_comunicacion_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: comunicacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comunicacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comunicacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comunicacion_id_seq OWNED BY public.comunicacion.id;


--
-- Name: etapa_acoger_concepto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_acoger_concepto (
    id integer NOT NULL,
    tipo_acogida_concepto character varying(30) NOT NULL,
    expediente_id integer NOT NULL,
    dias_termino integer,
    fecha_termino_calculada date,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone NOT NULL
);


--
-- Name: etapa_acoger_concepto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_acoger_concepto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_acoger_concepto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_acoger_concepto_id_seq OWNED BY public.etapa_acoger_concepto.id;


--
-- Name: etapa_cierre; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_cierre (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone NOT NULL
);


--
-- Name: etapa_cierre_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_cierre_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_cierre_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_cierre_id_seq OWNED BY public.etapa_cierre.id;


--
-- Name: etapa_respuesta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_respuesta (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    radicado character varying(15),
    fecha_radicado date,
    documento_radicado_id integer,
    requiere_medida_preventiva boolean,
    fecha_creacion date
);


--
-- Name: etapa_respuesta_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_respuesta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_respuesta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_respuesta_id_seq OWNED BY public.etapa_respuesta.id;


--
-- Name: expediente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente (
    id integer NOT NULL,
    radicado character varying(15),
    fecha_radicado date,
    vereda_id integer,
    fecha_creacion timestamp with time zone NOT NULL,
    abogado_responsable_id integer,
    direccion character varying(100),
    descripcion character varying(400),
    archivado boolean,
    radicado_inicial_file_id integer
);


--
-- Name: expediente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expediente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expediente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expediente_id_seq OWNED BY public.expediente.id;


--
-- Name: expediente_involucrado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_involucrado (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    involucrado_id integer NOT NULL
);


--
-- Name: expediente_involucrado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expediente_involucrado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expediente_involucrado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expediente_involucrado_id_seq OWNED BY public.expediente_involucrado.id;


--
-- Name: expediente_recurso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_recurso (
    expediente_id integer NOT NULL,
    recurso_id integer NOT NULL
);


--
-- Name: expediente_tipo_afectacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_tipo_afectacion (
    expediente_id integer NOT NULL,
    tipo_afectacion_id integer NOT NULL
);


--
-- Name: informe_proceso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_proceso (
    informe_id integer NOT NULL,
    asignador_id integer,
    activo boolean DEFAULT true NOT NULL,
    id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    descripcion text,
    estado character varying(30) NOT NULL,
    creador_id integer NOT NULL,
    version_actual integer NOT NULL,
    numero_devoluciones integer NOT NULL,
    fecha_creacion timestamp with time zone NOT NULL,
    fecha_ultima_actualizacion timestamp with time zone NOT NULL
);


--
-- Name: informe_proceso_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_proceso_auditoria (
    id integer NOT NULL,
    accion character varying(50) NOT NULL,
    usuario_id integer,
    descripcion text,
    datos_adicionales json,
    fecha_accion timestamp with time zone NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: informe_proceso_auditoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_proceso_auditoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_proceso_auditoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_proceso_auditoria_id_seq OWNED BY public.informe_proceso_auditoria.id;


--
-- Name: informe_proceso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_proceso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_proceso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_proceso_id_seq OWNED BY public.informe_proceso.id;


--
-- Name: informe_proceso_revision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_proceso_revision (
    id integer NOT NULL,
    version_revisada integer NOT NULL,
    revisor_id integer NOT NULL,
    accion character varying(30) NOT NULL,
    comentarios text,
    adjunto_file_id integer,
    adjunto_url character varying(500),
    adjunto_nombre character varying(255),
    adjunto_size bigint,
    fecha_revision timestamp with time zone NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: informe_proceso_revision_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_proceso_revision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_proceso_revision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_proceso_revision_id_seq OWNED BY public.informe_proceso_revision.id;


--
-- Name: informe_proceso_revisor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_proceso_revisor (
    id integer NOT NULL,
    revisor_id integer NOT NULL,
    fecha_asignacion timestamp with time zone NOT NULL,
    notificado boolean NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: informe_proceso_revisor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_proceso_revisor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_proceso_revisor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_proceso_revisor_id_seq OWNED BY public.informe_proceso_revisor.id;


--
-- Name: informe_proceso_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_proceso_version (
    id integer NOT NULL,
    numero_version integer NOT NULL,
    file_id integer,
    archivo_url character varying(500) NOT NULL,
    archivo_nombre character varying(255) NOT NULL,
    archivo_size bigint,
    usuario_subida_id integer NOT NULL,
    comentario text,
    fecha_subida timestamp with time zone NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: informe_proceso_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_proceso_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_proceso_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_proceso_version_id_seq OWNED BY public.informe_proceso_version.id;


--
-- Name: informe_recurso_afectado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_recurso_afectado (
    id integer NOT NULL,
    informe_id integer NOT NULL,
    recurso character varying(20) NOT NULL,
    magnitud character varying(20),
    reversibilidad character varying(20),
    no_existe boolean NOT NULL,
    fecha_creacion timestamp with time zone NOT NULL
);


--
-- Name: informe_recurso_afectado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_recurso_afectado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_recurso_afectado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_recurso_afectado_id_seq OWNED BY public.informe_recurso_afectado.id;


--
-- Name: informe_tecnico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_tecnico (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    profesional_asignado_id integer,
    revisor_asignado_id integer,
    modo character varying(10) DEFAULT 'FLUJO'::character varying NOT NULL,
    fecha_programacion_visita date,
    fecha_recibido_informe date,
    fecha_aceptacion_informe date,
    documento_informe_id integer,
    tipo_informe character varying(20),
    fecha_creacion timestamp with time zone NOT NULL
);


--
-- Name: informe_tecnico_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_tecnico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_tecnico_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_tecnico_id_seq OWNED BY public.informe_tecnico.id;


--
-- Name: medida_preventiva; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.medida_preventiva (
    id integer NOT NULL,
    etapa_respuesta_id integer,
    tipo_medida_id integer,
    cantidad text,
    especie text,
    estado_medida boolean,
    acto_administrativo_id integer
);


--
-- Name: medida_preventiva_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.medida_preventiva_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: medida_preventiva_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.medida_preventiva_id_seq OWNED BY public.medida_preventiva.id;


--
-- Name: municipio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipio (
    id integer NOT NULL,
    nombre character varying(30) NOT NULL
);


--
-- Name: municipio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.municipio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: municipio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.municipio_id_seq OWNED BY public.municipio.id;


--
-- Name: notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notificacion (
    id integer NOT NULL,
    acto_administrativo_id integer NOT NULL,
    numerado integer,
    fecha_numerado date,
    involucrado_id integer NOT NULL,
    fecha_envio_citacion date,
    fecha_constancia_citacion date,
    documento_citacion_id integer,
    notificacion_exitosa boolean,
    fecha_notificacion timestamp with time zone NOT NULL,
    tipo_notificacion_id integer,
    documento_notificacion_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notificacion_id_seq OWNED BY public.notificacion.id;


--
-- Name: oficio_remite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oficio_remite (
    id integer NOT NULL,
    etapa_acoger_concepto_id integer NOT NULL,
    radicado character varying(11) NOT NULL,
    fecha_radicado character varying(10),
    fecha_remitido character varying(10) NOT NULL,
    archivo_remite_id integer NOT NULL
);


--
-- Name: oficio_remite_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.oficio_remite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oficio_remite_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.oficio_remite_id_seq OWNED BY public.oficio_remite.id;


--
-- Name: quejoso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quejoso (
    id integer NOT NULL,
    nombre character varying(150),
    telefono character varying(10),
    correo character varying(100),
    anonimo boolean NOT NULL
);


--
-- Name: quejoso_expediente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quejoso_expediente (
    quejoso_id integer NOT NULL,
    expediente_id integer NOT NULL
);


--
-- Name: quejoso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quejoso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quejoso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quejoso_id_seq OWNED BY public.quejoso.id;


--
-- Name: radicado_asociado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.radicado_asociado (
    id integer NOT NULL,
    radicado character varying(15),
    expediente_id integer NOT NULL
);


--
-- Name: radicado_asociado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.radicado_asociado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: radicado_asociado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.radicado_asociado_id_seq OWNED BY public.radicado_asociado.id;


--
-- Name: recurso_afectado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recurso_afectado (
    id integer NOT NULL,
    nombre character varying(15) NOT NULL
);


--
-- Name: recurso_afectado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.recurso_afectado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: recurso_afectado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.recurso_afectado_id_seq OWNED BY public.recurso_afectado.id;


--
-- Name: solicitud_informacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_informacion (
    id integer NOT NULL,
    etapa_acoger_concepto_id integer NOT NULL,
    radicado character varying(11) NOT NULL,
    fecha_radicado character varying(10) NOT NULL,
    archivo_solicitud_id integer NOT NULL
);


--
-- Name: solicitud_informacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_informacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_informacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_informacion_id_seq OWNED BY public.solicitud_informacion.id;


--
-- Name: tipo_afectacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_afectacion (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL,
    recurso_id integer
);


--
-- Name: tipo_afectacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_afectacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_afectacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_afectacion_id_seq OWNED BY public.tipo_afectacion.id;


--
-- Name: tipo_medida; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_medida (
    id integer NOT NULL,
    nombre text
);


--
-- Name: tipo_medida_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_medida_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_medida_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_medida_id_seq OWNED BY public.tipo_medida.id;


--
-- Name: tipo_notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_notificacion (
    id integer NOT NULL,
    nombre character varying(15) NOT NULL
);


--
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_notificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_notificacion_id_seq OWNED BY public.tipo_notificacion.id;


--
-- Name: vereda; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vereda (
    id integer NOT NULL,
    nombre character varying(30) NOT NULL,
    municipio_id integer NOT NULL
);


--
-- Name: vereda_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.vereda_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vereda_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.vereda_id_seq OWNED BY public.vereda.id;


--
-- Name: acto_administrativo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_administrativo ALTER COLUMN id SET DEFAULT nextval('public.acto_administrativo_id_seq'::regclass);


--
-- Name: auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria ALTER COLUMN id SET DEFAULT nextval('public.auditoria_id_seq'::regclass);


--
-- Name: comunicacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion ALTER COLUMN id SET DEFAULT nextval('public.comunicacion_id_seq'::regclass);


--
-- Name: etapa_acoger_concepto id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_acoger_concepto ALTER COLUMN id SET DEFAULT nextval('public.etapa_acoger_concepto_id_seq'::regclass);


--
-- Name: etapa_cierre id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre ALTER COLUMN id SET DEFAULT nextval('public.etapa_cierre_id_seq'::regclass);


--
-- Name: etapa_respuesta id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_respuesta ALTER COLUMN id SET DEFAULT nextval('public.etapa_respuesta_id_seq'::regclass);


--
-- Name: expediente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente ALTER COLUMN id SET DEFAULT nextval('public.expediente_id_seq'::regclass);


--
-- Name: expediente_involucrado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado ALTER COLUMN id SET DEFAULT nextval('public.expediente_involucrado_id_seq'::regclass);


--
-- Name: informe_proceso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso ALTER COLUMN id SET DEFAULT nextval('public.informe_proceso_id_seq'::regclass);


--
-- Name: informe_proceso_auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_auditoria ALTER COLUMN id SET DEFAULT nextval('public.informe_proceso_auditoria_id_seq'::regclass);


--
-- Name: informe_proceso_revision id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revision ALTER COLUMN id SET DEFAULT nextval('public.informe_proceso_revision_id_seq'::regclass);


--
-- Name: informe_proceso_revisor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revisor ALTER COLUMN id SET DEFAULT nextval('public.informe_proceso_revisor_id_seq'::regclass);


--
-- Name: informe_proceso_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_version ALTER COLUMN id SET DEFAULT nextval('public.informe_proceso_version_id_seq'::regclass);


--
-- Name: informe_recurso_afectado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_recurso_afectado ALTER COLUMN id SET DEFAULT nextval('public.informe_recurso_afectado_id_seq'::regclass);


--
-- Name: informe_tecnico id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_tecnico ALTER COLUMN id SET DEFAULT nextval('public.informe_tecnico_id_seq'::regclass);


--
-- Name: medida_preventiva id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva ALTER COLUMN id SET DEFAULT nextval('public.medida_preventiva_id_seq'::regclass);


--
-- Name: municipio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio ALTER COLUMN id SET DEFAULT nextval('public.municipio_id_seq'::regclass);


--
-- Name: notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- Name: oficio_remite id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oficio_remite ALTER COLUMN id SET DEFAULT nextval('public.oficio_remite_id_seq'::regclass);


--
-- Name: quejoso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quejoso ALTER COLUMN id SET DEFAULT nextval('public.quejoso_id_seq'::regclass);


--
-- Name: radicado_asociado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.radicado_asociado ALTER COLUMN id SET DEFAULT nextval('public.radicado_asociado_id_seq'::regclass);


--
-- Name: recurso_afectado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_afectado ALTER COLUMN id SET DEFAULT nextval('public.recurso_afectado_id_seq'::regclass);


--
-- Name: solicitud_informacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_informacion ALTER COLUMN id SET DEFAULT nextval('public.solicitud_informacion_id_seq'::regclass);


--
-- Name: tipo_afectacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_afectacion ALTER COLUMN id SET DEFAULT nextval('public.tipo_afectacion_id_seq'::regclass);


--
-- Name: tipo_medida id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_medida ALTER COLUMN id SET DEFAULT nextval('public.tipo_medida_id_seq'::regclass);


--
-- Name: tipo_notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_notificacion ALTER COLUMN id SET DEFAULT nextval('public.tipo_notificacion_id_seq'::regclass);


--
-- Name: vereda id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda ALTER COLUMN id SET DEFAULT nextval('public.vereda_id_seq'::regclass);


--
-- Data for Name: acto_administrativo; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.acto_administrativo (id, tipo_acto, numerado, fecha_numerado, fecha_asigncion_juridica, documento_acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auditoria (id, expediente_id, expediente_radicado, usuario_id, tipo_evento, resultado, ip_address, user_agent, fecha, detalle, datos_anteriores, datos_nuevos) FROM stdin;
\.


--
-- Data for Name: comunicacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comunicacion (id, numerado, fecha_numerado, fecha_envio, acto_administrativo_id, documento_comunicacion_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_acoger_concepto; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_acoger_concepto (id, tipo_acogida_concepto, expediente_id, dias_termino, fecha_termino_calculada, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_cierre; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_cierre (id, expediente_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_respuesta; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_respuesta (id, expediente_id, radicado, fecha_radicado, documento_radicado_id, requiere_medida_preventiva, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: expediente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente (id, radicado, fecha_radicado, vereda_id, fecha_creacion, abogado_responsable_id, direccion, descripcion, archivado, radicado_inicial_file_id) FROM stdin;
\.


--
-- Data for Name: expediente_involucrado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_involucrado (id, expediente_id, involucrado_id) FROM stdin;
\.


--
-- Data for Name: expediente_recurso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_recurso (expediente_id, recurso_id) FROM stdin;
\.


--
-- Data for Name: expediente_tipo_afectacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_tipo_afectacion (expediente_id, tipo_afectacion_id) FROM stdin;
\.


--
-- Data for Name: informe_proceso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_proceso (informe_id, asignador_id, activo, id, nombre, descripcion, estado, creador_id, version_actual, numero_devoluciones, fecha_creacion, fecha_ultima_actualizacion) FROM stdin;
\.


--
-- Data for Name: informe_proceso_auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_proceso_auditoria (id, accion, usuario_id, descripcion, datos_adicionales, fecha_accion, proceso_id) FROM stdin;
\.


--
-- Data for Name: informe_proceso_revision; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_proceso_revision (id, version_revisada, revisor_id, accion, comentarios, adjunto_file_id, adjunto_url, adjunto_nombre, adjunto_size, fecha_revision, proceso_id) FROM stdin;
\.


--
-- Data for Name: informe_proceso_revisor; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_proceso_revisor (id, revisor_id, fecha_asignacion, notificado, proceso_id) FROM stdin;
\.


--
-- Data for Name: informe_proceso_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_proceso_version (id, numero_version, file_id, archivo_url, archivo_nombre, archivo_size, usuario_subida_id, comentario, fecha_subida, proceso_id) FROM stdin;
\.


--
-- Data for Name: informe_recurso_afectado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_recurso_afectado (id, informe_id, recurso, magnitud, reversibilidad, no_existe, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: informe_tecnico; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_tecnico (id, expediente_id, profesional_asignado_id, revisor_asignado_id, modo, fecha_programacion_visita, fecha_recibido_informe, fecha_aceptacion_informe, documento_informe_id, tipo_informe, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: medida_preventiva; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.medida_preventiva (id, etapa_respuesta_id, tipo_medida_id, cantidad, especie, estado_medida, acto_administrativo_id) FROM stdin;
\.


--
-- Data for Name: municipio; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.municipio (id, nombre) FROM stdin;
1	Almeida
2	Boyacá
3	Campohermoso
4	Chinavita
5	Chivor
6	Ciénega
7	Garagoa
8	Guateque
9	Guayatá
10	Jenesano
11	La Capilla
12	Macanal
13	Nuevo Colón
14	Pachavita
15	Ramiriquí
16	San Luis de Gaceno
17	Santa María
18	Somondoco
19	Sutatenza
20	Tenza
21	Tibaná
22	Turmequé
23	Ventaquemada
24	Viracachá
25	Úmbita
\.


--
-- Data for Name: notificacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notificacion (id, acto_administrativo_id, numerado, fecha_numerado, involucrado_id, fecha_envio_citacion, fecha_constancia_citacion, documento_citacion_id, notificacion_exitosa, fecha_notificacion, tipo_notificacion_id, documento_notificacion_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: oficio_remite; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.oficio_remite (id, etapa_acoger_concepto_id, radicado, fecha_radicado, fecha_remitido, archivo_remite_id) FROM stdin;
\.


--
-- Data for Name: quejoso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quejoso (id, nombre, telefono, correo, anonimo) FROM stdin;
\.


--
-- Data for Name: quejoso_expediente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quejoso_expediente (quejoso_id, expediente_id) FROM stdin;
\.


--
-- Data for Name: radicado_asociado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.radicado_asociado (id, radicado, expediente_id) FROM stdin;
\.


--
-- Data for Name: recurso_afectado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.recurso_afectado (id, nombre) FROM stdin;
1	Agua
2	Aire
3	Bosque
4	Fauna
5	Flora
6	Suelo
\.


--
-- Data for Name: solicitud_informacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.solicitud_informacion (id, etapa_acoger_concepto_id, radicado, fecha_radicado, archivo_solicitud_id) FROM stdin;
\.


--
-- Data for Name: tipo_afectacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_afectacion (id, nombre, recurso_id) FROM stdin;
1	Uso	1
2	Contaminación	1
3	Vertimiento	1
4	Contaminación	2
5	Emisiones	2
6	Tala	3
7	Quema	3
8	Daño	3
9	Caza	4
10	Captura	4
11	Daño	4
12	Daño	5
13	Extracción	5
14	Vertimiento	6
15	Eclosión	6
16	Erosión	6
\.


--
-- Data for Name: tipo_medida; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_medida (id, nombre) FROM stdin;
1	Decomiso preventivo
2	Suspensión del proyecto
3	Estudios y evaluaciones requeridas para conocer la naturaleza de los daños
4	Suspensión de actividades o de obras
5	Clausura temporal
6	Decomiso preventivo
7	Aprehensión preventiva
8	Congelación o suspensión de venta-empleo
9	Amonestación escrita
10	Elaboración de estudios ambientales
\.


--
-- Data for Name: tipo_notificacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_notificacion (id, nombre) FROM stdin;
1	Personal
2	Correo
3	Publicación
\.


--
-- Data for Name: vereda; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.vereda (id, nombre, municipio_id) FROM stdin;
1	Belen	1
2	Curiavaca Abajo	1
3	Curiavaca Arriba	1
4	Molinos	1
5	Rosal	1
6	Tibaita	1
7	Tona	1
8	Umbavita	1
9	Yavir	1
11	Huerta Chica	2
12	Huerta Grande Sector 1	2
13	Huerta Grande Sector 2	2
14	Pachaquira	2
15	Rique	2
16	Rupaguata	2
17	Siraquita	2
18	Soconsaque Occidente	2
19	Soconsaque Oriente	2
20	Vanegas Sector Norte	2
21	Vanegas Sector Sur	2
22	Castañal	3
23	Cañadas	3
24	Cedros Centro	3
26	Choma	3
27	Colombia	3
28	El Limon	3
29	El Rodeo	3
30	Encenillo	3
31	Guamal	3
32	Hoya Grande	3
33	Huerta Vieja	3
34	Macanalito	3
35	Palmichal	3
36	Sababetas	3
37	San Agustin	3
38	San José	3
39	Teguas	3
40	Toldo	3
41	Yoteguengue	3
42	Centro Abajo	4
43	Centro Arriba	4
44	Curavita	4
45	Fusa	4
46	Guayabal	4
47	Jordan	4
48	Juntas	4
49	Montejo	4
50	Mundo Nuevo	4
51	Quinchos	4
52	Sicha	4
53	Usillo	4
54	Valle	4
55	Zanja Abajo	4
56	Zanja Arriba	4
57	Alimentos	5
58	Camoyo	5
60	Chivor Chiquita	5
61	El Higueron	5
62	El Pino	5
63	Guali	5
64	Jagua la Playa	5
65	La Esmeralda	5
66	La Esperanza	5
67	San Cayetano	5
68	San Francisco	5
69	San Martin	5
70	Sinai	5
71	Albanil	6
72	Calabazal	6
73	Cebadal	6
74	El Plan	6
75	Espinal	6
76	Guatareta	6
77	Manzanos	6
78	Piedra Larga	6
79	Reavita	6
80	San Vicente	6
81	Tapias	6
82	Arada Chiquita	7
83	Arada Grande	7
84	Bancos de Arada	7
85	Bancos de Paramo	7
86	Bojaca	7
87	Caldera Abajo	7
88	Caldera Arriba	7
89	Caracol	7
90	Cienaga Guarumal	7
91	Cienaga Tablon	7
92	Cienaga Valvanera	7
93	Cuanica Abajo	7
94	Cucharero	7
95	Cunica Arriba	7
96	Cunica Molino	7
97	Curjal	7
98	Escobal	7
99	Fumbaque	7
100	Guayabal	7
101	Hipaquira	7
102	Maciecal	7
103	Manzanos Abajo	7
104	Quicua Abajo	7
105	Quicua Arriba	7
106	Resguardo Abajo	7
107	Resguardo Arriba	7
108	Resguardo Machilero	7
109	Resguardo Manzanos Arriba	7
110	Senda Abajo	7
111	Senda Arriba	7
112	Cantoras	8
113	Chinquica	8
114	Chorro de Oro	8
115	Chorro Tinto	8
116	Gaunza Abajo	8
117	Gaunza Arriba	8
118	Goteras	8
119	Juntas	8
120	Llano Grande	8
121	Mortiño	8
122	Munanta	8
123	Piedra Parada	8
124	Pozos	8
125	Puentes	8
126	Rosales	8
127	Sibata	8
128	Siravita	8
129	Suaitoque	8
130	Tincachoque	8
131	Ubajuca	8
132	Barro Negro	9
133	Caliche Abajo	9
134	Caliche Arriba	9
135	Carrizal	9
136	Chitavita	9
137	Ciavita Ii	9
138	Ciavita I	9
139	Ciavita Iii	9
140	El Tablon	9
141	Escaleras	9
142	Fonsaque Abajo	9
143	Fonsaque Arriba	9
144	Guaquira	9
145	Guarumal	9
146	Guavita	9
147	Hato Viejo	9
148	Las Juntas	9
149	Plaza Abajo	9
150	Plaza Arriba	9
151	Potreritos	9
152	Rincon Abajo	9
153	Rincon Arriba	9
154	Romaquira	9
155	Sochaquira Abajo	9
156	Sochaquira Arriba	9
157	Sunuba	9
158	Tencua Abajo	9
159	Tencua Arriba	9
160	Volcan	9
161	Baganique Alto	10
162	Baganique Bajo	10
163	Baganique Medio	10
164	Cardonal	10
165	Carrizal	10
166	Dulceyes	10
167	Foraquira	10
168	Naranjos	10
169	Nonceta	10
170	Paeces	10
171	Palenque	10
172	Pantano Colorado	10
173	Piranguata	10
174	Pulidos	10
175	Rodriguez	10
176	Soleres	10
177	Supaneca	10
178	Volador	10
179	Barro Blanco Abajo	11
180	Barroblanco Arriba	11
181	Camagoa	11
183	Chaguatoque	11
184	Chicio	11
185	Hato	11
186	Palma Abajo	11
187	Palma Arriba	11
188	Paramo	11
189	Peñas	11
190	Suntafita	11
191	Truco	11
192	Ubaneca	11
193	Zinc	11
194	Agua Blanca	12
196	Datil Chiquito	12
197	Datil Grande	12
198	Guavio	12
199	La Mesa	12
200	La Vega	12
201	Limon	12
202	Media Estancia	12
203	Muceño	12
204	Naranjos	12
205	Pantanos	12
206	Perdiguiz Chiquito	12
207	Perdiguiz Grande	12
208	Peña Blanca	12
209	Quebrada Negra	12
210	Tibacota	12
211	Vijagual	12
212	Volador	12
213	Alfaras	13
214	Aposentos	13
215	Carbonera	13
216	Centro Rural	13
217	El Uvo	13
218	Fiota	13
219	Invita	13
220	Jabonera	13
221	Llano Grande	13
222	Pavaquirá	13
223	Potreros	13
224	Sorca	13
225	Tapias	13
226	Tejar Abajo	13
227	Tejar Arriba	13
228	Zapatero	13
229	Agua Quina	14
230	Buenavista	14
232	Guacal	14
233	Hato Grande	14
234	Llano Grande	14
235	Pie de Peña	14
236	Soaquira	14
237	Caicedos	15
238	Chuscal	15
239	Comun	15
240	El Pabellon	15
241	Escobal	15
242	Faravita	15
243	Farquenta	15
244	Fernandez	15
245	Fragua - Hervideros	15
246	Gachantiva	15
247	Guacamayas	15
248	Guayabal	15
249	Hervidero	15
250	Hortigal	15
251	Naguata	15
252	Pantanno Largo	15
253	Peñas	15
254	Potreros	15
255	Resguardo Alto	15
256	Resguardo Bajo	15
257	Romazal	15
258	Rosal	15
259	Santana	15
260	Santuario	15
261	Agua Buena	16
262	Arrayanes	16
263	Caracol	16
264	Catatumbo	16
265	Caño Blanco	16
266	Caño Grande	16
267	Caño Tigre	16
269	Centro Guamal	16
270	Centro Horizonte	16
271	Cumaral	16
272	El Cairo	16
273	El Carmen	16
274	Gazajarro	16
275	Gazapal	16
276	Granja	16
277	Guichirales	16
278	La Colonia	16
279	La Dorada	16
280	La Dorada del Guavio	16
281	La Esperanza	16
282	La Mesa	16
283	La Selva	16
284	Laderas	16
285	Macanalito	16
286	Marañal	16
287	Monumento	16
288	Pensamiento	16
289	Piñuela	16
290	Planada Seca	16
291	Rio Chiquito	16
292	San Agustín del Chuy	16
293	San Carlos	16
294	San Isidro	16
295	San José del Chuy	16
296	San Pedro	16
297	Santa María	16
298	Tontogue Alto	16
299	Tontogue Bajo	16
300	Balcones	17
301	Calichana	17
302	Carbonera	17
303	Caño Negro	17
304	Ceiba Chiquita	17
305	Ceiba Grande	17
306	Charco Largo	17
307	Culima	17
308	De Planadas	17
309	El Retiro	17
310	Guaduales	17
311	Hormigueros	17
312	Hoya Grande	17
313	La Victoria	17
314	Nazareth	17
315	San Agustín	17
316	San Miguel	17
317	San Rafael	17
318	Santa Cecilia	17
319	Vara Santa	17
320	Barreras	18
321	Bohórquez	18
322	Boya I	18
323	Boya Ii	18
324	Cabrera	18
325	Cayos	18
326	Cobavita	18
327	Cucuavaca	18
328	Guaduas	18
329	Pancupa	18
330	Resguardo	18
331	Richa	18
332	Sabaneta	18
333	San Antonio	18
334	San Sebastian	18
335	Zarzal	18
336	Boqueron	19
337	Gaque	19
338	Guamo	19
339	Irson	19
340	Paramo	19
341	Piedra Larga	19
342	Salitre	19
343	Siguique	19
344	Aposento	20
345	Barzal	20
346	Chaguatoque	20
347	Cora Chiquito	20
348	Cora Grande	20
349	Mutatea	20
350	Quebradas	20
351	Resguardo	20
352	Rucha	20
353	Valle Grande Abajo	20
354	Valle Grande Arriba	20
355	Volcan	20
356	Arrayan	21
357	Batan	21
358	Bayeta	21
359	Carare	21
360	Chiguata	21
361	El Carmen	21
362	Gambita	21
363	Juana Ruiz	21
364	Laja	21
365	Las Juntas	21
366	Lavaderos	21
367	Mangles	21
368	Maranta	21
369	Mombita	21
370	Pie de Peña	21
371	Piedras de Candela	21
372	Quichatoque	21
373	Ruche	21
374	San José	21
375	Sastoque	21
376	Sirama	21
377	Sirata	21
378	Sitanta	21
379	Siuman	21
380	Supaneca Abajo	21
381	Supaneca Arriba	21
382	Suta Abajo	21
383	Suta Arriba	21
384	Zanja	21
386	Chirata	22
387	Chquinquirá	22
388	Guanzaque	22
389	Joraquira	22
390	Joyagua	22
391	Jurata	22
392	Pascata	22
393	Pozo Negro	22
394	Rinchoque	22
395	Rosales	22
396	Siguinique	22
397	Teguaneque	22
398	V Blanco	22
399	Bojirque	23
400	Boqueron	23
401	Capellania	23
402	Choquira	23
403	Compromiso	23
404	El Carmen	23
405	Estancia Grande	23
406	Frutillo	23
407	Hato	23
408	Jurpa	23
409	Mesa	23
410	Montoya	23
411	Nerita	23
412	Nerita Pd Piedra	23
413	Parroquia Vieja	23
414	Puente Poyaca	23
415	Siata	23
416	Sota	23
417	Supata	23
418	Caros	24
420	Chen	24
421	Galindos	24
422	Icarina	24
423	La Isla	24
424	Naranjos	24
425	Parras	24
426	Pirguata	24
427	Pueblo Viejo	24
428	Altamizal	25
429	Boqueron	25
430	Bosque	25
432	Chuscal	25
433	Jupal	25
434	Loma Gorda	25
435	Molino	25
436	Nueve Pilas	25
437	Pavas	25
438	Rosal	25
439	Sisa	25
440	Tambor Chiquito	25
441	Tambor Grande	25
442	Uvero	25
443	Casco Urbano	1
444	Casco Urbano	2
445	Casco Urbano	3
446	Casco Urbano	4
447	Casco Urbano	5
448	Casco Urbano	6
449	Casco Urbano	7
450	Casco Urbano	8
451	Casco Urbano	9
452	Casco Urbano	10
453	Casco Urbano	11
454	Casco Urbano	12
455	Casco Urbano	13
456	Casco Urbano	14
457	Casco Urbano	15
458	Casco Urbano	16
459	Casco Urbano	17
460	Casco Urbano	18
461	Casco Urbano	19
462	Casco Urbano	20
463	Casco Urbano	21
464	Casco Urbano	22
465	Casco Urbano	23
466	Casco Urbano	24
467	Casco Urbano	25
\.


--
-- Name: acto_administrativo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.acto_administrativo_id_seq', 1, false);


--
-- Name: auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auditoria_id_seq', 1, false);


--
-- Name: comunicacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comunicacion_id_seq', 1, false);


--
-- Name: etapa_acoger_concepto_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_acoger_concepto_id_seq', 1, false);


--
-- Name: etapa_cierre_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_cierre_id_seq', 1, false);


--
-- Name: etapa_respuesta_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_respuesta_id_seq', 1, false);


--
-- Name: expediente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_id_seq', 1, false);


--
-- Name: expediente_involucrado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_involucrado_id_seq', 1, false);


--
-- Name: informe_proceso_auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_proceso_auditoria_id_seq', 1, false);


--
-- Name: informe_proceso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_proceso_id_seq', 1, false);


--
-- Name: informe_proceso_revision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_proceso_revision_id_seq', 1, false);


--
-- Name: informe_proceso_revisor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_proceso_revisor_id_seq', 1, false);


--
-- Name: informe_proceso_version_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_proceso_version_id_seq', 1, false);


--
-- Name: informe_recurso_afectado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_recurso_afectado_id_seq', 1, false);


--
-- Name: informe_tecnico_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_tecnico_id_seq', 1, false);


--
-- Name: medida_preventiva_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.medida_preventiva_id_seq', 1, false);


--
-- Name: municipio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.municipio_id_seq', 1, false);


--
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 1, false);


--
-- Name: oficio_remite_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.oficio_remite_id_seq', 1, false);


--
-- Name: quejoso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.quejoso_id_seq', 1, false);


--
-- Name: radicado_asociado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.radicado_asociado_id_seq', 1, false);


--
-- Name: recurso_afectado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.recurso_afectado_id_seq', 1, false);


--
-- Name: solicitud_informacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.solicitud_informacion_id_seq', 1, false);


--
-- Name: tipo_afectacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_afectacion_id_seq', 1, false);


--
-- Name: tipo_medida_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_medida_id_seq', 1, false);


--
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_notificacion_id_seq', 1, false);


--
-- Name: vereda_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.vereda_id_seq', 1, false);


--
-- Name: acto_administrativo acto_administrativo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_administrativo
    ADD CONSTRAINT acto_administrativo_pkey PRIMARY KEY (id);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);


--
-- Name: comunicacion comunicacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion
    ADD CONSTRAINT comunicacion_pkey PRIMARY KEY (id);


--
-- Name: etapa_acoger_concepto etapa_acoger_concepto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_acoger_concepto
    ADD CONSTRAINT etapa_acoger_concepto_pkey PRIMARY KEY (id);


--
-- Name: etapa_cierre etapa_cierre_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre
    ADD CONSTRAINT etapa_cierre_pkey PRIMARY KEY (id);


--
-- Name: etapa_respuesta etapa_respuesta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_respuesta
    ADD CONSTRAINT etapa_respuesta_pkey PRIMARY KEY (id);


--
-- Name: etapa_respuesta etapa_respuesta_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_respuesta
    ADD CONSTRAINT etapa_respuesta_radicado_key UNIQUE (radicado);


--
-- Name: expediente_involucrado expediente_involucrado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_pkey PRIMARY KEY (id);


--
-- Name: expediente expediente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_pkey PRIMARY KEY (id);


--
-- Name: expediente expediente_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_radicado_key UNIQUE (radicado);


--
-- Name: expediente_recurso expediente_recurso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT expediente_recurso_pkey PRIMARY KEY (expediente_id, recurso_id);


--
-- Name: expediente_tipo_afectacion expediente_tipo_afectacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_tipo_afectacion
    ADD CONSTRAINT expediente_tipo_afectacion_pkey PRIMARY KEY (expediente_id, tipo_afectacion_id);


--
-- Name: informe_proceso_auditoria informe_proceso_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_auditoria
    ADD CONSTRAINT informe_proceso_auditoria_pkey PRIMARY KEY (id);


--
-- Name: informe_proceso informe_proceso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso
    ADD CONSTRAINT informe_proceso_pkey PRIMARY KEY (id);


--
-- Name: informe_proceso_revision informe_proceso_revision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revision
    ADD CONSTRAINT informe_proceso_revision_pkey PRIMARY KEY (id);


--
-- Name: informe_proceso_revisor informe_proceso_revisor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revisor
    ADD CONSTRAINT informe_proceso_revisor_pkey PRIMARY KEY (id);


--
-- Name: informe_proceso_version informe_proceso_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_version
    ADD CONSTRAINT informe_proceso_version_pkey PRIMARY KEY (id);


--
-- Name: informe_recurso_afectado informe_recurso_afectado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_recurso_afectado
    ADD CONSTRAINT informe_recurso_afectado_pkey PRIMARY KEY (id);


--
-- Name: informe_tecnico informe_tecnico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_tecnico
    ADD CONSTRAINT informe_tecnico_pkey PRIMARY KEY (id);


--
-- Name: medida_preventiva medida_preventiva_etapa_respuesta_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_etapa_respuesta_id_key UNIQUE (etapa_respuesta_id);


--
-- Name: medida_preventiva medida_preventiva_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_pkey PRIMARY KEY (id);


--
-- Name: municipio municipio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_pkey PRIMARY KEY (id);


--
-- Name: notificacion notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_pkey PRIMARY KEY (id);


--
-- Name: oficio_remite oficio_remite_etapa_acoger_concepto_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oficio_remite
    ADD CONSTRAINT oficio_remite_etapa_acoger_concepto_id_key UNIQUE (etapa_acoger_concepto_id);


--
-- Name: oficio_remite oficio_remite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oficio_remite
    ADD CONSTRAINT oficio_remite_pkey PRIMARY KEY (id);


--
-- Name: quejoso_expediente quejoso_expediente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quejoso_expediente
    ADD CONSTRAINT quejoso_expediente_pkey PRIMARY KEY (quejoso_id, expediente_id);


--
-- Name: quejoso quejoso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quejoso
    ADD CONSTRAINT quejoso_pkey PRIMARY KEY (id);


--
-- Name: radicado_asociado radicado_asociado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.radicado_asociado
    ADD CONSTRAINT radicado_asociado_pkey PRIMARY KEY (id);


--
-- Name: radicado_asociado radicado_asociado_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.radicado_asociado
    ADD CONSTRAINT radicado_asociado_radicado_key UNIQUE (radicado);


--
-- Name: recurso_afectado recurso_afectado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_afectado
    ADD CONSTRAINT recurso_afectado_pkey PRIMARY KEY (id);


--
-- Name: solicitud_informacion solicitud_informacion_etapa_acoger_concepto_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_informacion
    ADD CONSTRAINT solicitud_informacion_etapa_acoger_concepto_id_key UNIQUE (etapa_acoger_concepto_id);


--
-- Name: solicitud_informacion solicitud_informacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_informacion
    ADD CONSTRAINT solicitud_informacion_pkey PRIMARY KEY (id);


--
-- Name: tipo_afectacion tipo_afectacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_afectacion
    ADD CONSTRAINT tipo_afectacion_pkey PRIMARY KEY (id);


--
-- Name: tipo_medida tipo_medida_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_medida
    ADD CONSTRAINT tipo_medida_pkey PRIMARY KEY (id);


--
-- Name: tipo_notificacion tipo_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_notificacion
    ADD CONSTRAINT tipo_notificacion_pkey PRIMARY KEY (id);


--
-- Name: expediente_involucrado uq_exp_inv; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT uq_exp_inv UNIQUE (expediente_id, involucrado_id);


--
-- Name: informe_recurso_afectado uq_informe_recurso; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_recurso_afectado
    ADD CONSTRAINT uq_informe_recurso UNIQUE (informe_id, recurso);


--
-- Name: vereda vereda_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_pkey PRIMARY KEY (id);


--
-- Name: ix_acto_admin_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acto_admin_fecha_creacion ON public.acto_administrativo USING btree (fecha_creacion);


--
-- Name: ix_etapa_acoger_concepto_expediente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_acoger_concepto_expediente ON public.etapa_acoger_concepto USING btree (expediente_id);


--
-- Name: ix_etapa_cierre_expediente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_cierre_expediente ON public.etapa_cierre USING btree (expediente_id);


--
-- Name: ix_etapa_respuesta_expediente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_respuesta_expediente ON public.etapa_respuesta USING btree (expediente_id);


--
-- Name: ix_etapa_respuesta_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_respuesta_fecha ON public.etapa_respuesta USING btree (fecha_radicado);


--
-- Name: ix_expediente_abogado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_abogado ON public.expediente USING btree (abogado_responsable_id);


--
-- Name: ix_expediente_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_fecha_creacion ON public.expediente USING btree (fecha_creacion);


--
-- Name: ix_informe_proceso_auditoria_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_auditoria_proceso_id ON public.informe_proceso_auditoria USING btree (proceso_id);


--
-- Name: ix_informe_proceso_creador_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_creador_id ON public.informe_proceso USING btree (creador_id);


--
-- Name: ix_informe_proceso_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_estado ON public.informe_proceso USING btree (estado);


--
-- Name: ix_informe_proceso_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_fecha_creacion ON public.informe_proceso USING btree (fecha_creacion);


--
-- Name: ix_informe_proceso_informe_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_informe_id ON public.informe_proceso USING btree (informe_id);


--
-- Name: ix_informe_proceso_revision_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_revision_proceso_id ON public.informe_proceso_revision USING btree (proceso_id);


--
-- Name: ix_informe_proceso_revision_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_revision_revisor_id ON public.informe_proceso_revision USING btree (revisor_id);


--
-- Name: ix_informe_proceso_revisor_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_revisor_proceso_id ON public.informe_proceso_revisor USING btree (proceso_id);


--
-- Name: ix_informe_proceso_revisor_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_revisor_revisor_id ON public.informe_proceso_revisor USING btree (revisor_id);


--
-- Name: ix_informe_proceso_version_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_version_file_id ON public.informe_proceso_version USING btree (file_id);


--
-- Name: ix_informe_proceso_version_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_proceso_version_proceso_id ON public.informe_proceso_version USING btree (proceso_id);


--
-- Name: ix_informe_recurso_afectado_informe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_recurso_afectado_informe ON public.informe_recurso_afectado USING btree (informe_id);


--
-- Name: ix_informe_tecnico_expediente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_tecnico_expediente ON public.informe_tecnico USING btree (expediente_id);


--
-- Name: ix_informe_tecnico_profesional; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_informe_tecnico_profesional ON public.informe_tecnico USING btree (profesional_asignado_id);


--
-- Name: ix_notificacion_acto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_acto ON public.notificacion USING btree (acto_administrativo_id);


--
-- Name: ix_notificacion_fecha_notificacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_fecha_notificacion ON public.notificacion USING btree (fecha_notificacion);


--
-- Name: ix_radicado_asociado_expediente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_radicado_asociado_expediente ON public.radicado_asociado USING btree (expediente_id);


--
-- Name: uq_informe_proceso_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_informe_proceso_activo ON public.informe_proceso USING btree (informe_id) WHERE activo;


--
-- Name: auditoria auditoria_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: comunicacion comunicacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion
    ADD CONSTRAINT comunicacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id);


--
-- Name: etapa_acoger_concepto etapa_acoger_concepto_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_acoger_concepto
    ADD CONSTRAINT etapa_acoger_concepto_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: etapa_acoger_concepto etapa_acoger_concepto_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_acoger_concepto
    ADD CONSTRAINT etapa_acoger_concepto_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: etapa_cierre etapa_cierre_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre
    ADD CONSTRAINT etapa_cierre_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: etapa_cierre etapa_cierre_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre
    ADD CONSTRAINT etapa_cierre_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: etapa_respuesta etapa_respuesta_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_respuesta
    ADD CONSTRAINT etapa_respuesta_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_involucrado expediente_involucrado_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_recurso expediente_recurso_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT expediente_recurso_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_recurso expediente_recurso_recurso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT expediente_recurso_recurso_id_fkey FOREIGN KEY (recurso_id) REFERENCES public.recurso_afectado(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_tipo_afectacion expediente_tipo_afectacion_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_tipo_afectacion
    ADD CONSTRAINT expediente_tipo_afectacion_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_tipo_afectacion expediente_tipo_afectacion_tipo_afectacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_tipo_afectacion
    ADD CONSTRAINT expediente_tipo_afectacion_tipo_afectacion_id_fkey FOREIGN KEY (tipo_afectacion_id) REFERENCES public.tipo_afectacion(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente expediente_vereda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_vereda_id_fkey FOREIGN KEY (vereda_id) REFERENCES public.vereda(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: informe_proceso_auditoria informe_proceso_auditoria_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_auditoria
    ADD CONSTRAINT informe_proceso_auditoria_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.informe_proceso(id) ON DELETE CASCADE;


--
-- Name: informe_proceso informe_proceso_informe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso
    ADD CONSTRAINT informe_proceso_informe_id_fkey FOREIGN KEY (informe_id) REFERENCES public.informe_tecnico(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: informe_proceso_revision informe_proceso_revision_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revision
    ADD CONSTRAINT informe_proceso_revision_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.informe_proceso(id) ON DELETE CASCADE;


--
-- Name: informe_proceso_revisor informe_proceso_revisor_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_revisor
    ADD CONSTRAINT informe_proceso_revisor_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.informe_proceso(id) ON DELETE CASCADE;


--
-- Name: informe_proceso_version informe_proceso_version_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_proceso_version
    ADD CONSTRAINT informe_proceso_version_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.informe_proceso(id) ON DELETE CASCADE;


--
-- Name: informe_recurso_afectado informe_recurso_afectado_informe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_recurso_afectado
    ADD CONSTRAINT informe_recurso_afectado_informe_id_fkey FOREIGN KEY (informe_id) REFERENCES public.informe_tecnico(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: informe_tecnico informe_tecnico_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_tecnico
    ADD CONSTRAINT informe_tecnico_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: medida_preventiva medida_preventiva_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: medida_preventiva medida_preventiva_etapa_respuesta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_etapa_respuesta_id_fkey FOREIGN KEY (etapa_respuesta_id) REFERENCES public.etapa_respuesta(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: medida_preventiva medida_preventiva_tipo_medida_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_tipo_medida_id_fkey FOREIGN KEY (tipo_medida_id) REFERENCES public.tipo_medida(id);


--
-- Name: notificacion notificacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: notificacion notificacion_tipo_notificacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_tipo_notificacion_id_fkey FOREIGN KEY (tipo_notificacion_id) REFERENCES public.tipo_notificacion(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: oficio_remite oficio_remite_etapa_acoger_concepto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oficio_remite
    ADD CONSTRAINT oficio_remite_etapa_acoger_concepto_id_fkey FOREIGN KEY (etapa_acoger_concepto_id) REFERENCES public.etapa_acoger_concepto(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: quejoso_expediente quejoso_expediente_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quejoso_expediente
    ADD CONSTRAINT quejoso_expediente_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: quejoso_expediente quejoso_expediente_quejoso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quejoso_expediente
    ADD CONSTRAINT quejoso_expediente_quejoso_id_fkey FOREIGN KEY (quejoso_id) REFERENCES public.quejoso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: radicado_asociado radicado_asociado_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.radicado_asociado
    ADD CONSTRAINT radicado_asociado_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: solicitud_informacion solicitud_informacion_etapa_acoger_concepto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_informacion
    ADD CONSTRAINT solicitud_informacion_etapa_acoger_concepto_id_fkey FOREIGN KEY (etapa_acoger_concepto_id) REFERENCES public.etapa_acoger_concepto(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: tipo_afectacion tipo_afectacion_recurso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_afectacion
    ADD CONSTRAINT tipo_afectacion_recurso_id_fkey FOREIGN KEY (recurso_id) REFERENCES public.recurso_afectado(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: vereda vereda_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipio(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict jspgYDdbGdTODsRsx4Q4RsCDmjBNYbpTyQttdFBD5U3bfkzFWzDkVdVEedZEWYB

