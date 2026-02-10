--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2025-10-08 04:28:21

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- TOC entry 239 (class 1259 OID 16910)
-- Name: codigos_recuperacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.codigos_recuperacion (
    correo character varying(255) NOT NULL,
    codigo character varying(100) NOT NULL,
    expiracion timestamp without time zone NOT NULL
);


ALTER TABLE public.codigos_recuperacion OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16752)
-- Name: decision_fondo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.decision_fondo (
    id integer NOT NULL,
    tipo_sancion_id integer,
    detalle text,
    etapa_id integer
);


ALTER TABLE public.decision_fondo OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 49891)
-- Name: decision_fondo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.decision_fondo ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.decision_fondo_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 228 (class 1259 OID 16773)
-- Name: ejecucion_sancion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ejecucion_sancion (
    id integer NOT NULL,
    cobro_coactivo boolean,
    disposicion boolean,
    ruia boolean,
    etapa_id integer,
    act_admin text,
    fecha_act date
);


ALTER TABLE public.ejecucion_sancion OWNER TO postgres;

--
-- TOC entry 263 (class 1259 OID 49908)
-- Name: ejecucion_sancion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.ejecucion_sancion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ejecucion_sancion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 16676)
-- Name: etapa; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.etapa (
    id integer NOT NULL,
    expediente_radicado text,
    tipo_etapa_id integer,
    fecha_inicio timestamp without time zone,
    fecha_fin date
);


ALTER TABLE public.etapa OWNER TO postgres;

--
-- TOC entry 252 (class 1259 OID 49840)
-- Name: etapa_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.etapa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.etapa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 219 (class 1259 OID 16655)
-- Name: expediente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expediente (
    radicado text NOT NULL,
    nombre_expediente text,
    motivo_afectacion text,
    fecha_creacion date NOT NULL,
    encargado_id bigint,
    direccion text,
    vereda_id integer
);


ALTER TABLE public.expediente OWNER TO postgres;

--
-- TOC entry 250 (class 1259 OID 33450)
-- Name: expediente_recurso; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expediente_recurso (
    expediente_radicado text NOT NULL,
    recurso_id integer NOT NULL
);


ALTER TABLE public.expediente_recurso OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16733)
-- Name: formulacion_cargos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.formulacion_cargos (
    id integer NOT NULL,
    descargos boolean,
    etapa_id integer
);


ALTER TABLE public.formulacion_cargos OWNER TO postgres;

--
-- TOC entry 260 (class 1259 OID 49890)
-- Name: formulacion_cargos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.formulacion_cargos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.formulacion_cargos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 231 (class 1259 OID 16809)
-- Name: involucrado; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.involucrado (
    id integer NOT NULL,
    numero_documento bigint,
    tipo_documento text,
    nombre text,
    celular bigint,
    correo text
);


ALTER TABLE public.involucrado OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 16816)
-- Name: involucrado_expediente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.involucrado_expediente (
    involucrado_id integer NOT NULL,
    expediente_radicado text NOT NULL
);


ALTER TABLE public.involucrado_expediente OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 49819)
-- Name: involucrado_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.involucrado ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.involucrado_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 233 (class 1259 OID 16833)
-- Name: involucrado_notificacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.involucrado_notificacion (
    id integer NOT NULL,
    proceso_notificacion_id integer,
    involucrado_id integer,
    numero_envio text,
    fecha_envio date,
    fecha_constancia date,
    notificacion_exitosa boolean
);


ALTER TABLE public.involucrado_notificacion OWNER TO postgres;

--
-- TOC entry 255 (class 1259 OID 49851)
-- Name: involucrado_notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.involucrado_notificacion ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.involucrado_notificacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 224 (class 1259 OID 16719)
-- Name: ley_1333_2009; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ley_1333_2009 (
    id integer NOT NULL,
    tipo_cesacion_id integer,
    etapa_id integer
);


ALTER TABLE public.ley_1333_2009 OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 49878)
-- Name: ley_1333_2009_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.ley_1333_2009 ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ley_1333_2009_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 238 (class 1259 OID 16889)
-- Name: log_auditoria; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.log_auditoria (
    id integer NOT NULL,
    expediente_radicado text,
    tabla_afectada text NOT NULL,
    id_registro text,
    tipo_operacion text NOT NULL,
    usuario_id bigint,
    fecha timestamp without time zone DEFAULT now(),
    descripcion text,
    datos_anteriores jsonb,
    datos_nuevos jsonb
);


ALTER TABLE public.log_auditoria OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 16888)
-- Name: log_auditoria_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.log_auditoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.log_auditoria_id_seq OWNER TO postgres;

--
-- TOC entry 5180 (class 0 OID 0)
-- Dependencies: 237
-- Name: log_auditoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.log_auditoria_id_seq OWNED BY public.log_auditoria.id;


--
-- TOC entry 223 (class 1259 OID 16700)
-- Name: medida_preventiva; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.medida_preventiva (
    id integer NOT NULL,
    id_tipo integer,
    cantidad text,
    especie text,
    estado_medida boolean,
    etapa_id integer
);


ALTER TABLE public.medida_preventiva OWNER TO postgres;

--
-- TOC entry 257 (class 1259 OID 49860)
-- Name: medida_preventiva_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.medida_preventiva ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.medida_preventiva_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 217 (class 1259 OID 16636)
-- Name: municipio; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.municipio (
    id integer NOT NULL,
    nombre text
);


ALTER TABLE public.municipio OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 33422)
-- Name: municipio_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.municipio ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.municipio_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 244 (class 1259 OID 17039)
-- Name: notificacion_usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notificacion_usuario (
    id integer NOT NULL,
    mensaje text NOT NULL,
    expediente_radicado text NOT NULL,
    numero_documento bigint NOT NULL
);


ALTER TABLE public.notificacion_usuario OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 17038)
-- Name: notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notificacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notificacion_id_seq OWNER TO postgres;

--
-- TOC entry 5181 (class 0 OID 0)
-- Dependencies: 243
-- Name: notificacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notificacion_id_seq OWNED BY public.notificacion_usuario.id;


--
-- TOC entry 236 (class 1259 OID 16863)
-- Name: permiso; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permiso (
    id integer NOT NULL,
    nombre text NOT NULL,
    menu_path text
);


ALTER TABLE public.permiso OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16862)
-- Name: permiso_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permiso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.permiso_id_seq OWNER TO postgres;

--
-- TOC entry 5182 (class 0 OID 0)
-- Dependencies: 235
-- Name: permiso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permiso_id_seq OWNED BY public.permiso.id;


--
-- TOC entry 230 (class 1259 OID 16794)
-- Name: proceso_notificacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proceso_notificacion (
    id integer NOT NULL,
    fecha_creacion date,
    etapa_id integer,
    tipo_id integer,
    nombre text
);


ALTER TABLE public.proceso_notificacion OWNER TO postgres;

--
-- TOC entry 254 (class 1259 OID 49842)
-- Name: proceso_notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.proceso_notificacion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.proceso_notificacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 249 (class 1259 OID 33426)
-- Name: recurso_afectado; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.recurso_afectado (
    id integer NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.recurso_afectado OWNER TO postgres;

--
-- TOC entry 248 (class 1259 OID 33425)
-- Name: recurso_afectado_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.recurso_afectado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.recurso_afectado_id_seq OWNER TO postgres;

--
-- TOC entry 5183 (class 0 OID 0)
-- Dependencies: 248
-- Name: recurso_afectado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.recurso_afectado_id_seq OWNED BY public.recurso_afectado.id;


--
-- TOC entry 241 (class 1259 OID 16995)
-- Name: rol; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rol (
    id integer NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.rol OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 16994)
-- Name: rol_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.rol_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rol_id_seq OWNER TO postgres;

--
-- TOC entry 5184 (class 0 OID 0)
-- Dependencies: 240
-- Name: rol_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.rol_id_seq OWNED BY public.rol.id;


--
-- TOC entry 242 (class 1259 OID 17005)
-- Name: rol_permiso; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rol_permiso (
    rol_id integer NOT NULL,
    permiso_id integer NOT NULL
);


ALTER TABLE public.rol_permiso OWNER TO postgres;

--
-- TOC entry 258 (class 1259 OID 49861)
-- Name: tipo_cesacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tipo_cesacion (
    id integer NOT NULL,
    nombre text
);


ALTER TABLE public.tipo_cesacion OWNER TO postgres;

--
-- TOC entry 264 (class 1259 OID 49914)
-- Name: tipo_cesacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.tipo_cesacion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tipo_cesacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 220 (class 1259 OID 16667)
-- Name: tipo_etapa; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tipo_etapa (
    id integer NOT NULL,
    nombre text
);


ALTER TABLE public.tipo_etapa OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 33424)
-- Name: tipo_etapa_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.tipo_etapa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tipo_etapa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 222 (class 1259 OID 16693)
-- Name: tipo_medida; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tipo_medida (
    id integer NOT NULL,
    nombre text
);


ALTER TABLE public.tipo_medida OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 49852)
-- Name: tipo_medida_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.tipo_medida ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tipo_medida_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 229 (class 1259 OID 16785)
-- Name: tipo_notificacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tipo_notificacion (
    id integer NOT NULL,
    nombre text,
    tipo_etapa_id integer
);


ALTER TABLE public.tipo_notificacion OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 49841)
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.tipo_notificacion ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tipo_notificacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 226 (class 1259 OID 16745)
-- Name: tipo_sancion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tipo_sancion (
    id integer NOT NULL,
    nombre text
);


ALTER TABLE public.tipo_sancion OWNER TO postgres;

--
-- TOC entry 262 (class 1259 OID 49892)
-- Name: tipo_sancion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.tipo_sancion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tipo_sancion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 234 (class 1259 OID 16850)
-- Name: usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuario (
    numero_documento bigint NOT NULL,
    nombre_usuario text NOT NULL,
    correo text,
    hash_contrasena text NOT NULL,
    activo boolean DEFAULT true,
    ultimo_ingreso timestamp without time zone,
    creado_en timestamp without time zone DEFAULT now(),
    rol_id integer
);


ALTER TABLE public.usuario OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16643)
-- Name: vereda; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vereda (
    id integer NOT NULL,
    nombre text,
    municipio_id integer
);


ALTER TABLE public.vereda OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 33423)
-- Name: vereda_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.vereda ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.vereda_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 4869 (class 2604 OID 16892)
-- Name: log_auditoria id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log_auditoria ALTER COLUMN id SET DEFAULT nextval('public.log_auditoria_id_seq'::regclass);


--
-- TOC entry 4872 (class 2604 OID 17042)
-- Name: notificacion_usuario id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion_usuario ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- TOC entry 4868 (class 2604 OID 16866)
-- Name: permiso id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permiso ALTER COLUMN id SET DEFAULT nextval('public.permiso_id_seq'::regclass);


