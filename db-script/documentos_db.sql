-- ============================================================
-- documentos_db — esquema y datos iniciales de app-docs
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb documentos_db && psql -U postgres -d documentos_db -f documentos_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict Mm6ePlqpXeSNGRRWtvm3fxvnUmRLvRpVK4wgN3ARQtkKqXkDq8wYhUMkTal4J0V


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
-- Name: asignaciones_revisores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asignaciones_revisores (
    id integer NOT NULL,
    revisor_id integer NOT NULL,
    fecha_asignacion timestamp with time zone NOT NULL,
    notificado boolean NOT NULL,
    documento_id integer NOT NULL
);


--
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asignaciones_revisores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asignaciones_revisores_id_seq OWNED BY public.asignaciones_revisores.id;


--
-- Name: auditoria_documentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auditoria_documentos (
    ip_address character varying(45),
    id integer NOT NULL,
    accion character varying(50) NOT NULL,
    usuario_id integer,
    descripcion text,
    datos_adicionales json,
    fecha_accion timestamp with time zone NOT NULL,
    documento_id integer NOT NULL
);


--
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auditoria_documentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auditoria_documentos_id_seq OWNED BY public.auditoria_documentos.id;


--
-- Name: documentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos (
    estado character varying(20) NOT NULL,
    usuario_creador_id integer NOT NULL,
    tipo_archivo character varying(10),
    id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    descripcion text,
    version_actual integer NOT NULL,
    numero_devoluciones integer NOT NULL,
    fecha_creacion timestamp with time zone NOT NULL,
    fecha_ultima_actualizacion timestamp with time zone NOT NULL
);


--
-- Name: documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentos_id_seq OWNED BY public.documentos.id;


