-- ============================================================
-- expedientes_db — esquema y datos iniciales de app-sancionatoria
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb expedientes_db && psql -U postgres -d expedientes_db -f expedientes_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict MZ9Qqtzq4RqfH6BuvkRgSsKc9AVK9V2Irgg8RcPci1FoydVOqQRvtRVZVpUtDPy


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
    documento_acto_administrativo_id integer,
    fecha_creacion timestamp with time zone
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
    usuario_id bigint,
    tipo_evento character varying(60) NOT NULL,
    resultado character varying(20) NOT NULL,
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
-- Name: documento_anexo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_anexo (
    id integer NOT NULL,
    etapa_tipo character varying(50) NOT NULL,
    etapa_ref_id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    documento_anexo_id integer NOT NULL,
    fecha_subida timestamp with time zone NOT NULL
);


--
-- Name: documento_anexo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_anexo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_anexo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_anexo_id_seq OWNED BY public.documento_anexo.id;


--
-- Name: etapa_apertura_probatoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_apertura_probatoria (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: etapa_apertura_probatoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_apertura_probatoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_apertura_probatoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_apertura_probatoria_id_seq OWNED BY public.etapa_apertura_probatoria.id;


--
-- Name: etapa_cesacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_cesacion (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone,
    tipo_cesacion_id integer
);


--
-- Name: etapa_cesacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_cesacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_cesacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_cesacion_id_seq OWNED BY public.etapa_cesacion.id;


--
-- Name: etapa_cierre_probatoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_cierre_probatoria (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: etapa_cierre_probatoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_cierre_probatoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_cierre_probatoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_cierre_probatoria_id_seq OWNED BY public.etapa_cierre_probatoria.id;


--
-- Name: etapa_decision_fondo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_decision_fondo (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    acto_recurso_id integer,
    fecha_creacion timestamp with time zone,
    tipo_sancion_id integer,
    detalle text
);


--
-- Name: etapa_decision_fondo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_decision_fondo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_decision_fondo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_decision_fondo_id_seq OWNED BY public.etapa_decision_fondo.id;


--
-- Name: etapa_ejecucion_sancion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_ejecucion_sancion (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    fecha_creacion timestamp with time zone,
    tipo_acto character varying(15),
    fecha_auto date,
    documento_acto_administrativo_id integer,
    cobro_coactivo boolean,
    documento_cobro_id integer,
    disposicion boolean,
    ruia boolean,
    documento_ruia_id integer,
    memorando boolean,
    documento_memorando_id integer
);


--
-- Name: etapa_ejecucion_sancion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_ejecucion_sancion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_ejecucion_sancion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_ejecucion_sancion_id_seq OWNED BY public.etapa_ejecucion_sancion.id;


--
-- Name: etapa_formulacion_cargos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_formulacion_cargos (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone,
    descargos boolean,
    documento_id integer
);


--
-- Name: etapa_formulacion_cargos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_formulacion_cargos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_formulacion_cargos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_formulacion_cargos_id_seq OWNED BY public.etapa_formulacion_cargos.id;


--
-- Name: etapa_indagacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_indagacion (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: etapa_indagacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_indagacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_indagacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_indagacion_id_seq OWNED BY public.etapa_indagacion.id;


--
-- Name: etapa_inicio_sancionatorio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_inicio_sancionatorio (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: etapa_inicio_sancionatorio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_inicio_sancionatorio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_inicio_sancionatorio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_inicio_sancionatorio_id_seq OWNED BY public.etapa_inicio_sancionatorio.id;


--
-- Name: etapa_medida_preventiva; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_medida_preventiva (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    fecha_creacion timestamp with time zone,
    tipo_medida_id integer,
    cantidad text,
    especie text,
    estado_medida boolean
);


--
-- Name: etapa_medida_preventiva_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_medida_preventiva_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_medida_preventiva_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_medida_preventiva_id_seq OWNED BY public.etapa_medida_preventiva.id;


--
-- Name: etapa_probatoria_recurso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.etapa_probatoria_recurso (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    acto_administrativo_id integer,
    acto_decision_id integer,
    fecha_creacion timestamp with time zone
);


--
-- Name: etapa_probatoria_recurso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.etapa_probatoria_recurso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: etapa_probatoria_recurso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.etapa_probatoria_recurso_id_seq OWNED BY public.etapa_probatoria_recurso.id;


--
-- Name: expediente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente (
    id integer NOT NULL,
    radicado character varying(15),
    expediente character varying(7),
    motivo_afectacion character varying(200),
    fecha_creacion timestamp with time zone NOT NULL,
    encargado_id integer,
    direccion character varying(100),
    vereda_id integer,
    archivado boolean,
    fecha_archivado timestamp with time zone
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
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    recurso_id integer NOT NULL
);


--
-- Name: expediente_recurso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expediente_recurso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expediente_recurso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expediente_recurso_id_seq OWNED BY public.expediente_recurso.id;


--
-- Name: municipio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipio (
    id integer NOT NULL,
    nombre character varying(20)
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
    acto_administrativo_id integer,
    numerado integer,
    fecha_numerado date,
    involucrado_id integer,
    fecha_envio_citacion date,
    fecha_constancia_citacion date,
    documento_citacion_id integer,
    notificacion_exitosa boolean,
    fecha_notificacion date,
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
-- Name: tipo_cesacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_cesacion (
    id integer NOT NULL,
    nombre text
);


--
-- Name: tipo_cesacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_cesacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_cesacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_cesacion_id_seq OWNED BY public.tipo_cesacion.id;


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
    nombre character varying(15)
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
-- Name: tipo_sancion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_sancion (
    id integer NOT NULL,
    nombre text
);


--
-- Name: tipo_sancion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_sancion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_sancion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_sancion_id_seq OWNED BY public.tipo_sancion.id;


--
-- Name: vereda; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vereda (
    id integer NOT NULL,
    nombre character varying(25),
    municipio_id integer
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
-- Name: documento_anexo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_anexo ALTER COLUMN id SET DEFAULT nextval('public.documento_anexo_id_seq'::regclass);


--
-- Name: etapa_apertura_probatoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_apertura_probatoria ALTER COLUMN id SET DEFAULT nextval('public.etapa_apertura_probatoria_id_seq'::regclass);


--
-- Name: etapa_cesacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion ALTER COLUMN id SET DEFAULT nextval('public.etapa_cesacion_id_seq'::regclass);


--
-- Name: etapa_cierre_probatoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre_probatoria ALTER COLUMN id SET DEFAULT nextval('public.etapa_cierre_probatoria_id_seq'::regclass);


--
-- Name: etapa_decision_fondo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo ALTER COLUMN id SET DEFAULT nextval('public.etapa_decision_fondo_id_seq'::regclass);


--
-- Name: etapa_ejecucion_sancion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_ejecucion_sancion ALTER COLUMN id SET DEFAULT nextval('public.etapa_ejecucion_sancion_id_seq'::regclass);


--
-- Name: etapa_formulacion_cargos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_formulacion_cargos ALTER COLUMN id SET DEFAULT nextval('public.etapa_formulacion_cargos_id_seq'::regclass);


--
-- Name: etapa_indagacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_indagacion ALTER COLUMN id SET DEFAULT nextval('public.etapa_indagacion_id_seq'::regclass);


--
-- Name: etapa_inicio_sancionatorio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_inicio_sancionatorio ALTER COLUMN id SET DEFAULT nextval('public.etapa_inicio_sancionatorio_id_seq'::regclass);


--
-- Name: etapa_medida_preventiva id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva ALTER COLUMN id SET DEFAULT nextval('public.etapa_medida_preventiva_id_seq'::regclass);


--
-- Name: etapa_probatoria_recurso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso ALTER COLUMN id SET DEFAULT nextval('public.etapa_probatoria_recurso_id_seq'::regclass);


--
-- Name: expediente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente ALTER COLUMN id SET DEFAULT nextval('public.expediente_id_seq'::regclass);


--
-- Name: expediente_involucrado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado ALTER COLUMN id SET DEFAULT nextval('public.expediente_involucrado_id_seq'::regclass);


--
-- Name: expediente_recurso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_recurso ALTER COLUMN id SET DEFAULT nextval('public.expediente_recurso_id_seq'::regclass);


--
-- Name: municipio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio ALTER COLUMN id SET DEFAULT nextval('public.municipio_id_seq'::regclass);


--
-- Name: notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- Name: recurso_afectado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_afectado ALTER COLUMN id SET DEFAULT nextval('public.recurso_afectado_id_seq'::regclass);


--
-- Name: tipo_cesacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_cesacion ALTER COLUMN id SET DEFAULT nextval('public.tipo_cesacion_id_seq'::regclass);


--
-- Name: tipo_medida id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_medida ALTER COLUMN id SET DEFAULT nextval('public.tipo_medida_id_seq'::regclass);


--
-- Name: tipo_notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_notificacion ALTER COLUMN id SET DEFAULT nextval('public.tipo_notificacion_id_seq'::regclass);


--
-- Name: tipo_sancion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_sancion ALTER COLUMN id SET DEFAULT nextval('public.tipo_sancion_id_seq'::regclass);


--
-- Name: vereda id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda ALTER COLUMN id SET DEFAULT nextval('public.vereda_id_seq'::regclass);


--
-- Data for Name: acto_administrativo; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.acto_administrativo (id, tipo_acto, numerado, fecha_numerado, documento_acto_administrativo_id, fecha_creacion) FROM stdin;
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
-- Data for Name: documento_anexo; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_anexo (id, etapa_tipo, etapa_ref_id, nombre, documento_anexo_id, fecha_subida) FROM stdin;
\.


--
-- Data for Name: etapa_apertura_probatoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_apertura_probatoria (id, expediente_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_cesacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_cesacion (id, expediente_id, acto_administrativo_id, fecha_creacion, tipo_cesacion_id) FROM stdin;
\.


--
-- Data for Name: etapa_cierre_probatoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_cierre_probatoria (id, expediente_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_decision_fondo; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_decision_fondo (id, expediente_id, acto_administrativo_id, acto_recurso_id, fecha_creacion, tipo_sancion_id, detalle) FROM stdin;
\.


--
-- Data for Name: etapa_ejecucion_sancion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_ejecucion_sancion (id, expediente_id, fecha_creacion, tipo_acto, fecha_auto, documento_acto_administrativo_id, cobro_coactivo, documento_cobro_id, disposicion, ruia, documento_ruia_id, memorando, documento_memorando_id) FROM stdin;
\.


--
-- Data for Name: etapa_formulacion_cargos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_formulacion_cargos (id, expediente_id, acto_administrativo_id, fecha_creacion, descargos, documento_id) FROM stdin;
\.


--
-- Data for Name: etapa_indagacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_indagacion (id, expediente_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_inicio_sancionatorio; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_inicio_sancionatorio (id, expediente_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: etapa_medida_preventiva; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_medida_preventiva (id, expediente_id, acto_administrativo_id, fecha_creacion, tipo_medida_id, cantidad, especie, estado_medida) FROM stdin;
\.


--
-- Data for Name: etapa_probatoria_recurso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.etapa_probatoria_recurso (id, expediente_id, acto_administrativo_id, acto_decision_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: expediente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente (id, radicado, expediente, motivo_afectacion, fecha_creacion, encargado_id, direccion, vereda_id, archivado, fecha_archivado) FROM stdin;
\.


--
-- Data for Name: expediente_involucrado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_involucrado (id, expediente_id, involucrado_id) FROM stdin;
\.


--
-- Data for Name: expediente_recurso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_recurso (id, expediente_id, recurso_id) FROM stdin;
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
-- Data for Name: recurso_afectado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.recurso_afectado (id, nombre) FROM stdin;
1	Agua
2	Aire
3	Bosque
4	Fauna
5	Flora
6	Suelo
7	Ruido
8	Social
\.


--
-- Data for Name: tipo_cesacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_cesacion (id, nombre) FROM stdin;
1	Muerte del investigado cuando es una persona natural o liquidación definitiva de la persona jurídica, en el segundo caso procederá lo contenido en el artículo 9A de la presente Ley.
2	Que el hecho investigado no sea constitutivo de infracción ambiental.
3	Que la conducta investigada no sea imputable al presunto infractor.
4	Que la actividad esté legalmente amparada y/o autorizada.
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
6	Aprehensión preventiva
7	Congelación o suspensión de venta-empleo
8	Amonestación escrita
9	Elaboración de estudios ambientales
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
-- Data for Name: tipo_sancion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_sancion (id, nombre) FROM stdin;
1	Amonestación escrita
2	Cierre temporal o definitivo
3	Revocatoria o caducidad de licencia ambiental, autorización, concesión, permiso o registro
4	Demolición de obra a costa del infractor
5	Decomiso preventivo de especímenes, especies silvestres
6	Restitución de especímenes de flora y fauna silvestres o acuática
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
-- Name: documento_anexo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_anexo_id_seq', 1, false);


--
-- Name: etapa_apertura_probatoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_apertura_probatoria_id_seq', 1, false);


--
-- Name: etapa_cesacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_cesacion_id_seq', 1, false);


--
-- Name: etapa_cierre_probatoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_cierre_probatoria_id_seq', 1, false);


--
-- Name: etapa_decision_fondo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_decision_fondo_id_seq', 1, false);


--
-- Name: etapa_ejecucion_sancion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_ejecucion_sancion_id_seq', 1, false);


--
-- Name: etapa_formulacion_cargos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_formulacion_cargos_id_seq', 1, false);


--
-- Name: etapa_indagacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_indagacion_id_seq', 1, false);


--
-- Name: etapa_inicio_sancionatorio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_inicio_sancionatorio_id_seq', 1, false);


--
-- Name: etapa_medida_preventiva_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_medida_preventiva_id_seq', 1, false);


--
-- Name: etapa_probatoria_recurso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.etapa_probatoria_recurso_id_seq', 1, false);


--
-- Name: expediente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_id_seq', 1, false);


--
-- Name: expediente_involucrado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_involucrado_id_seq', 1, false);


--
-- Name: expediente_recurso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_recurso_id_seq', 1, false);


--
-- Name: municipio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.municipio_id_seq', 1, false);


--
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 1, false);


--
-- Name: recurso_afectado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.recurso_afectado_id_seq', 1, false);


--
-- Name: tipo_cesacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_cesacion_id_seq', 1, false);


--
-- Name: tipo_medida_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_medida_id_seq', 1, false);


--
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_notificacion_id_seq', 1, false);


--
-- Name: tipo_sancion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_sancion_id_seq', 1, false);


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
-- Name: documento_anexo documento_anexo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_anexo
    ADD CONSTRAINT documento_anexo_pkey PRIMARY KEY (id);


--
-- Name: etapa_apertura_probatoria etapa_apertura_probatoria_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_apertura_probatoria
    ADD CONSTRAINT etapa_apertura_probatoria_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_apertura_probatoria etapa_apertura_probatoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_apertura_probatoria
    ADD CONSTRAINT etapa_apertura_probatoria_pkey PRIMARY KEY (id);


--
-- Name: etapa_cesacion etapa_cesacion_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion
    ADD CONSTRAINT etapa_cesacion_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_cesacion etapa_cesacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion
    ADD CONSTRAINT etapa_cesacion_pkey PRIMARY KEY (id);


--
-- Name: etapa_cierre_probatoria etapa_cierre_probatoria_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre_probatoria
    ADD CONSTRAINT etapa_cierre_probatoria_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_cierre_probatoria etapa_cierre_probatoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre_probatoria
    ADD CONSTRAINT etapa_cierre_probatoria_pkey PRIMARY KEY (id);


--
-- Name: etapa_decision_fondo etapa_decision_fondo_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_decision_fondo etapa_decision_fondo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_pkey PRIMARY KEY (id);


--
-- Name: etapa_ejecucion_sancion etapa_ejecucion_sancion_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_ejecucion_sancion
    ADD CONSTRAINT etapa_ejecucion_sancion_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_ejecucion_sancion etapa_ejecucion_sancion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_ejecucion_sancion
    ADD CONSTRAINT etapa_ejecucion_sancion_pkey PRIMARY KEY (id);


--
-- Name: etapa_formulacion_cargos etapa_formulacion_cargos_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_formulacion_cargos
    ADD CONSTRAINT etapa_formulacion_cargos_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_formulacion_cargos etapa_formulacion_cargos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_formulacion_cargos
    ADD CONSTRAINT etapa_formulacion_cargos_pkey PRIMARY KEY (id);


--
-- Name: etapa_indagacion etapa_indagacion_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_indagacion
    ADD CONSTRAINT etapa_indagacion_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_indagacion etapa_indagacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_indagacion
    ADD CONSTRAINT etapa_indagacion_pkey PRIMARY KEY (id);


--
-- Name: etapa_inicio_sancionatorio etapa_inicio_sancionatorio_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_inicio_sancionatorio
    ADD CONSTRAINT etapa_inicio_sancionatorio_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_inicio_sancionatorio etapa_inicio_sancionatorio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_inicio_sancionatorio
    ADD CONSTRAINT etapa_inicio_sancionatorio_pkey PRIMARY KEY (id);


--
-- Name: etapa_medida_preventiva etapa_medida_preventiva_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva
    ADD CONSTRAINT etapa_medida_preventiva_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_medida_preventiva etapa_medida_preventiva_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva
    ADD CONSTRAINT etapa_medida_preventiva_pkey PRIMARY KEY (id);


--
-- Name: etapa_probatoria_recurso etapa_probatoria_recurso_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso
    ADD CONSTRAINT etapa_probatoria_recurso_expediente_id_key UNIQUE (expediente_id);


--
-- Name: etapa_probatoria_recurso etapa_probatoria_recurso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso
    ADD CONSTRAINT etapa_probatoria_recurso_pkey PRIMARY KEY (id);


--
-- Name: expediente expediente_expediente_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_expediente_key UNIQUE (expediente);


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
    ADD CONSTRAINT expediente_recurso_pkey PRIMARY KEY (id);


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
-- Name: recurso_afectado recurso_afectado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_afectado
    ADD CONSTRAINT recurso_afectado_pkey PRIMARY KEY (id);


--
-- Name: tipo_cesacion tipo_cesacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_cesacion
    ADD CONSTRAINT tipo_cesacion_pkey PRIMARY KEY (id);


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
-- Name: tipo_sancion tipo_sancion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_sancion
    ADD CONSTRAINT tipo_sancion_pkey PRIMARY KEY (id);


--
-- Name: expediente_involucrado uq_exp_inv; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT uq_exp_inv UNIQUE (expediente_id, involucrado_id);


--
-- Name: expediente_recurso uq_exp_rec; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT uq_exp_rec UNIQUE (expediente_id, recurso_id);


--
-- Name: vereda vereda_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_pkey PRIMARY KEY (id);


--
-- Name: ix_auditoria_expediente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_expediente_id ON public.auditoria USING btree (expediente_id);


--
-- Name: ix_auditoria_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_fecha ON public.auditoria USING btree (fecha);


--
-- Name: ix_auditoria_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_usuario_id ON public.auditoria USING btree (usuario_id);


--
-- Name: ix_documento_anexo_etapa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_anexo_etapa ON public.documento_anexo USING btree (etapa_tipo, etapa_ref_id);


--
-- Name: ix_etapa_apertura_probatoria_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_apertura_probatoria_acto_administrativo_id ON public.etapa_apertura_probatoria USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_cesacion_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_cesacion_acto_administrativo_id ON public.etapa_cesacion USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_cierre_probatoria_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_cierre_probatoria_acto_administrativo_id ON public.etapa_cierre_probatoria USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_decision_fondo_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_decision_fondo_acto_administrativo_id ON public.etapa_decision_fondo USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_decision_fondo_acto_recurso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_decision_fondo_acto_recurso_id ON public.etapa_decision_fondo USING btree (acto_recurso_id);


--
-- Name: ix_etapa_formulacion_cargos_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_formulacion_cargos_acto_administrativo_id ON public.etapa_formulacion_cargos USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_indagacion_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_indagacion_acto_administrativo_id ON public.etapa_indagacion USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_inicio_sancionatorio_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_inicio_sancionatorio_acto_administrativo_id ON public.etapa_inicio_sancionatorio USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_medida_preventiva_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_medida_preventiva_acto_administrativo_id ON public.etapa_medida_preventiva USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_probatoria_recurso_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_probatoria_recurso_acto_administrativo_id ON public.etapa_probatoria_recurso USING btree (acto_administrativo_id);


--
-- Name: ix_etapa_probatoria_recurso_acto_decision_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_etapa_probatoria_recurso_acto_decision_id ON public.etapa_probatoria_recurso USING btree (acto_decision_id);


--
-- Name: ix_expediente_archivado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_archivado ON public.expediente USING btree (archivado);


--
-- Name: ix_expediente_encargado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_encargado_fecha ON public.expediente USING btree (encargado_id, fecha_creacion);


--
-- Name: ix_expediente_encargado_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_encargado_id ON public.expediente USING btree (encargado_id);


--
-- Name: ix_expediente_involucrado_involucrado_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_involucrado_involucrado_id ON public.expediente_involucrado USING btree (involucrado_id);


--
-- Name: ix_expediente_recurso_recurso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_recurso_recurso_id ON public.expediente_recurso USING btree (recurso_id);


--
-- Name: ix_expediente_vereda_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_vereda_id ON public.expediente USING btree (vereda_id);


--
-- Name: ix_notificacion_acto_administrativo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_acto_administrativo_id ON public.notificacion USING btree (acto_administrativo_id);


--
-- Name: ix_notificacion_acto_exitosa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_acto_exitosa ON public.notificacion USING btree (acto_administrativo_id, notificacion_exitosa);


--
-- Name: ix_notificacion_involucrado_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_involucrado_id ON public.notificacion USING btree (involucrado_id);


--
-- Name: ix_vereda_municipio_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vereda_municipio_id ON public.vereda USING btree (municipio_id);


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
-- Name: etapa_apertura_probatoria etapa_apertura_probatoria_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_apertura_probatoria
    ADD CONSTRAINT etapa_apertura_probatoria_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_apertura_probatoria etapa_apertura_probatoria_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_apertura_probatoria
    ADD CONSTRAINT etapa_apertura_probatoria_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_cesacion etapa_cesacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion
    ADD CONSTRAINT etapa_cesacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_cesacion etapa_cesacion_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion
    ADD CONSTRAINT etapa_cesacion_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_cesacion etapa_cesacion_tipo_cesacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cesacion
    ADD CONSTRAINT etapa_cesacion_tipo_cesacion_id_fkey FOREIGN KEY (tipo_cesacion_id) REFERENCES public.tipo_cesacion(id);


--
-- Name: etapa_cierre_probatoria etapa_cierre_probatoria_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre_probatoria
    ADD CONSTRAINT etapa_cierre_probatoria_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_cierre_probatoria etapa_cierre_probatoria_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_cierre_probatoria
    ADD CONSTRAINT etapa_cierre_probatoria_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_decision_fondo etapa_decision_fondo_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_decision_fondo etapa_decision_fondo_acto_recurso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_acto_recurso_id_fkey FOREIGN KEY (acto_recurso_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_decision_fondo etapa_decision_fondo_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_decision_fondo etapa_decision_fondo_tipo_sancion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_decision_fondo
    ADD CONSTRAINT etapa_decision_fondo_tipo_sancion_id_fkey FOREIGN KEY (tipo_sancion_id) REFERENCES public.tipo_sancion(id);


--
-- Name: etapa_ejecucion_sancion etapa_ejecucion_sancion_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_ejecucion_sancion
    ADD CONSTRAINT etapa_ejecucion_sancion_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_formulacion_cargos etapa_formulacion_cargos_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_formulacion_cargos
    ADD CONSTRAINT etapa_formulacion_cargos_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_formulacion_cargos etapa_formulacion_cargos_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_formulacion_cargos
    ADD CONSTRAINT etapa_formulacion_cargos_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_indagacion etapa_indagacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_indagacion
    ADD CONSTRAINT etapa_indagacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_indagacion etapa_indagacion_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_indagacion
    ADD CONSTRAINT etapa_indagacion_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_inicio_sancionatorio etapa_inicio_sancionatorio_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_inicio_sancionatorio
    ADD CONSTRAINT etapa_inicio_sancionatorio_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_inicio_sancionatorio etapa_inicio_sancionatorio_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_inicio_sancionatorio
    ADD CONSTRAINT etapa_inicio_sancionatorio_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_medida_preventiva etapa_medida_preventiva_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva
    ADD CONSTRAINT etapa_medida_preventiva_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_medida_preventiva etapa_medida_preventiva_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva
    ADD CONSTRAINT etapa_medida_preventiva_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


--
-- Name: etapa_medida_preventiva etapa_medida_preventiva_tipo_medida_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_medida_preventiva
    ADD CONSTRAINT etapa_medida_preventiva_tipo_medida_id_fkey FOREIGN KEY (tipo_medida_id) REFERENCES public.tipo_medida(id);


--
-- Name: etapa_probatoria_recurso etapa_probatoria_recurso_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso
    ADD CONSTRAINT etapa_probatoria_recurso_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_probatoria_recurso etapa_probatoria_recurso_acto_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso
    ADD CONSTRAINT etapa_probatoria_recurso_acto_decision_id_fkey FOREIGN KEY (acto_decision_id) REFERENCES public.acto_administrativo(id) ON DELETE SET NULL;


--
-- Name: etapa_probatoria_recurso etapa_probatoria_recurso_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.etapa_probatoria_recurso
    ADD CONSTRAINT etapa_probatoria_recurso_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT expediente_recurso_recurso_id_fkey FOREIGN KEY (recurso_id) REFERENCES public.recurso_afectado(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: expediente expediente_vereda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_vereda_id_fkey FOREIGN KEY (vereda_id) REFERENCES public.vereda(id) ON UPDATE CASCADE;


--
-- Name: notificacion notificacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: notificacion notificacion_tipo_notificacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_tipo_notificacion_id_fkey FOREIGN KEY (tipo_notificacion_id) REFERENCES public.tipo_notificacion(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: vereda vereda_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipio(id) ON UPDATE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict MZ9Qqtzq4RqfH6BuvkRgSsKc9AVK9V2Irgg8RcPci1FoydVOqQRvtRVZVpUtDPy