--
-- TOC entry 4873 (class 2604 OID 33429)
-- Name: recurso_afectado id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recurso_afectado ALTER COLUMN id SET DEFAULT nextval('public.recurso_afectado_id_seq'::regclass);


--
-- TOC entry 4871 (class 2604 OID 16998)
-- Name: rol id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol ALTER COLUMN id SET DEFAULT nextval('public.rol_id_seq'::regclass);


--
-- TOC entry 5149 (class 0 OID 16910)
-- Dependencies: 239
-- Data for Name: codigos_recuperacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.codigos_recuperacion (correo, codigo, expiracion) FROM stdin;
\.


--
-- TOC entry 5137 (class 0 OID 16752)
-- Dependencies: 227
-- Data for Name: decision_fondo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.decision_fondo (id, tipo_sancion_id, detalle, etapa_id) FROM stdin;
3	2	N/A	24
5	4	N/A	34
6	2	N/AA	37
\.


--
-- TOC entry 5138 (class 0 OID 16773)
-- Dependencies: 228
-- Data for Name: ejecucion_sancion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ejecucion_sancion (id, cobro_coactivo, disposicion, ruia, etapa_id, act_admin, fecha_act) FROM stdin;
1	t	f	t	25	\N	\N
2	t	t	t	29	\N	\N
3	t	t	t	38	RES1213	2025-10-09
\.


--
-- TOC entry 5131 (class 0 OID 16676)
-- Dependencies: 221
-- Data for Name: etapa; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.etapa (id, expediente_radicado, tipo_etapa_id, fecha_inicio, fecha_fin) FROM stdin;
4	Radicado 1011	2	2025-09-25 00:00:00	\N
1	CASCADE	2	2025-09-23 00:00:00	\N
5	Radicado 2	2	2025-10-02 00:00:00	\N
6	Radicado 1011	1	2025-10-03 00:00:00	\N
8	Radicado Prueba 21	2	2025-10-05 00:00:00	\N
9	Radicado Prueba	2	2025-10-05 00:00:00	\N
10	Radicado 3	2	2025-10-05 00:00:00	\N
13	Radicado Prueba 13	1	2025-10-05 13:05:34.14542	\N
14	Radicado Prueba 21	1	2025-10-05 13:10:28.626194	\N
15	Radicado 2	1	2025-10-05 13:13:28.203715	\N
16	Radicado 3	1	2025-10-05 13:32:46.213629	\N
17	CASCADE	1	2025-10-05 13:35:22.025902	\N
19	Radicado 1011	3	2025-10-05 17:35:53.775064	\N
7	Radicado 11	1	2025-10-05 00:00:00	\N
11	Radicado 11	2	2025-10-05 00:00:00	\N
20	Radicado 11	3	2025-10-05 17:51:21.736771	\N
21	Radicado 1011	4	2025-10-05 18:47:21.839118	\N
23	Radicado 1011	5	2025-10-05 20:52:34.339718	\N
24	Radicado 1011	6	2025-10-05 22:49:35.404817	\N
25	Radicado 1011	7	2025-10-06 00:02:12.171877	\N
26	Radicado 11	4	2025-10-06 00:05:52.935832	\N
27	Radicado 11	5	2025-10-06 00:07:32.880008	\N
28	Radicado 11	6	2025-10-06 00:07:39.685992	\N
29	Radicado 11	7	2025-10-06 00:07:51.8929	\N
30	Radicado Prueba 13	2	2025-10-06 10:41:31.232679	\N
31	Radicado Prueba 13	3	2025-10-06 10:54:03.020101	\N
32	Radicado Prueba 13	4	2025-10-06 11:13:56.88245	\N
33	Radicado Prueba 13	5	2025-10-06 11:18:03.144855	\N
34	Radicado Prueba 13	6	2025-10-06 11:19:33.259015	\N
35	Radicado Prueba 13	7	2025-10-06 11:27:01.859475	\N
12	Radicado Prueba 133	2	2025-10-05 00:00:00	\N
18	Radicado Prueba 133	1	2025-10-05 13:36:08.020708	\N
22	Radicado Prueba 133	4	2025-10-05 20:11:28.543906	\N
36	Radicado Prueba 133	5	2025-10-08 01:27:47.19051	\N
37	Radicado Prueba 133	6	2025-10-08 01:32:50.154929	\N
38	Radicado Prueba 133	7	2025-10-08 01:38:40.446617	\N
39	Radicado Prueba 133	3	2025-10-08 02:28:56.092217	\N
\.


--
-- TOC entry 5129 (class 0 OID 16655)
-- Dependencies: 219
-- Data for Name: expediente; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.expediente (radicado, nombre_expediente, motivo_afectacion, fecha_creacion, encargado_id, direccion, vereda_id) FROM stdin;
Radicado Prueba 133	Expediente Prueba	Envenenamiento	2025-09-20	1233506795	NA	1144
Radicado Prueba 13	Expediente Prueba	Envenenamiento 	2025-09-20	1233506795	NA	1161
Radicado Prueba 21	Expediente Prueba	Envenenamiento 	2025-09-20	1233506795	NA	871
CASCADE	Expediente 11	Minado	2025-09-11	1233506795	NA	1145
Radicado 2	Expediente 2	Envenenamiento 	2025-09-08	1233506795	NA	1137
Radicado Prueba	Expediente Prueba	Envenenamiento 	2025-09-08	1233506795	NA	1134
Radicado 3	Expediente 3	Envenenamiento 	2025-09-08	1233506795	NA	1009
Radicado 1011	Expediente Prueba	Envenenamiento	2025-09-08	1233506795	NA	968
Radicado 11	Expediente 1	Envenenamiento	2025-09-07	1233506795	NA	1156
\.


--
-- TOC entry 5160 (class 0 OID 33450)
-- Dependencies: 250
-- Data for Name: expediente_recurso; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.expediente_recurso (expediente_radicado, recurso_id) FROM stdin;
Radicado 2	3
Radicado 3	2
Radicado Prueba	2
Radicado Prueba 13	1
Radicado Prueba 13	3
Radicado Prueba 21	1
Radicado Prueba 21	3
Radicado 1011	2
CASCADE	3
CASCADE	2
Radicado 11	1
Radicado Prueba 133	1
\.


--
-- TOC entry 5135 (class 0 OID 16733)
-- Dependencies: 225
-- Data for Name: formulacion_cargos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.formulacion_cargos (id, descargos, etapa_id) FROM stdin;
1	t	21
5	t	26
4	f	22
\.


--
-- TOC entry 5141 (class 0 OID 16809)
-- Dependencies: 231
-- Data for Name: involucrado; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.involucrado (id, numero_documento, tipo_documento, nombre, celular, correo) FROM stdin;
1	1233506795	CC	Julian David Rodriguez Fernandez	3214875446	julianrf527@gmail.com
2	1233506796	CC	Julian David Rodriguez Fernandez	3214875446	julianrf527@gmail.com
3	1234567	CC	Joan Amaya	3132020132	pepefernandez730@gmail.com
4	1233506793	CC	Julian Rodriguez	3003133213	ejemplo@gmail.com
5	1056688846	CC	Cesar Mora	3112758002	cesarmaro95@gmail.com
\.


--
-- TOC entry 5142 (class 0 OID 16816)
-- Dependencies: 232
-- Data for Name: involucrado_expediente; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.involucrado_expediente (involucrado_id, expediente_radicado) FROM stdin;
2	Radicado Prueba
1	Radicado Prueba
1	Radicado Prueba 21
2	Radicado Prueba 21
1	CASCADE
1	Radicado 3
2	Radicado 1011
1	Radicado 1011
1	Radicado 11
5	Radicado Prueba 13
1	Radicado Prueba 13
1	Radicado Prueba 133
2	Radicado Prueba 133
\.


--
-- TOC entry 5143 (class 0 OID 16833)
-- Dependencies: 233
-- Data for Name: involucrado_notificacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.involucrado_notificacion (id, proceso_notificacion_id, involucrado_id, numero_envio, fecha_envio, fecha_constancia, notificacion_exitosa) FROM stdin;
27	73	2	213	2025-10-03	2025-09-30	t
28	75	1	2024ER	\N	\N	f
25	70	2	123	2025-10-08	\N	f
34	75	2	2024ER	\N	\N	f
35	72	2	123	\N	\N	f
36	70	1	123	2025-10-08	\N	f
39	93	5	2025EE17	2025-10-03	2025-10-10	f
40	79	1	2024EE13	\N	\N	f
41	95	1	2024ER15	\N	\N	f
42	79	2	2024EE13	\N	\N	f
43	97	2	2025	\N	\N	f
37	91	5	2025EE17	2025-10-07	2025-10-05	f
38	91	1	2025EE17	2025-10-07	2025-10-02	f
\.


--
-- TOC entry 5134 (class 0 OID 16719)
-- Dependencies: 224
-- Data for Name: ley_1333_2009; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ley_1333_2009 (id, tipo_cesacion_id, etapa_id) FROM stdin;
1	3	39
\.