--
-- Name: file_hash; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file_hash (
    id integer NOT NULL,
    file_hash character varying(64) NOT NULL,
    file_url text NOT NULL,
    content_type character varying(100),
    file_size integer,
    numero_usos integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: file_hash_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.file_hash_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: file_hash_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.file_hash_id_seq OWNED BY public.file_hash.id;


--
-- Name: revisiones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.revisiones (
    estado_revision character varying(20) NOT NULL,
    archivo_adjunto_url character varying(500),
    archivo_adjunto_nombre character varying(255),
    id integer NOT NULL,
    version_revisada integer NOT NULL,
    revisor_id integer NOT NULL,
    comentarios text,
    adjunto_file_id integer,
    adjunto_size bigint,
    fecha_revision timestamp with time zone NOT NULL,
    documento_id integer NOT NULL
);


--
-- Name: revisiones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.revisiones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: revisiones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.revisiones_id_seq OWNED BY public.revisiones.id;


--
-- Name: versiones_documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.versiones_documento (
    archivo_nombre_original character varying(255) NOT NULL,
    id integer NOT NULL,
    numero_version integer NOT NULL,
    file_id integer,
    archivo_url character varying(500) NOT NULL,
    archivo_size bigint,
    usuario_subida_id integer NOT NULL,
    comentario text,
    fecha_subida timestamp with time zone NOT NULL,
    documento_id integer NOT NULL
);


--
-- Name: versiones_documento_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.versiones_documento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: versiones_documento_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.versiones_documento_id_seq OWNED BY public.versiones_documento.id;


--
-- Name: vista_documentos_detalle; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vista_documentos_detalle AS
 SELECT d.id,
    d.nombre,
    d.descripcion,
    d.tipo_archivo,
    d.estado,
    d.version_actual,
    d.numero_devoluciones,
    d.usuario_creador_id AS creador_id,
    d.fecha_creacion,
    d.fecha_ultima_actualizacion,
    COALESCE(rev_count.total_revisiones, (0)::bigint) AS total_revisiones,
    COALESCE(asig_count.total_revisores, (0)::bigint) AS total_revisores
   FROM ((public.documentos d
     LEFT JOIN ( SELECT revisiones.documento_id,
            count(*) AS total_revisiones
           FROM public.revisiones
          GROUP BY revisiones.documento_id) rev_count ON ((rev_count.documento_id = d.id)))
     LEFT JOIN ( SELECT asignaciones_revisores.documento_id,
            count(*) AS total_revisores
           FROM public.asignaciones_revisores
          GROUP BY asignaciones_revisores.documento_id) asig_count ON ((asig_count.documento_id = d.id)));


--
-- Name: asignaciones_revisores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asignaciones_revisores ALTER COLUMN id SET DEFAULT nextval('public.asignaciones_revisores_id_seq'::regclass);


--
-- Name: auditoria_documentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_documentos ALTER COLUMN id SET DEFAULT nextval('public.auditoria_documentos_id_seq'::regclass);


--
-- Name: documentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos ALTER COLUMN id SET DEFAULT nextval('public.documentos_id_seq'::regclass);


--
-- Name: file_hash id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_hash ALTER COLUMN id SET DEFAULT nextval('public.file_hash_id_seq'::regclass);


--
-- Name: revisiones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.revisiones ALTER COLUMN id SET DEFAULT nextval('public.revisiones_id_seq'::regclass);


--
-- Name: versiones_documento id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.versiones_documento ALTER COLUMN id SET DEFAULT nextval('public.versiones_documento_id_seq'::regclass);


--
-- Data for Name: asignaciones_revisores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.asignaciones_revisores (id, revisor_id, fecha_asignacion, notificado, documento_id) FROM stdin;
\.


--
-- Data for Name: auditoria_documentos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auditoria_documentos (ip_address, id, accion, usuario_id, descripcion, datos_adicionales, fecha_accion, documento_id) FROM stdin;
\.


--
-- Data for Name: documentos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documentos (estado, usuario_creador_id, tipo_archivo, id, nombre, descripcion, version_actual, numero_devoluciones, fecha_creacion, fecha_ultima_actualizacion) FROM stdin;
\.


--
-- Data for Name: file_hash; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.file_hash (id, file_hash, file_url, content_type, file_size, numero_usos, created_at) FROM stdin;
\.


--
-- Data for Name: revisiones; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.revisiones (estado_revision, archivo_adjunto_url, archivo_adjunto_nombre, id, version_revisada, revisor_id, comentarios, adjunto_file_id, adjunto_size, fecha_revision, documento_id) FROM stdin;
\.


--
-- Data for Name: versiones_documento; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.versiones_documento (archivo_nombre_original, id, numero_version, file_id, archivo_url, archivo_size, usuario_subida_id, comentario, fecha_subida, documento_id) FROM stdin;
\.


--
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.asignaciones_revisores_id_seq', 1, false);


--
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auditoria_documentos_id_seq', 1, false);


--
-- Name: documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documentos_id_seq', 1, false);


--
-- Name: file_hash_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.file_hash_id_seq', 1, false);


--
-- Name: revisiones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.revisiones_id_seq', 1, false);


--
-- Name: versiones_documento_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.versiones_documento_id_seq', 1, false);


--
-- Name: asignaciones_revisores asignaciones_revisores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asignaciones_revisores
    ADD CONSTRAINT asignaciones_revisores_pkey PRIMARY KEY (id);


--
-- Name: auditoria_documentos auditoria_documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_documentos
    ADD CONSTRAINT auditoria_documentos_pkey PRIMARY KEY (id);


--
-- Name: documentos documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_pkey PRIMARY KEY (id);


--
-- Name: file_hash file_hash_file_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_hash
    ADD CONSTRAINT file_hash_file_hash_key UNIQUE (file_hash);


--
-- Name: file_hash file_hash_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_hash
    ADD CONSTRAINT file_hash_pkey PRIMARY KEY (id);


--
-- Name: revisiones revisiones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.revisiones
    ADD CONSTRAINT revisiones_pkey PRIMARY KEY (id);


--
-- Name: versiones_documento versiones_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.versiones_documento
    ADD CONSTRAINT versiones_documento_pkey PRIMARY KEY (id);


--
-- Name: ix_asignaciones_revisores_documento_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_asignaciones_revisores_documento_id ON public.asignaciones_revisores USING btree (documento_id);


--
-- Name: ix_asignaciones_revisores_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_asignaciones_revisores_revisor_id ON public.asignaciones_revisores USING btree (revisor_id);


--
-- Name: ix_auditoria_documentos_documento_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_documentos_documento_id ON public.auditoria_documentos USING btree (documento_id);


--
-- Name: ix_documentos_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_estado ON public.documentos USING btree (estado);


--
-- Name: ix_documentos_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_fecha_creacion ON public.documentos USING btree (fecha_creacion);


--
-- Name: ix_documentos_usuario_creador_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_usuario_creador_id ON public.documentos USING btree (usuario_creador_id);


--
-- Name: ix_revisiones_documento_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_revisiones_documento_id ON public.revisiones USING btree (documento_id);


--
-- Name: ix_revisiones_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_revisiones_revisor_id ON public.revisiones USING btree (revisor_id);


--
-- Name: ix_versiones_documento_documento_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_versiones_documento_documento_id ON public.versiones_documento USING btree (documento_id);


--
-- Name: ix_versiones_documento_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_versiones_documento_file_id ON public.versiones_documento USING btree (file_id);


--
-- Name: asignaciones_revisores asignaciones_revisores_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asignaciones_revisores
    ADD CONSTRAINT asignaciones_revisores_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- Name: auditoria_documentos auditoria_documentos_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_documentos
    ADD CONSTRAINT auditoria_documentos_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- Name: revisiones revisiones_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.revisiones
    ADD CONSTRAINT revisiones_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- Name: versiones_documento versiones_documento_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.versiones_documento
    ADD CONSTRAINT versiones_documento_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Mm6ePlqpXeSNGRRWtvm3fxvnUmRLvRpVK4wgN3ARQtkKqXkDq8wYhUMkTal4J0V