--
-- TOC entry 5148 (class 0 OID 16889)
-- Dependencies: 238
-- Data for Name: log_auditoria; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.log_auditoria (id, expediente_radicado, tabla_afectada, id_registro, tipo_operacion, usuario_id, fecha, descripcion, datos_anteriores, datos_nuevos) FROM stdin;
10	\N	expediente	\N	SELECT	1233506795	2025-09-20 16:58:39.22502	Consulta de archivos: page=1, limit=10, filtros: radicado=None, nombre_expediente=None, fecha_creacion=None, encargado_id=None	null	null
11	\N	expediente	\N	SELECT	1233506795	2025-09-20 16:58:39.268679	Consulta de archivos: page=1, limit=10, filtros: radicado=None, nombre_expediente=None, fecha_creacion=None, encargado_id=None	null	null
12	\N	expediente	\N	SELECT	1233506795	2025-09-20 16:59:16.913408	Consulta de archivos: page=1, limit=10, filtros: radicado=None, nombre_expediente=None, fecha_creacion=None, encargado_id=None	null	null
13	\N	expediente	\N	SELECT	1233506795	2025-09-20 16:59:16.930601	Consulta de archivos: page=1, limit=10, filtros: radicado=None, nombre_expediente=None, fecha_creacion=None, encargado_id=None	null	null
14	\N	expediente	\N	INSERT	1233506796	2025-09-20 20:14:44.967188	Creación de expediente Radicado Prueba 2 con recursos: [1]	null	null
15	\N	expediente	\N	INSERT	1233506796	2025-09-20 20:20:30.055547	Creación de expediente Radicado Prueba 13 con recursos: [1, 3]	null	null
16	\N	expediente	\N	INSERT	1233506796	2025-09-20 20:29:13.80799	Creación de expediente Radicado Prueba 21 con recursos: [1, 3]	null	null
17	\N	involucrado_expediente	\N	INSERT	1233506796	2025-09-20 20:37:21.962614	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba 2	null	null
18	\N	involucrado_expediente	\N	DELETE	1233506795	2025-09-20 20:55:50.239658	Desvinculado involucrado_id=2 del expediente radicado=Radicado 11	null	null
19	\N	involucrado_expediente	\N	INSERT	1233506795	2025-09-20 20:56:10.888901	Vinculado involucrado_id=2 al expediente radicado=Radicado 11	null	null
20	\N	involucrado_expediente	\N	DELETE	1233506795	2025-09-20 20:58:01.207006	Desvinculado involucrado_id=2 del expediente radicado=Radicado 11	null	null
21	\N	expediente	\N	UPDATE	1233506795	2025-09-20 20:59:25.66155	Actualización de expediente 'Radicado 11' a 'Radicado 111' con datos: nombre_expediente=Expediente 11, motivo_afectacion=Minado, direccion=NA, vereda_id=1145	null	null
22	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:03:19.652807	Actualización de expediente 'Radicado Prueba 10' a 'Radicado 100' con datos: nombre_expediente=Expediente Prueba, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=968	null	null
23	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:13:17.18874	Actualización de expediente 'Radicado 111' a 'Radicado 11' con datos: nombre_expediente=Expediente 11, motivo_afectacion=Minado, direccion=NA, vereda_id=1145	null	null
24	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:24:09.289488	Actualización de expediente 'Radicado 100' a 'Radicado 101' con datos: nombre_expediente=Expediente Prueba, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=968	null	null
25	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:28:36.05827	Actualización de expediente 'Radicado 11' a 'Radicado 111' con datos: nombre_expediente=Expediente 11, motivo_afectacion=Minado, direccion=NA, vereda_id=1145	null	null
26	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:35:54.856102	Actualización de expediente 'Radicado 101' a 'Radicado 1011' con datos: nombre_expediente=Expediente Prueba, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=968	null	null
27	\N	expediente	\N	UPDATE	1233506795	2025-09-20 21:41:16.170433	Actualización de expediente 'Radicado 111' a 'Radicado 1111' con datos: nombre_expediente=Expediente 11, motivo_afectacion=Minado, direccion=NA, vereda_id=1145	null	null
28	\N	involucrado_expediente	\N	INSERT	1233506795	2025-09-22 14:10:30.113138	Vinculado involucrado_id=1 al expediente radicado=Radicado 1011	null	null
29	\N	involucrado_expediente	\N	INSERT	1233506795	2025-09-23 17:00:57.1036	Vinculado involucrado_id=2 al expediente radicado=Radicado 1011	null	null
30	\N	involucrado	\N	INSERT	1233506795	2025-09-30 05:26:43.142495	Creación de involucrado id=3, numero_documento=1234567, tipo_documento=CC	null	null
31	\N	involucrado_expediente	\N	INSERT	1233506795	2025-09-30 05:26:43.185874	Vinculado involucrado_id=3 al expediente radicado=Radicado 1011	null	null
32	\N	expediente	\N	UPDATE	1233506795	2025-09-30 05:29:00.993594	Actualización de expediente 'Radicado 1011' a 'Radicado 1011' con datos: nombre_expediente=Expediente Prueba, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=968	null	null
33	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-01 01:25:26.944759	Desvinculado involucrado_id=3 del expediente radicado=Radicado 1011	null	null
34	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-01 01:28:05.72312	Vinculado involucrado_id=3 al expediente radicado=Radicado 1011	null	null
35	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-01 01:28:20.455311	Desvinculado involucrado_id=3 del expediente radicado=Radicado 1011	null	null
36	\N	rol	\N	UPDATE	1233506795	2025-10-01 05:23:46.385905	Actualización de rol ID 4 a nombre 'Ingeniero2' con permisos [1, 2, 3]	null	null
37	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:38:02.844828	Actualización de estado de usuario 1233506796 de True a False	null	null
38	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:38:06.564843	Actualización de estado de usuario 1233506796 de False a True	null	null
39	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:39:16.051096	Actualización de estado de usuario 123508795 de True a False	null	null
40	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:39:18.048328	Actualización de estado de usuario 123508795 de False a True	null	null
41	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:44:19.083655	Actualización de rol del usuario 1233506796 de 10 a 10	null	null
42	\N	usuario	\N	UPDATE	1233506795	2025-10-01 05:44:20.735921	Actualización de estado de usuario 1233506796 de True a False	null	null
43	\N	expediente	\N	UPDATE	1233506795	2025-10-01 05:56:08.478138	Actualización de encargado del expediente Radicado 1111 a 123508795	null	null
44	\N	expediente	\N	UPDATE	1233506795	2025-10-01 05:57:30.252128	Actualización de encargado del expediente CASCADE a 1233506795	null	null
45	\N	expediente	\N	UPDATE	1233506795	2025-10-01 05:57:42.819932	Actualización de expediente 'CASCADE' a 'Radicado 1010' con datos: nombre_expediente=Expediente 11, motivo_afectacion=Minado, direccion=NA, vereda_id=1145	null	null
46	\N	expediente	\N	UPDATE	1233506795	2025-10-01 05:57:53.878392	Actualización de encargado del expediente Radicado 1010 a 123508795	null	null
47	\N	expediente	\N	UPDATE	1233506795	2025-10-02 18:54:40.690077	Actualización de encargado del expediente CASCADE a 1233506795	null	null
48	Radicado Prueba 21	expediente	\N	UPDATE	1233506795	2025-10-02 19:10:06.665986	Actualización de encargado del expediente Radicado Prueba 21 a 1233506795	null	null
49	Radicado Prueba 13	expediente	\N	UPDATE	1233506795	2025-10-02 19:10:07.751068	Actualización de encargado del expediente Radicado Prueba 13 a 1233506795	null	null
51	Radicado 2	expediente	\N	UPDATE	1233506795	2025-10-03 05:36:50.196403	Actualización de encargado del expediente Radicado 2 a 1233506795	null	null
52	\N	notificacion	\N	DELETE	1233506795	2025-10-03 05:46:52.832064	Notificación ID=5 eliminada	null	null
53	Radicado Prueba	expediente	\N	UPDATE	1233506795	2025-10-03 05:58:05.206886	Actualización de encargado del expediente Radicado Prueba a 1233506795	null	null
55	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:06:15.119585	Notificación ID=6 eliminada	null	null
56	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:06:22.06256	Notificación ID=7 eliminada	null	null
57	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:06:29.995858	Notificación ID=8 eliminada	null	null
60	Radicado Prueba 13	expediente	\N	UPDATE	1233506795	2025-10-03 06:08:57.691875	Actualización de encargado del expediente Radicado Prueba 13 a None	null	null
61	Radicado Prueba 21	expediente	\N	UPDATE	1233506795	2025-10-03 06:08:58.642417	Actualización de encargado del expediente Radicado Prueba 21 a None	null	null
62	CASCADE	expediente	\N	UPDATE	1233506795	2025-10-03 06:08:59.457354	Actualización de encargado del expediente CASCADE a None	null	null
63	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-03 06:09:00.649904	Actualización de encargado del expediente Radicado 1011 a None	null	null
64	Radicado 3	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:17.360942	Actualización de encargado del expediente Radicado 3 a 1233506795	null	null
66	Radicado Prueba	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:23.736126	Actualización de encargado del expediente Radicado Prueba a 1233506795	null	null
67	Radicado 2	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:24.920264	Actualización de encargado del expediente Radicado 2 a 1233506795	null	null
69	Radicado Prueba 13	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:27.569498	Actualización de encargado del expediente Radicado Prueba 13 a 1233506795	null	null
70	Radicado Prueba 21	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:28.847882	Actualización de encargado del expediente Radicado Prueba 21 a 1233506795	null	null
71	CASCADE	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:30.083717	Actualización de encargado del expediente CASCADE a 1233506795	null	null
72	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:32.167248	Actualización de encargado del expediente Radicado 1011 a 1233506795	null	null
73	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:16.930218	Notificación ID=13 eliminada	null	null
74	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:21.678948	Notificación ID=21 eliminada	null	null
75	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:24.530894	Notificación ID=19 eliminada	null	null
76	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:32.548348	Notificación ID=14 eliminada	null	null
77	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:34.359356	Notificación ID=15 eliminada	null	null
78	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:35.85544	Notificación ID=16 eliminada	null	null
79	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:37.218096	Notificación ID=17 eliminada	null	null
80	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:39.53921	Notificación ID=18 eliminada	null	null
81	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:37:42.464844	Notificación ID=20 eliminada	null	null
82	Radicado 3	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:32.993796	Actualización de encargado del expediente Radicado 3 a None	null	null
84	Radicado Prueba	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:34.830096	Actualización de encargado del expediente Radicado Prueba a None	null	null
85	Radicado 2	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:35.755078	Actualización de encargado del expediente Radicado 2 a None	null	null
86	Radicado 2	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:38.785921	Actualización de encargado del expediente Radicado 2 a 1233506795	null	null
87	Radicado Prueba	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:39.905264	Actualización de encargado del expediente Radicado Prueba a 1233506795	null	null
89	Radicado 3	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:42.208856	Actualización de encargado del expediente Radicado 3 a 1233506795	null	null
90	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:39:38.007562	Notificación ID=25 eliminada	null	null
91	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:39:39.331745	Notificación ID=24 eliminada	null	null
92	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-03 06:39:51.772797	Actualización de encargado del expediente Radicado 1011 a None	null	null
93	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-03 06:39:53.346949	Actualización de encargado del expediente Radicado 1011 a 1233506795	null	null
94	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:40:39.377827	Notificación ID=22 eliminada	null	null
95	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:40:41.233738	Notificación ID=23 eliminada	null	null
96	\N	notificacion	\N	DELETE	1233506795	2025-10-03 06:40:42.915947	Notificación ID=26 eliminada	null	null
97	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:09:04.683035	Vinculado involucrado_id=2 al expediente radicado=Radicado Prueba	null	null
98	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:09:36.593974	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba	null	null
99	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:11:02.613438	Vinculado involucrado_id=1 al expediente radicado=Radicado 3	null	null
100	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:12:52.61732	Desvinculado involucrado_id=1 del expediente radicado=Radicado 3	null	null
59	Radicado Prueba 133	expediente	\N	UPDATE	1233506795	2025-10-03 06:08:55.573841	Actualización de encargado del expediente Radicado Prueba 2 a None	null	null
68	Radicado Prueba 133	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:26.003504	Actualización de encargado del expediente Radicado Prueba 2 a 1233506795	null	null
101	\N	involucrado	\N	INSERT	1233506795	2025-10-05 16:13:23.784189	Creación de involucrado id=4, numero_documento=1233506793, tipo_documento=CC	null	null
102	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:13:23.795061	Vinculado involucrado_id=4 al expediente radicado=Radicado 3	null	null
103	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:14:28.56063	Vinculado involucrado_id=1 al expediente radicado=Radicado 1	null	null
104	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:18:09.13456	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba 21	null	null
105	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:18:51.393624	Vinculado involucrado_id=2 al expediente radicado=Radicado Prueba 21	null	null
106	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:24:39.103167	Vinculado involucrado_id=1 al expediente radicado=Radicado 2	null	null
107	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:27:44.399586	Desvinculado involucrado_id=1 del expediente radicado=CASCADE	null	null
108	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:27:51.766175	Vinculado involucrado_id=1 al expediente radicado=CASCADE	null	null
109	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:29:12.844106	Desvinculado involucrado_id=4 del expediente radicado=Radicado 3	null	null
110	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:29:21.647183	Vinculado involucrado_id=1 al expediente radicado=Radicado 3	null	null
111	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:29:42.170182	Desvinculado involucrado_id=1 del expediente radicado=Radicado 3	null	null
112	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:29:54.152917	Vinculado involucrado_id=1 al expediente radicado=Radicado 3	null	null
113	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:30:09.201689	Desvinculado involucrado_id=1 del expediente radicado=Radicado 3	null	null
114	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:31:15.088486	Vinculado involucrado_id=1 al expediente radicado=Radicado 3	null	null
115	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:35:31.342879	Desvinculado involucrado_id=1 del expediente radicado=Radicado Prueba 2	null	null
116	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:46:10.235504	Vinculado involucrado_id=1 al expediente radicado=Radicado 1011	null	null
117	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:50:15.542106	Vinculado involucrado_id=1 al expediente radicado=Radicado 1011	null	null
118	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:50:33.294226	Vinculado involucrado_id=2 al expediente radicado=Radicado 1011	null	null
119	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 16:50:43.809659	Desvinculado involucrado_id=1 del expediente radicado=Radicado 1011	null	null
120	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 16:52:05.689179	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba 2	null	null
121	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-05 17:41:33.955522	Desvinculado involucrado_id=1 del expediente radicado=Radicado 2	null	null
122	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-05 21:49:51.211356	Vinculado involucrado_id=1 al expediente radicado=Radicado 1011	null	null
54	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-03 05:58:07.403668	Actualización de encargado del expediente Radicado 1 a 1233506795	null	null
58	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-03 06:07:28.54579	Actualización de encargado del expediente Radicado 1 a 123508795	null	null
65	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-03 06:36:22.739775	Actualización de encargado del expediente Radicado 1 a 1233506795	null	null
83	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:33.829502	Actualización de encargado del expediente Radicado 1 a None	null	null
88	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-03 06:38:41.066795	Actualización de encargado del expediente Radicado 1 a 1233506795	null	null
123	\N	expediente	\N	UPDATE	1233506795	2025-10-05 22:41:00.726216	Actualización de expediente 'Radicado 1' a 'Radicado 11' con datos: nombre_expediente=Expediente 1, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=1156	null	null
124	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-06 15:28:02.386903	Actualización de encargado del expediente Radicado 1011 a 123508795	null	null
125	Radicado 1011	expediente	\N	UPDATE	1233506795	2025-10-06 15:28:04.363251	Actualización de encargado del expediente Radicado 1011 a 1233506795	null	null
126	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-06 15:28:29.88946	Actualización de encargado del expediente Radicado 11 a 1233506796	null	null
127	Radicado 11	expediente	\N	UPDATE	1233506795	2025-10-06 15:28:31.243792	Actualización de encargado del expediente Radicado 11 a 1233506795	null	null
128	\N	notificacion	\N	DELETE	1233506795	2025-10-06 15:29:19.012666	Notificación ID=28 eliminada	null	null
129	\N	notificacion	\N	DELETE	1233506795	2025-10-06 15:29:23.56371	Notificación ID=30 eliminada	null	null
130	\N	involucrado	\N	INSERT	1233506795	2025-10-06 15:36:30.416064	Creación de involucrado id=5, numero_documento=1056688846, tipo_documento=CC	null	null
131	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-06 15:36:30.435634	Vinculado involucrado_id=5 al expediente radicado=Radicado Prueba 13	null	null
132	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-06 15:37:00.459808	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba 13	null	null
133	\N	involucrado_expediente	\N	DELETE	1233506795	2025-10-06 15:43:24.384735	Desvinculado involucrado_id=1 del expediente radicado=Radicado Prueba 2	null	null
134	\N	rol	\N	DELETE	1233506795	2025-10-07 18:55:30.076516	Eliminación de rol ID 9 con nombre 'Ingeniero 10011' y sus permisos asociados	null	null
50	Radicado Prueba 133	expediente	\N	UPDATE	1233506795	2025-10-02 19:10:10.647258	Actualización de encargado del expediente Radicado Prueba 2 a 1233506795	null	null
135	\N	expediente	\N	UPDATE	1233506795	2025-10-07 23:24:31.21551	Actualización de expediente 'Radicado Prueba 2' a 'Radicado Prueba 133' con datos: nombre_expediente=Expediente Prueba, motivo_afectacion=Envenenamiento, direccion=NA, vereda_id=1121	null	null
136	Radicado Prueba 133	expediente	Radicado Prueba 133	UPDATE	1233506795	2025-10-07 23:34:10.068911	Actualizó expediente 'Radicado Prueba 133' a 'Radicado Prueba 133'	{"radicado": "Radicado Prueba 133", "direccion": "NA", "vereda_id": 1121, "encargado_id": 1233506795, "motivo_afectacion": "Envenenamiento", "nombre_expediente": "Expediente Prueba"}	{"radicado": "Radicado Prueba 133", "direccion": "NA", "vereda_id": 1144, "motivo_afectacion": "Envenenamiento", "nombre_expediente": "Expediente Prueba"}
137	Radicado Prueba 13	expediente	\N	UPDATE	1233506795	2025-10-08 03:05:46.681472	Actualización de encargado del expediente Radicado Prueba 13 a 123508795	null	null
138	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-08 06:20:58.834284	Vinculado involucrado_id=1 al expediente radicado=Radicado Prueba 133	null	null
139	Radicado Prueba 133	involucrado_notificacion	40	INSERT	1233506795	2025-10-08 06:21:10.969831	Se agregó una nueva notificación ID=40 para el proceso ID=79 en el expediente Radicado Prueba 133.	null	{"fecha_envio": null, "numero_envio": "2024EE13", "involucrado_id": 1, "fecha_constancia": null, "notificacion_exitosa": false, "proceso_notificacion_id": 79}
140	\N	MedidaPreventiva	\N	INSERT	1233506795	2025-10-08 06:21:29.02245	Creación de medida preventiva (ID: 4) en el expediente Radicado Prueba 133	null	{"id": 4, "especie": "Especie x", "id_tipo": 1, "cantidad": "123 m³", "etapa_id": 18, "estado_medida": false}
141	\N	proceso_notificacion	\N	INSERT	1233506795	2025-10-08 06:21:37.815565	Se creó el proceso 'AUTO 123' (ID=95) en la etapa 18.	null	null
142	Radicado Prueba 133	involucrado_notificacion	41	INSERT	1233506795	2025-10-08 06:21:48.957482	Se agregó una nueva notificación ID=41 para el proceso ID=95 en el expediente Radicado Prueba 133.	null	{"fecha_envio": null, "numero_envio": "2024ER15", "involucrado_id": 1, "fecha_constancia": null, "notificacion_exitosa": false, "proceso_notificacion_id": 95}
143	\N	DecisionFondo	6	CREACIÓN	1233506795	2025-10-08 06:35:32.984223	Creación de decisión de fondo en expediente Radicado Prueba 133 (etapa_id=37)	null	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 1}
144	\N	DecisionFondo	6	ACTUALIZACIÓN	1233506795	2025-10-08 06:38:29.085988	Actualización de decisión de fondo en expediente Radicado Prueba 133	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 1}	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 2}
145	\N	Etapa	\N	INSERT	1233506795	2025-10-08 06:38:40.451111	Creación de una nueva etapa (ID: 38) para el expediente Radicado Prueba 133 con tipo de etapa 7	null	{"etapa_id": 38, "tipo_etapa_id": 7, "expediente_radicado": "Radicado Prueba 133"}
146	\N	EjecucionSancion	3	CREACIÓN	1233506795	2025-10-08 07:05:56.337623	Creación de ejecución de sanción en expediente Radicado Prueba 133	null	{"ruia": false, "etapa_id": 38, "disposicion": false, "cobro_coactivo": false}
147	\N	EjecucionSancion	3	ACTUALIZACIÓN	1233506795	2025-10-08 07:08:03.387574	Actualización de ejecución de sanción ID 3	{"ruia": false, "disposicion": false, "cobro_coactivo": false}	{"ruia": false, "disposicion": false, "cobro_coactivo": false}
148	\N	EjecucionSancion	3	ACTUALIZACIÓN	1233506795	2025-10-08 07:11:59.96538	Actualización de ejecución de sanción ID 3	{"ruia": false, "disposicion": false, "cobro_coactivo": false}	{"ruia": false, "disposicion": false, "cobro_coactivo": false}
149	\N	EjecucionSancion	3	ACTUALIZACIÓN	1233506795	2025-10-08 07:22:20.395947	Actualización de ejecución de sanción ID 3	{"ruia": false, "disposicion": false, "cobro_coactivo": false}	{"ruia": false, "disposicion": false, "cobro_coactivo": false}
150	\N	proceso_notificacion	\N	INSERT	1233506795	2025-10-08 07:22:41.501935	Se creó el proceso '123' (ID=96) en la etapa 12.	null	null
151	Radicado Prueba 133	proceso_notificacion	96	DELETE	1233506795	2025-10-08 07:22:56.028688	Se eliminó el proceso ID=96 ('123') y sus notificaciones asociadas.	{"id": 96, "nombre": "123"}	null
152	\N	proceso_notificacion	\N	INSERT	1233506795	2025-10-08 07:23:01.284237	Se creó el proceso '123' (ID=97) en la etapa 12.	null	null
153	\N	proceso_notificacion	97	UPDATE	1233506795	2025-10-08 07:23:55.298303	Se actualizó el proceso ID=97: nombre '123' → 'AUTO 123xd'.	{"nombre": "123"}	{"nombre": "AUTO 123xd"}
154	Radicado Prueba 133	expediente	Radicado Prueba 133	UPDATE	1233506795	2025-10-08 07:26:07.638827	Actualizó expediente 'Radicado Prueba 133' a 'Radicado Prueba 133'	{"radicado": "Radicado Prueba 133"}	{"radicado": "Radicado Prueba 133", "direccion": "NA", "vereda_id": 1144, "motivo_afectacion": "Envenenamiento", "nombre_expediente": "Expediente Prueba"}
155	\N	involucrado_expediente	\N	INSERT	1233506795	2025-10-08 07:26:28.142771	Vinculado involucrado_id=2 al expediente radicado=Radicado Prueba 133	null	null
156	Radicado Prueba 133	involucrado_notificacion	42	INSERT	1233506795	2025-10-08 07:26:39.457117	Se agregó una nueva notificación ID=42 para el proceso ID=79 en el expediente Radicado Prueba 133.	null	{"fecha_envio": null, "numero_envio": "2024EE13", "involucrado_id": 2, "fecha_constancia": null, "notificacion_exitosa": false, "proceso_notificacion_id": 79}
157	Radicado Prueba 133	involucrado_notificacion	43	INSERT	1233506795	2025-10-08 07:27:25.303369	Se agregó una nueva notificación ID=43 para el proceso ID=97 en el expediente Radicado Prueba 133.	null	{"fecha_envio": null, "numero_envio": "2025", "involucrado_id": 2, "fecha_constancia": null, "notificacion_exitosa": false, "proceso_notificacion_id": 97}
158	\N	MedidaPreventiva	\N	UPDATE	1233506795	2025-10-08 07:27:35.336773	Actualización de medida preventiva (ID: 4) en el expediente Radicado Prueba 133	{"id": 4, "especie": "Especie x", "id_tipo": 1, "cantidad": "123 m³", "etapa_id": 18, "estado_medida": false}	{"id": 4, "especie": "Especie x", "id_tipo": 1, "cantidad": "12345 m³", "etapa_id": 18, "estado_medida": false}
159	\N	FormulacionCargos	4	UPDATE	1233506795	2025-10-08 07:30:11.872316	Actualización de formulación de cargos (ID: 4) para el expediente Radicado Prueba 133.	{"id": 4, "descargos": false}	{"id": 4, "descargos": true}
160	\N	DecisionFondo	6	ACTUALIZACIÓN	1233506795	2025-10-08 07:30:28.107109	Actualización de decisión de fondo en expediente Radicado Prueba 133	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 2}	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 4}
161	Radicado Prueba 13	expediente	\N	UPDATE	1233506795	2025-10-08 07:32:20.832592	Actualización de encargado del expediente Radicado Prueba 13 a 1233506795	null	null
162	Radicado Prueba 13	involucrado_notificacion	37	UPDATE	1233506795	2025-10-08 08:01:11.124121	Se actualizó la notificación ID=37 del expediente Radicado Prueba 13.	{"fecha_envio": "2025-10-07", "numero_envio": "2025EE17", "involucrado_id": 5, "fecha_constancia": "2025-10-07", "notificacion_exitosa": true}	{"fecha_envio": "2025-10-07", "numero_envio": "2025EE17", "involucrado_id": 5, "fecha_constancia": "2025-10-05", "notificacion_exitosa": false}
163	Radicado Prueba 13	involucrado_notificacion	38	UPDATE	1233506795	2025-10-08 08:01:19.637502	Se actualizó la notificación ID=38 del expediente Radicado Prueba 13.	{"fecha_envio": "2025-10-07", "numero_envio": "2025EE17", "involucrado_id": 1, "fecha_constancia": "2025-10-07", "notificacion_exitosa": true}	{"fecha_envio": "2025-10-07", "numero_envio": "2025EE17", "involucrado_id": 1, "fecha_constancia": "2025-10-02", "notificacion_exitosa": false}
164	\N	Ley13332009	\N	INSERT	1233506795	2025-10-08 09:24:03.590477	Creación de registro Ley 1333/2009 (ID: 1) en el expediente Radicado Prueba 133	null	{"id": 1, "etapa_id": 39, "tipo_cesacion_id": 1}
165	\N	Ley13332009	1	UPDATE	1233506795	2025-10-08 09:24:30.389649	Actualización de Ley 1333/2009 (ID: 1) en expediente Radicado Prueba 133. tipo_cesacion_id: 1 → 2	{"tipo_cesacion_id": 1}	{"tipo_cesacion_id": 2}
170	\N	DecisionFondo	6	ACTUALIZACIÓN	1233506795	2025-10-08 09:26:57.204369	Actualización de decisión de fondo en expediente Radicado Prueba 133	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 2}	{"detalle": "N/AA", "etapa_id": 37, "tipo_sancion_id": 2}
166	\N	Ley13332009	1	UPDATE	1233506795	2025-10-08 09:25:50.887531	Actualización de Ley 1333/2009 (ID: 1) en expediente Radicado Prueba 133. tipo_cesacion_id: 2 → 3	{"tipo_cesacion_id": 2}	{"tipo_cesacion_id": 3}
167	\N	FormulacionCargos	4	UPDATE	1233506795	2025-10-08 09:26:36.185949	Actualización de formulación de cargos (ID: 4) para el expediente Radicado Prueba 133.	{"id": 4, "descargos": true}	{"id": 4, "descargos": false}
168	\N	proceso_notificacion	\N	INSERT	1233506795	2025-10-08 09:26:44.677119	Se creó el proceso '123xd' (ID=98) en la etapa 36.	null	null
169	\N	DecisionFondo	6	ACTUALIZACIÓN	1233506795	2025-10-08 09:26:53.325893	Actualización de decisión de fondo en expediente Radicado Prueba 133	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 4}	{"detalle": "N/A", "etapa_id": 37, "tipo_sancion_id": 2}
171	\N	EjecucionSancion	3	ACTUALIZACIÓN	1233506795	2025-10-08 09:27:04.602534	Actualización de ejecución de sanción ID 3	{"ruia": false, "disposicion": false, "cobro_coactivo": false}	{"ruia": true, "disposicion": true, "cobro_coactivo": true}
\.


--
-- TOC entry 5133 (class 0 OID 16700)
-- Dependencies: 223
-- Data for Name: medida_preventiva; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.medida_preventiva (id, id_tipo, cantidad, especie, estado_medida, etapa_id) FROM stdin;
1	2	12345 ton	Especie xy	f	6
3	1	123 m³	Especie xy	f	15
2	3	123 Ha	Especie z	f	13
4	1	12345 m³	Especie x	f	18
\.


--
-- TOC entry 5127 (class 0 OID 16636)
-- Dependencies: 217
-- Data for Name: municipio; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.municipio (id, nombre) FROM stdin;
64	Chivor
65	Ciénega
66	Garagoa
67	Guateque
68	Guayatá
69	Jenesano
70	La Capilla
71	Macanal
72	Nuevo Colón
73	Pachavita
74	Ramiriquí
75	San Luis de Gaceno
76	Santa María
77	Somondoco
78	Sutatenza
79	Tenza
80	Tibaná
81	Turmequé
82	Umbita
83	Ventaquemada
84	Viracacha
\.


--
-- TOC entry 5154 (class 0 OID 17039)
-- Dependencies: 244
-- Data for Name: notificacion_usuario; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notificacion_usuario (id, mensaje, expediente_radicado, numero_documento) FROM stdin;
9	Se te ha asignado un nuevo expediente	Radicado 11	123508795
27	Se te ha asignado un nuevo expediente	Radicado 1011	123508795
29	Se te ha asignado un nuevo expediente	Radicado 11	1233506796
31	Se te ha asignado un nuevo expediente	Radicado Prueba 13	123508795
\.


--
-- TOC entry 5146 (class 0 OID 16863)
-- Dependencies: 236
-- Data for Name: permiso; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permiso (id, nombre, menu_path) FROM stdin;
1	usuarios_agregar	/user/add
2	usuarios_gestionar	/user/manage
3	usuarios_roles y permisos	/user/rol
4	expediente_gestionar	/file/manage
5	expediente_asignar encargados	/file/assign_manager
6	expediente_visualizar	/file/view
7	expediente_alertas	/file/alerts
\.


--
-- TOC entry 5140 (class 0 OID 16794)
-- Dependencies: 230
-- Data for Name: proceso_notificacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.proceso_notificacion (id, fecha_creacion, etapa_id, tipo_id, nombre) FROM stdin;
70	2025-10-03	4	2	AUTO 123
72	2025-10-03	4	1	AUTO Expediente Prueba
73	2025-10-03	6	3	AUTO 123
74	2025-10-03	6	4	123
75	2025-10-05	9	1	Expediente Prueba
76	2025-10-05	10	1	123
78	2025-10-05	8	1	AUTO 123
79	2025-10-05	12	1	AUTO 123
77	2025-10-05	11	1	123
80	2025-10-05	5	1	AUTO 123
81	2025-10-05	13	4	AUTO Expediente Prueba
85	2025-10-05	20	7	123
90	2025-10-06	26	9	123
91	2025-10-06	30	1	AUTO 001
92	2025-10-06	30	2	RES 002
93	2025-10-06	31	5	AUTO 001
94	2025-10-06	32	9	AUTO 001
95	2025-10-08	18	3	AUTO 123
97	2025-10-08	12	2	AUTO 123xd
98	2025-10-08	36	10	123xd
\.


--
-- TOC entry 5159 (class 0 OID 33426)
-- Dependencies: 249
-- Data for Name: recurso_afectado; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.recurso_afectado (id, nombre) FROM stdin;
1	Agua
2	Aire
3	Bosque
\.


--
-- TOC entry 5151 (class 0 OID 16995)
-- Dependencies: 241
-- Data for Name: rol; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rol (id, nombre) FROM stdin;
1	admin
2	abogado
3	Ingeniero
10	Ingeniero 1000
5	Ingeniero 3
6	Ingeniero 4
11	asd
7	Ingeniero 10
8	Ingeniero 2
4	Ingeniero2
\.


--
-- TOC entry 5152 (class 0 OID 17005)
-- Dependencies: 242
-- Data for Name: rol_permiso; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rol_permiso (rol_id, permiso_id) FROM stdin;
1	1
1	2
3	1
3	2
3	3
10	4
5	2
5	1
6	1
6	2
11	1
11	2
7	1
7	2
7	3
8	1
8	2
8	3
8	4
8	5
4	1
4	2
4	3
\.


--
-- TOC entry 5168 (class 0 OID 49861)
-- Dependencies: 258
-- Data for Name: tipo_cesacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tipo_cesacion (id, nombre) FROM stdin;
1	Muerte de investigado
2	No es constitutivo de infracción ambiental
3	Conducta investigada no es imputable al presunto infractor
4	La actividad esta legalmente amparada/autorizada
\.


--
-- TOC entry 5130 (class 0 OID 16667)
-- Dependencies: 220
-- Data for Name: tipo_etapa; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tipo_etapa (id, nombre) FROM stdin;
1	DETALLE MEDIDA PREVENTIVA
2	INDAGACION PRELIMINAR
3	PROCEDIMIENTO LEY 1333 DE 2009
5	APERTURA ETAPA PROBATORIA
4	FORMULACION DE CARGOS
6	DECISION DE FONDO
7	EJECUCION DE LA SANCION
\.


--
-- TOC entry 5132 (class 0 OID 16693)
-- Dependencies: 222
-- Data for Name: tipo_medida; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tipo_medida (id, nombre) FROM stdin;
1	Decomiso preventivo
2	Suspensión del proyecto
3	Estudios y evaluaciones requeridas para conocer la naturaleza de lo daños
\.


--
-- TOC entry 5139 (class 0 OID 16785)
-- Dependencies: 229
-- Data for Name: tipo_notificacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tipo_notificacion (id, nombre, tipo_etapa_id) FROM stdin;
6	Diligencia ADM ART 22	3
7	Cesacion Art. 23 L.1333/2009	3
8	Suspension anticipáda del proceso AUTO/RES	3
9	Formula Cargos Art 25 Ley 1333 de 2009	4
1	Indagacíon Preliminar	2
3	Legalización de medida preventiva Art. 15 L.1333/2009	1
4	Imposición de medida preventiva Art. 36 L.1333/2009	1
5	Inicio proceso Art. 18L. 1333/2009	3
2	Diligencia ADM ART 22	2
10	Abre periodo probatorio Art. 26 L.1333/2009	5
11	Recurso de reposición Art. 26 L.1333/2009	5
12	Cierra periodo probatorio Art. 26 L1333/2009	5
13	Alegatos de conclusión	5
14	Resolución y fecha decide Art. 27 L.1333/2009	6
15	Recurso de reposición  Art. 30 L.1333/2009	6
\.


--
-- TOC entry 5136 (class 0 OID 16745)
-- Dependencies: 226
-- Data for Name: tipo_sancion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tipo_sancion (id, nombre) FROM stdin;
1	Amonestación escrita
2	Cierre temporal o definitivo
3	Revocatorio o caducidad de licencia ambiental, autorización, concesión, permiso o registro
4	Demolición de obra a costa del infractor
5	Decomiso preventivo de especímenes, especies silvestres
6	Restitución de especímenes de flora y fauna silvestres o acuática
\.


--
-- TOC entry 5144 (class 0 OID 16850)
-- Dependencies: 234
-- Data for Name: usuario; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuario (numero_documento, nombre_usuario, correo, hash_contrasena, activo, ultimo_ingreso, creado_en, rol_id) FROM stdin;
123508795	Julian David Rodriguez Fernandez	jrodriguezfe@unal.edu.co	$2b$12$v4niRhGKgt5OzUHCYR5xruK1E/f4yANh0Jud1F50rcDdEcBUQw.M.	t	2025-09-01 15:07:03.00815	2025-09-01 15:07:03.008155	8
1233506795	Julian David Rodriguez	julianrf527@gmail.com	$2b$12$1lsDTStN3eA3ET37mmR0ceSjD4xS6LdKLmtQBe70FSurK.hNWas/W	t	2025-10-08 07:43:41.732755	2025-07-15 13:42:39.599884	1
1233506796	Julian david rodriguez fernandez	juliandrf527@gmail.com	$2b$12$.0VZAB3EbApyX6hwhNY1/OvTr7ksxBKwRsHNX5w.AtDeMYNZUSS1y	t	2025-10-03 01:28:29.686076	2025-08-14 23:35:02.826552	10
123124124	Julian David Rodriguez Fernandez	morofake527@gmail.com	$2b$12$uWY7QG55I6hXkcljotLSzOwGGS0FT7E3nqEkXZvp4/v5urcOeQ8Aq	t	2025-10-07 17:24:19.389358	2025-09-01 15:12:57.422527	3
\.


--
-- TOC entry 5128 (class 0 OID 16643)
-- Dependencies: 218
-- Data for Name: vereda; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.vereda (id, nombre, municipio_id) FROM stdin;
825	Alimentos	64
826	Camoyo	64
827	Centro	64
828	Chivor Chiquito	64
829	El Pino	64
830	Guali	64
831	Higuerón	64
832	Jagua-La Playa	64
833	La Esmeralda	64
834	La Esperanza	64
835	San Cayetano	64
836	San Martín	64
837	San Francisco	64
838	Sinaí	64
839	Zona Urbana	64
840	San Vicente	65
841	Albañil	65
842	Plan	65
843	Reavita	65
844	Tapias	65
845	Cebadal	65
846	Espinal	65
847	Piedra Larga	65
848	Calabazal	65
849	Guatareta	65
850	Manzanos	65
851	Centro	65
852	Zona Urbana	65
853	Arada Chiquita	66
854	Arada Grande	66
855	Bancos de Arada	66
856	Bancos de Páramo	66
857	Bojacá	66
858	Caldera Abajo	66
859	Caldera Arriba	66
860	Caracol	66
861	Ciénega Guarumal	66
862	Ciénega Tablón	66
863	Ciénega Valvanera	66
864	Cucharero	66
865	Curial	66
866	Escobal	66
867	Fumbaque	66
868	Guanica Grande Abajo	66
869	Guanica Grande Arriba	66
870	Guanica	66
871	La Calera	66
872	La Peña	66
873	La Salina	66
874	Las Cruces	66
875	Las Lajas	66
876	Las Palmas	66
877	Los Chorros	66
878	Los Mangos	66
879	Muese	66
880	Montebello	66
881	Nazareth	66
882	Páramo	66
883	Peña Blanca	66
884	Planadas	66
885	Puente Roto	66
886	Puerto Nuevo	66
887	San Isidro	66
888	San José	66
889	San Luis	66
890	San Miguel	66
891	San Roque	66
892	Santa Bárbara	66
893	Santa Rosa	66
894	Santa Rita	66
895	Tablón	66
896	Valvanera	66
897	Venta Quemada	66
898	Zona Urbana	66
899	Cantoras	67
900	Chinquica	67
901	Chorro de Oro	67
902	Gaunza Arriba	67
903	Chorro Tinto	67
904	Gotera	67
905	Gaunza Abajo	67
906	Gaunza Arriba	67
907	Juntas	67
908	LLano Grande	67
909	Mortiño	67
910	Munanta	67
911	Piedra Parada	67
912	Pozos	67
913	Puente	67
914	Rosales	67
915	Sibatá	67
916	Siravitá	67
917	Suaitoque	67
918	Tincachoque	67
919	Ubujuca	67
920	Zona Urbana	67
921	Caliche Abajo	68
922	Caliche Arriba	68
923	Sunuba	68
924	Escaleras	68
925	Volcán	68
926	Barrero Negro	68
927	Hato Viejo	68
928	Sochaquira Abajo	68
929	Sochaquira Arriba	68
930	Tencua Arriba	68
931	Tencua Abajo	68
932	Rincón Abajo	68
933	Rincón Arriba	68
934	Romaguira	68
935	Guarumal	68
936	Fonsaque Abajo	68
937	Fonsaque Arriba	68
938	Ciavita I	68
939	Ciavita II	68
940	Ciavita III	68
941	Carrizal	68
942	Portachuelo	68
943	Alazán Abajo	68
944	Alazán Arriba	68
945	Zulia	68
946	Tablón	68
947	Guayatá	68
948	Guayabal	68
949	Chitavita	68
950	Juntas	68
951	Baganique Alto	69
952	Baganique Medio	69
953	Bagamuire Bajo	69
954	Carrizal	69
955	Cardonal	69
956	Dulceyes	69
957	Falengue	69
958	Foraquira	69
959	Monqueta	69
960	Pacées	69
961	Palenque	69
962	Piranguata	69
963	Pulidos	69
964	Rodríguez	69
965	Solderes	69
966	Supaneca	69
967	Volador	69
968	Camagoa	70
969	Palma Arriba	70
970	Palma Abajo	70
971	Zinc	70
972	El Hato	70
973	Páramo	70
974	Suntafita	70
975	Ubanaca	70
976	Chucio	70
977	Truco	70
978	Peñas	70
979	Barro Blanco Abajo	70
980	Barro Blanco Arriba	70
981	Datí Chiquito	71
982	Datí Grande	71
983	Trapichito	71
984	Pantanos	71
985	Limesa	71
986	Pedroguz Grande	71
987	Pedroguz Chiquito	71
988	Volador	71
989	Centro	71
990	Viajal	71
991	La Vega	71
992	Peña Blanca	71
993	Naranjal	71
994	Limón	71
995	Media Estancia	71
996	Quebrada Negra	71
997	Guamo	71
998	Alfaras	72
999	Zapatero	72
1000	El Uvo	72
1001	Llano Grande	72
1002	Carbonera	72
1003	Fiota	72
1004	Potreros	72
1005	Tapias	72
1006	Invita	72
1007	Sorca	72
1008	Aposentos	72
1009	Tejar Abajo	72
1010	Pavaquira	72
1011	Tejar Arriba	72
1012	Jabonera	72
1013	Centro Rural	72
1014	Susaquira	73
1015	Sacaneca	73
1016	Llano Grande	73
1017	Centro	73
1018	Pie de Peña	73
1019	Guacal	73
1020	Aguacuina	73
1021	Buenavista	73
1022	Hato Grande	73
1023	Rosal	74
1024	Peñas	74
1025	Santana	74
1026	Potreros	74
1027	Pabellón	74
1028	Resguardo Bajo	74
1029	Resguardo Alto	74
1030	Faravita	74
1031	Cacicedos	74
1032	Santuario	74
1033	Romasal	74
1034	Gachacavita	74
1035	Fernandez	74
1036	Hervideros	74
1037	Fragua	74
1038	Común	74
1039	Pantano Largo	74
1040	Naguata	74
1041	Guacamayas	74
1042	Farquená	74
1043	Escobal	74
1044	Ortigal	74
1045	Chuscal	74
1046	Guayabal	74
1047	Centro Urbano	74
1048	Cavetero	75
1049	Santa María	75
1050	Buenavista	75
1051	La Esperanza	75
1052	Manuel	75
1053	Santa Rita	75
1054	La Florida	75
1055	San José del Chuy	75
1056	La Unión	75
1057	La Reforma	75
1058	Guchipas	75
1059	San Pedro	75
1060	Buenos Aires	75
1061	Chavinave	75
1062	El Triunfo	75
1063	Porvenir	75
1064	San Pablo	75
1065	Buenos Aires Alto	75
1066	Buenos Aires Bajo	75
1067	La Esperanza Baja	75
1068	El Bosque	75
1069	Guayabal	75
1070	Las Minas	75
1071	La Granja	75
1072	El Vergel	75
1073	Lucero	75
1074	Inglolandia	75
1075	Inglolandia Bajo	75
1076	Gachaneque	75
1077	Palmarito	75
1078	La Laguna	75
1079	La Reforma Baja	75
1080	Rio Chiquito	75
1081	Caño Tigre	75
1082	Cortijo	76
1083	Santa Lucía	76
1084	San Rafael	76
1085	Gachaneca	76
1086	Plazuelas	76
1087	San Agustín	76
1088	Caño Negro	76
1089	Centro	76
1090	Santa Teresa	76
1091	San Ignacio	76
1092	Gacal Bajo	76
1093	La Vega	76
1094	Vijagual	76
1095	Chaves Uribe	76
1096	Calima	76
1097	Fórmulas	76
1098	Bohórquez	77
1099	Boya I	77
1100	Boya II	77
1101	Cabecera	77
1102	Centro	77
1103	Cucurinca	77
1104	Guandoque	77
1105	Jagüey	77
1106	La Florida	77
1107	La Palma	77
1108	San Antonio (Chiguato)	77
1109	San Isidro	77
1110	Santa Bárbara	77
1111	Zanja Honda	77
1112	Zanja Fría	77
1113	Zanja	77
1114	Zona urbana	78
1115	Boqueron	78
1116	Paramo	78
1117	Gaque	78
1118	Piedra larga	78
1119	Salitre	78
1120	Ovejeras	78
1121	Sisique centro	78
1122	Sisique	78
1123	Irson	78
1124	Guamo	78
1125	Barzal	79
1126	Apostólico	79
1127	Chaguateque	79
1128	Quebradas	79
1129	Resguardo	79
1130	Valle Grande Arriba	79
1131	Valle Grande Abajo	79
1132	Ruche	79
1133	Mutatá	79
1134	Cota Grande	79
1135	Yacata	79
1136	Yopalosa	79
1137	Cota Chica	79
1138	Agrado	79
1139	Agrado Alto	79
1140	Zona Urbana	79
1141	Supaneca Arriba	80
1142	Supaneca Abajo	80
1143	Juana Ruiz	80
1144	Laja	80
1145	Sirata	80
1146	Suta Abajo	80
1147	Suta Arriba	80
1148	Siuman	80
1149	Carare	80
1150	Ruche	80
1151	Chiguata	80
1152	Quichatoque	80
1153	Las Juntas	80
1154	Maranta	80
1155	Sastoque	80
1156	Sirama	80
1157	Zanja	80
1158	Piedras de Candela	80
1159	Bayeta	80
1160	Batán	80
1161	Mombita	80
1162	Arrubla	80
1163	Gambita	80
1164	Mangles	80
1165	Vereda Pie de Peña	80
1166	San Jose	80
1167	El Carmen	80
1168	Sitanta	80
1169	Rosales	81
1170	Rincoque	81
1171	Centro Urbano	81
1172	Jaraquira	81
1173	Pozo Negro	81
1174	Jurata	81
1175	Pascata	81
1176	Volcán Blanco	81
1177	Teguanaque	81
1178	Chiquirita	81
1179	Joyagua	81
1180	Guansaque	81
1181	Siguinque	81
1182	Chirata	81
1183	Altamzal	82
1184	Pavas	82
1185	Boquerón	82
1186	Molino	82
1187	Rosal	82
1188	Centro	82
1189	Uvero	82
1190	Juncal	82
1191	Sisa Medio	82
1192	Sisa Arriba	82
1193	Gaunza	82
1194	Tambor Chico	82
1195	Tambor Grande	82
1196	Jupal	82
1197	Bosque	82
1198	Palo Cado	82
1199	Llano Verde	82
1200	La Palma	82
1201	Los Puentes	82
1202	Loma Gorda	82
1203	Tasvita	82
1204	Nueve Pilas	82
1205	Boqueron	83
1206	Parroquia Vieja	83
1207	Frutillo	83
1208	El Carmen	83
1209	Compromiso	83
1210	La Mesa	83
1211	El Hato	83
1212	Jurpa	83
1213	Centro	83
1214	Choquira	83
1215	Capellania	83
1216	Nerita	83
1217	Puente De Piedra	83
1218	Supata	83
1219	Montoya	83
1220	Matangana	83
1221	Estancia Grande	83
1222	San Jose Del Gacal	83
1223	Bojirque	83
1224	Puente De Boyaca	83
1225	Centro	84
1226	Zona Urbana	84
1227	Naranjos	84
1228	Icarina	84
1229	Pirguata	84
1230	Galindos	84
1231	Parras	84
1232	Caros	84
1233	La Isla	84
1234	Pueblo Viejo	84
1235	Chen	84
\.


--
-- TOC entry 5185 (class 0 OID 0)
-- Dependencies: 261
-- Name: decision_fondo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.decision_fondo_id_seq', 6, true);


--
-- TOC entry 5186 (class 0 OID 0)
-- Dependencies: 263
-- Name: ejecucion_sancion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ejecucion_sancion_id_seq', 3, true);


--
-- TOC entry 5187 (class 0 OID 0)
-- Dependencies: 252
-- Name: etapa_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.etapa_id_seq', 39, true);


--
-- TOC entry 5188 (class 0 OID 0)
-- Dependencies: 260
-- Name: formulacion_cargos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.formulacion_cargos_id_seq', 5, true);


--
-- TOC entry 5189 (class 0 OID 0)
-- Dependencies: 251
-- Name: involucrado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.involucrado_id_seq', 5, true);


--
-- TOC entry 5190 (class 0 OID 0)
-- Dependencies: 255
-- Name: involucrado_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.involucrado_notificacion_id_seq', 43, true);


--
-- TOC entry 5191 (class 0 OID 0)
-- Dependencies: 259
-- Name: ley_1333_2009_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ley_1333_2009_id_seq', 1, true);


--
-- TOC entry 5192 (class 0 OID 0)
-- Dependencies: 237
-- Name: log_auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.log_auditoria_id_seq', 171, true);


--
-- TOC entry 5193 (class 0 OID 0)
-- Dependencies: 257
-- Name: medida_preventiva_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.medida_preventiva_id_seq', 4, true);


--
-- TOC entry 5194 (class 0 OID 0)
-- Dependencies: 245
-- Name: municipio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.municipio_id_seq', 84, true);


--
-- TOC entry 5195 (class 0 OID 0)
-- Dependencies: 243
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 32, true);


--
-- TOC entry 5196 (class 0 OID 0)
-- Dependencies: 235
-- Name: permiso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.permiso_id_seq', 7, true);


--
-- TOC entry 5197 (class 0 OID 0)
-- Dependencies: 254
-- Name: proceso_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.proceso_notificacion_id_seq', 98, true);


--
-- TOC entry 5198 (class 0 OID 0)
-- Dependencies: 248
-- Name: recurso_afectado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.recurso_afectado_id_seq', 3, true);


--
-- TOC entry 5199 (class 0 OID 0)
-- Dependencies: 240
-- Name: rol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rol_id_seq', 11, true);


--
-- TOC entry 5200 (class 0 OID 0)
-- Dependencies: 264
-- Name: tipo_cesacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tipo_cesacion_id_seq', 1, false);


--
-- TOC entry 5201 (class 0 OID 0)
-- Dependencies: 247
-- Name: tipo_etapa_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tipo_etapa_id_seq', 8, true);


--
-- TOC entry 5202 (class 0 OID 0)
-- Dependencies: 256
-- Name: tipo_medida_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tipo_medida_id_seq', 3, true);


--
-- TOC entry 5203 (class 0 OID 0)
-- Dependencies: 253
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tipo_notificacion_id_seq', 15, true);


--
-- TOC entry 5204 (class 0 OID 0)
-- Dependencies: 262
-- Name: tipo_sancion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tipo_sancion_id_seq', 6, true);


--
-- TOC entry 5205 (class 0 OID 0)
-- Dependencies: 246
-- Name: vereda_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vereda_id_seq', 1235, true);


--
-- TOC entry 4916 (class 2606 OID 16815)
-- Name: involucrado actor_externo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado
    ADD CONSTRAINT actor_externo_pkey PRIMARY KEY (id);


--
-- TOC entry 4936 (class 2606 OID 16914)
-- Name: codigos_recuperacion codigos_recuperacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.codigos_recuperacion
    ADD CONSTRAINT codigos_recuperacion_pkey PRIMARY KEY (correo);


--
-- TOC entry 4904 (class 2606 OID 16762)
-- Name: decision_fondo decision_fondo_etapa_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.decision_fondo
    ADD CONSTRAINT decision_fondo_etapa_id_key UNIQUE (etapa_id);


--
-- TOC entry 4906 (class 2606 OID 16758)
-- Name: decision_fondo decision_fondo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.decision_fondo
    ADD CONSTRAINT decision_fondo_pkey PRIMARY KEY (id);


--
-- TOC entry 4908 (class 2606 OID 16779)
-- Name: ejecucion_sancion ejecucion_sancion_etapa_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ejecucion_sancion
    ADD CONSTRAINT ejecucion_sancion_etapa_id_key UNIQUE (etapa_id);


--
-- TOC entry 4910 (class 2606 OID 16777)
-- Name: ejecucion_sancion ejecucion_sancion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ejecucion_sancion
    ADD CONSTRAINT ejecucion_sancion_pkey PRIMARY KEY (id);


--
-- TOC entry 4886 (class 2606 OID 16682)
-- Name: etapa etapa_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.etapa
    ADD CONSTRAINT etapa_pkey PRIMARY KEY (id);


--
-- TOC entry 4879 (class 2606 OID 16661)
-- Name: expediente expediente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_pkey PRIMARY KEY (radicado);


--
-- TOC entry 4948 (class 2606 OID 33456)
-- Name: expediente_recurso expediente_recurso_afectado_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT expediente_recurso_afectado_pkey PRIMARY KEY (expediente_radicado, recurso_id);


--
-- TOC entry 4898 (class 2606 OID 16739)
-- Name: formulacion_cargos formulacion_cargos_etapa_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.formulacion_cargos
    ADD CONSTRAINT formulacion_cargos_etapa_id_key UNIQUE (etapa_id);


--
-- TOC entry 4900 (class 2606 OID 16737)
-- Name: formulacion_cargos formulacion_cargos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.formulacion_cargos
    ADD CONSTRAINT formulacion_cargos_pkey PRIMARY KEY (id);


--
-- TOC entry 4919 (class 2606 OID 49821)
-- Name: involucrado_expediente involucrado_expediente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_expediente
    ADD CONSTRAINT involucrado_expediente_pkey PRIMARY KEY (involucrado_id, expediente_radicado);


--
-- TOC entry 4921 (class 2606 OID 16839)
-- Name: involucrado_notificacion involucrado_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_notificacion
    ADD CONSTRAINT involucrado_notificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4894 (class 2606 OID 16727)
-- Name: ley_1333_2009 ley_1333_2009_etapa_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ley_1333_2009
    ADD CONSTRAINT ley_1333_2009_etapa_id_key UNIQUE (etapa_id);


--
-- TOC entry 4896 (class 2606 OID 16725)
-- Name: ley_1333_2009 ley_1333_2009_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ley_1333_2009
    ADD CONSTRAINT ley_1333_2009_pkey PRIMARY KEY (id);


--
-- TOC entry 4934 (class 2606 OID 16897)
-- Name: log_auditoria log_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log_auditoria
    ADD CONSTRAINT log_auditoria_pkey PRIMARY KEY (id);


--
-- TOC entry 4890 (class 2606 OID 16708)
-- Name: medida_preventiva medida_preventiva_etapa_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_etapa_id_key UNIQUE (etapa_id);


--
-- TOC entry 4892 (class 2606 OID 16706)
-- Name: medida_preventiva medida_preventiva_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_pkey PRIMARY KEY (id);


--
-- TOC entry 4875 (class 2606 OID 16642)
-- Name: municipio municipio_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_pkey PRIMARY KEY (id);


--
-- TOC entry 4944 (class 2606 OID 17046)
-- Name: notificacion_usuario notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion_usuario
    ADD CONSTRAINT notificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4929 (class 2606 OID 16872)
-- Name: permiso permiso_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_nombre_key UNIQUE (nombre);


--
-- TOC entry 4931 (class 2606 OID 16870)
-- Name: permiso permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_pkey PRIMARY KEY (id);


--
-- TOC entry 4914 (class 2606 OID 16798)
-- Name: proceso_notificacion proceso_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proceso_notificacion
    ADD CONSTRAINT proceso_notificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4946 (class 2606 OID 33433)
-- Name: recurso_afectado recurso_afectado_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recurso_afectado
    ADD CONSTRAINT recurso_afectado_pkey PRIMARY KEY (id);


--
-- TOC entry 4938 (class 2606 OID 17004)
-- Name: rol rol_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_nombre_key UNIQUE (nombre);


--
-- TOC entry 4942 (class 2606 OID 17009)
-- Name: rol_permiso rol_permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_pkey PRIMARY KEY (rol_id, permiso_id);


--
-- TOC entry 4940 (class 2606 OID 17002)
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id);


--
-- TOC entry 4951 (class 2606 OID 49867)
-- Name: tipo_cesacion tipo_cesacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_cesacion
    ADD CONSTRAINT tipo_cesacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4902 (class 2606 OID 16751)
-- Name: tipo_sancion tipo_decision_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_sancion
    ADD CONSTRAINT tipo_decision_pkey PRIMARY KEY (id);


--
-- TOC entry 4882 (class 2606 OID 16675)
-- Name: tipo_etapa tipo_etapa_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_etapa
    ADD CONSTRAINT tipo_etapa_nombre_key UNIQUE (nombre);


--
-- TOC entry 4884 (class 2606 OID 16673)
-- Name: tipo_etapa tipo_etapa_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_etapa
    ADD CONSTRAINT tipo_etapa_pkey PRIMARY KEY (id);


--
-- TOC entry 4888 (class 2606 OID 16699)
-- Name: tipo_medida tipo_medida_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_medida
    ADD CONSTRAINT tipo_medida_pkey PRIMARY KEY (id);


--
-- TOC entry 4912 (class 2606 OID 16791)
-- Name: tipo_notificacion tipo_proceso_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_notificacion
    ADD CONSTRAINT tipo_proceso_notificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4923 (class 2606 OID 49910)
-- Name: usuario unique_correo; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT unique_correo UNIQUE (correo);


--
-- TOC entry 4925 (class 2606 OID 16861)
-- Name: usuario usuario_correo_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_correo_key UNIQUE (correo);


--
-- TOC entry 4927 (class 2606 OID 16859)
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (numero_documento);


--
-- TOC entry 4877 (class 2606 OID 16649)
-- Name: vereda vereda_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_pkey PRIMARY KEY (id);


--
-- TOC entry 4880 (class 1259 OID 17035)
-- Name: idx_expediente_encargado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expediente_encargado ON public.expediente USING btree (encargado_id);


--
-- TOC entry 4949 (class 1259 OID 41630)
-- Name: idx_expediente_recurso_radicado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_expediente_recurso_radicado ON public.expediente_recurso USING btree (expediente_radicado);


--
-- TOC entry 4917 (class 1259 OID 41629)
-- Name: idx_involucrado_expediente_radicado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_involucrado_expediente_radicado ON public.involucrado_expediente USING btree (expediente_radicado);


--
-- TOC entry 4932 (class 1259 OID 17036)
-- Name: idx_log_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_log_usuario ON public.log_auditoria USING btree (usuario_id);


--
-- TOC entry 4962 (class 2606 OID 16768)
-- Name: decision_fondo decision_fondo_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.decision_fondo
    ADD CONSTRAINT decision_fondo_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4963 (class 2606 OID 16763)
-- Name: decision_fondo decision_fondo_id_tipo_sancion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.decision_fondo
    ADD CONSTRAINT decision_fondo_id_tipo_sancion_fkey FOREIGN KEY (tipo_sancion_id) REFERENCES public.tipo_sancion(id);


--
-- TOC entry 4964 (class 2606 OID 16780)
-- Name: ejecucion_sancion ejecucion_sancion_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ejecucion_sancion
    ADD CONSTRAINT ejecucion_sancion_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4955 (class 2606 OID 41631)
-- Name: etapa etapa_expediente_radicado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.etapa
    ADD CONSTRAINT etapa_expediente_radicado_fkey FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4956 (class 2606 OID 16688)
-- Name: etapa etapa_tipo_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.etapa
    ADD CONSTRAINT etapa_tipo_etapa_id_fkey FOREIGN KEY (tipo_etapa_id) REFERENCES public.tipo_etapa(id);


--
-- TOC entry 4979 (class 2606 OID 41624)
-- Name: expediente_recurso expediente_recurso_expediente_radicado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT expediente_recurso_expediente_radicado_fkey FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON DELETE CASCADE;


--
-- TOC entry 4953 (class 2606 OID 16662)
-- Name: expediente expediente_vereda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_vereda_id_fkey FOREIGN KEY (vereda_id) REFERENCES public.vereda(id);


--
-- TOC entry 4980 (class 2606 OID 33457)
-- Name: expediente_recurso fk_exp_radicado; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT fk_exp_radicado FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4954 (class 2606 OID 16961)
-- Name: expediente fk_expediente_encargado; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT fk_expediente_encargado FOREIGN KEY (encargado_id) REFERENCES public.usuario(numero_documento) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 4981 (class 2606 OID 33462)
-- Name: expediente_recurso fk_recurso; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expediente_recurso
    ADD CONSTRAINT fk_recurso FOREIGN KEY (recurso_id) REFERENCES public.recurso_afectado(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4959 (class 2606 OID 49873)
-- Name: ley_1333_2009 fk_tipo_cesacion; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ley_1333_2009
    ADD CONSTRAINT fk_tipo_cesacion FOREIGN KEY (tipo_cesacion_id) REFERENCES public.tipo_cesacion(id);


--
-- TOC entry 4965 (class 2606 OID 49827)
-- Name: tipo_notificacion fk_tipo_notificacion_tipo_etapa; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tipo_notificacion
    ADD CONSTRAINT fk_tipo_notificacion_tipo_etapa FOREIGN KEY (tipo_etapa_id) REFERENCES public.tipo_etapa(id);


--
-- TOC entry 4977 (class 2606 OID 17047)
-- Name: notificacion_usuario fk_usuario; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion_usuario
    ADD CONSTRAINT fk_usuario FOREIGN KEY (numero_documento) REFERENCES public.usuario(numero_documento) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4972 (class 2606 OID 25235)
-- Name: usuario fk_usuario_rol; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES public.rol(id);


--
-- TOC entry 4961 (class 2606 OID 16740)
-- Name: formulacion_cargos formulacion_cargos_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.formulacion_cargos
    ADD CONSTRAINT formulacion_cargos_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4968 (class 2606 OID 49822)
-- Name: involucrado_expediente involucrado_expediente_expediente_radicado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_expediente
    ADD CONSTRAINT involucrado_expediente_expediente_radicado_fkey FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON UPDATE CASCADE;


--
-- TOC entry 4969 (class 2606 OID 41619)
-- Name: involucrado_expediente involucrado_expediente_involucrado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_expediente
    ADD CONSTRAINT involucrado_expediente_involucrado_id_fkey FOREIGN KEY (involucrado_id) REFERENCES public.involucrado(id) ON DELETE CASCADE;


--
-- TOC entry 4970 (class 2606 OID 16845)
-- Name: involucrado_notificacion involucrado_notificacion_involucrado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_notificacion
    ADD CONSTRAINT involucrado_notificacion_involucrado_id_fkey FOREIGN KEY (involucrado_id) REFERENCES public.involucrado(id);


--
-- TOC entry 4971 (class 2606 OID 16840)
-- Name: involucrado_notificacion involucrado_notificacion_notificacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.involucrado_notificacion
    ADD CONSTRAINT involucrado_notificacion_notificacion_id_fkey FOREIGN KEY (proceso_notificacion_id) REFERENCES public.proceso_notificacion(id);


--
-- TOC entry 4960 (class 2606 OID 16728)
-- Name: ley_1333_2009 ley_1333_2009_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ley_1333_2009
    ADD CONSTRAINT ley_1333_2009_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4973 (class 2606 OID 41636)
-- Name: log_auditoria log_auditoria_expediente_radicado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log_auditoria
    ADD CONSTRAINT log_auditoria_expediente_radicado_fkey FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4974 (class 2606 OID 16972)
-- Name: log_auditoria log_auditoria_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log_auditoria
    ADD CONSTRAINT log_auditoria_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(numero_documento);


--
-- TOC entry 4957 (class 2606 OID 16714)
-- Name: medida_preventiva medida_preventiva_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4958 (class 2606 OID 16709)
-- Name: medida_preventiva medida_preventiva_id_tipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.medida_preventiva
    ADD CONSTRAINT medida_preventiva_id_tipo_fkey FOREIGN KEY (id_tipo) REFERENCES public.tipo_medida(id);


--
-- TOC entry 4978 (class 2606 OID 41641)
-- Name: notificacion_usuario notificacion_expediente_radicado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion_usuario
    ADD CONSTRAINT notificacion_expediente_radicado_fkey FOREIGN KEY (expediente_radicado) REFERENCES public.expediente(radicado) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4966 (class 2606 OID 16799)
-- Name: proceso_notificacion proceso_notificacion_etapa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proceso_notificacion
    ADD CONSTRAINT proceso_notificacion_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES public.etapa(id);


--
-- TOC entry 4967 (class 2606 OID 16804)
-- Name: proceso_notificacion proceso_notificacion_tipo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proceso_notificacion
    ADD CONSTRAINT proceso_notificacion_tipo_id_fkey FOREIGN KEY (tipo_id) REFERENCES public.tipo_notificacion(id);


--
-- TOC entry 4975 (class 2606 OID 17015)
-- Name: rol_permiso rol_permiso_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permiso(id) ON DELETE CASCADE;


--
-- TOC entry 4976 (class 2606 OID 17010)
-- Name: rol_permiso rol_permiso_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id) ON DELETE CASCADE;


--
-- TOC entry 4952 (class 2606 OID 16650)
-- Name: vereda vereda_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipio(id);


-- Completed on 2025-10-08 04:28:21

--
-- PostgreSQL database dump complete
--

