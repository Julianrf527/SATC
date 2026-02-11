--
-- PostgreSQL database dump
--

\restrict bzcpPsRPAqP3kghIkY9kw58qYtCFiLDtR0920hEtEIb8wFWKLE9AsJ1UIx0nruM

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2026-02-10 09:11:38

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

--
-- TOC entry 230 (class 1255 OID 17751)
-- Name: registrar_auditoria(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.registrar_auditoria() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO auditoria_documentos (documento_id, usuario_id, accion, descripcion)
        VALUES (NEW.id, NEW.usuario_creador_id, 'crear', 'Documento creado');
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.estado <> NEW.estado THEN
            INSERT INTO auditoria_documentos (documento_id, usuario_id, accion, descripcion)
            VALUES (NEW.id, NEW.usuario_creador_id,
                CASE 
                    WHEN NEW.estado = 'aprobado' THEN 'aprobar'
                    WHEN NEW.estado = 'rechazado' THEN 'devolver'
                    WHEN NEW.estado = 'finalizado' THEN 'finalizar'
                    ELSE 'actualizar'
                END,
                'Estado cambiado de ' || OLD.estado || ' a ' || NEW.estado);
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.registrar_auditoria() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 17752)
-- Name: asignaciones_revisores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asignaciones_revisores (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    revisor_id integer NOT NULL,
    fecha_asignacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    notificado boolean DEFAULT false
);


ALTER TABLE public.asignaciones_revisores OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 17760)
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.asignaciones_revisores ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.asignaciones_revisores_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 17761)
-- Name: auditoria_documentos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auditoria_documentos (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    usuario_id integer NOT NULL,
    accion character varying(50) NOT NULL,
    descripcion text,
    datos_adicionales jsonb,
    fecha_accion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ip_address character varying(45)
);


ALTER TABLE public.auditoria_documentos OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 17771)
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auditoria_documentos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.auditoria_documentos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 17772)
-- Name: documentos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documentos (
    id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    descripcion text,
    tipo_archivo character varying(10) NOT NULL,
    usuario_creador_id integer NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    estado character varying(20) DEFAULT 'en_revision'::character varying NOT NULL,
    version_actual integer DEFAULT 1,
    numero_devoluciones integer DEFAULT 0,
    fecha_ultima_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT documentos_estado_check CHECK (((estado)::text = ANY (ARRAY[('en_revision'::character varying)::text, ('aprobado'::character varying)::text, ('rechazado'::character varying)::text, ('finalizado'::character varying)::text]))),
    CONSTRAINT documentos_tipo_archivo_check CHECK (((tipo_archivo)::text = ANY (ARRAY[('pdf'::character varying)::text, ('docx'::character varying)::text, ('doc'::character varying)::text]))),
    CONSTRAINT max_devoluciones CHECK ((numero_devoluciones <= 3))
);


ALTER TABLE public.documentos OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 17790)
-- Name: documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.documentos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.documentos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 225 (class 1259 OID 17791)
-- Name: revisiones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.revisiones (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    version_revisada integer NOT NULL,
    revisor_id integer NOT NULL,
    estado_revision character varying(20) NOT NULL,
    comentarios text,
    fecha_revision timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT revisiones_estado_revision_check CHECK (((estado_revision)::text = ANY (ARRAY[('aprobado'::character varying)::text, ('devuelto'::character varying)::text])))
);


ALTER TABLE public.revisiones OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 17803)
-- Name: revisiones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.revisiones ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.revisiones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 227 (class 1259 OID 17804)
-- Name: versiones_documento; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.versiones_documento (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    numero_version integer NOT NULL,
    archivo_url character varying(500) NOT NULL,
    archivo_nombre_original character varying(255) NOT NULL,
    archivo_size bigint,
    usuario_subida_id integer NOT NULL,
    fecha_subida timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    comentario text
);


ALTER TABLE public.versiones_documento OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 17816)
-- Name: versiones_documento_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.versiones_documento ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.versiones_documento_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 229 (class 1259 OID 17817)
-- Name: vista_documentos_detalle; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vista_documentos_detalle AS
 SELECT d.id,
    d.id AS documento_id,
    d.nombre,
    d.descripcion,
    d.tipo_archivo,
    d.estado,
    d.version_actual,
    d.numero_devoluciones,
    d.usuario_creador_id,
    d.fecha_creacion,
    d.fecha_ultima_actualizacion,
    COALESCE(count(DISTINCT r.id), (0)::bigint) AS total_revisiones,
    COALESCE(count(DISTINCT ar.revisor_id), (0)::bigint) AS total_revisores,
    vd.id AS version_id,
    vd.numero_version,
    vd.archivo_url,
    vd.archivo_nombre_original AS archivo_nombre,
    vd.archivo_size,
    vd.fecha_subida,
    vd.comentario,
    r.id AS revision_id,
    r.revisor_id,
    r.estado_revision,
    r.comentarios,
    r.fecha_revision,
    r.version_revisada,
    ar.fecha_asignacion,
    ar.notificado,
    ad.id AS auditoria_id,
    ad.usuario_id,
    ad.accion,
    ad.descripcion AS descripcion_auditoria,
    ad.fecha_accion
   FROM ((((public.documentos d
     LEFT JOIN public.versiones_documento vd ON (((vd.documento_id = d.id) AND (vd.numero_version = d.version_actual))))
     LEFT JOIN public.revisiones r ON ((r.documento_id = d.id)))
     LEFT JOIN public.asignaciones_revisores ar ON ((ar.documento_id = d.id)))
     LEFT JOIN public.auditoria_documentos ad ON (((ad.documento_id = d.id) AND (ad.id = ( SELECT max(auditoria_documentos.id) AS max
           FROM public.auditoria_documentos
          WHERE (auditoria_documentos.documento_id = d.id))))))
  GROUP BY d.id, d.nombre, d.descripcion, d.tipo_archivo, d.estado, d.version_actual, d.numero_devoluciones, d.usuario_creador_id, d.fecha_creacion, d.fecha_ultima_actualizacion, vd.id, vd.numero_version, vd.archivo_url, vd.archivo_nombre_original, vd.archivo_size, vd.fecha_subida, vd.comentario, r.id, r.revisor_id, r.estado_revision, r.comentarios, r.fecha_revision, r.version_revisada, ar.fecha_asignacion, ar.notificado, ad.id, ad.usuario_id, ad.accion, ad.descripcion, ad.fecha_accion;


ALTER VIEW public.vista_documentos_detalle OWNER TO postgres;

--
-- TOC entry 5086 (class 0 OID 17752)
-- Dependencies: 219
-- Data for Name: asignaciones_revisores; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asignaciones_revisores (id, documento_id, revisor_id, fecha_asignacion, notificado) FROM stdin;
12	16	1233506796	2025-12-07 21:32:01.453659	t
13	17	1233506796	2025-12-11 11:01:52.894003	t
14	18	1233506796	2025-12-11 11:09:45.550225	t
\.


--
-- TOC entry 5088 (class 0 OID 17761)
-- Dependencies: 221
-- Data for Name: auditoria_documentos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auditoria_documentos (id, documento_id, usuario_id, accion, descripcion, datos_adicionales, fecha_accion, ip_address) FROM stdin;
55	16	1233506795	crear	Documento creado	\N	2025-12-07 21:32:00.282006	\N
56	16	1233506795	crear	Documento creado con 1 revisor(es)	{"revisores": [1233506796]}	2025-12-07 21:32:01.465238	\N
57	16	1233506795	devolver	Estado cambiado de en_revision a rechazado	\N	2025-12-07 21:33:17.396092	\N
58	16	1233506796	devolver	Estado cambiado de en_revision a rechazado, rechazos 1/3	{"version": 1, "comentarios": "No cumple con x criterios"}	2025-12-07 21:33:18.363865	\N
59	16	1233506795	actualizar	Estado cambiado de rechazado a en_revision	\N	2025-12-07 21:35:04.298216	\N
60	16	1233506795	aprobar	Estado cambiado de en_revision a aprobado	\N	2025-12-07 21:35:40.546589	\N
61	16	1233506796	aprobar	Documento aprobado exitosamente	{"version": 2, "comentarios": "Aprobado"}	2025-12-07 21:35:41.763196	\N
62	17	1233506795	crear	Documento creado	\N	2025-12-11 11:01:51.80451	\N
63	17	1233506795	crear	Documento creado con 1 revisor(es)	{"revisores": [1233506796]}	2025-12-11 11:01:52.900243	\N
64	17	1233506795	devolver	Estado cambiado de en_revision a rechazado	\N	2025-12-11 11:03:12.123854	\N
65	17	1233506796	devolver	Estado cambiado de en_revision a rechazado, rechazos 1/3	{"version": 1, "comentarios": "Falto una firma"}	2025-12-11 11:03:13.136841	\N
66	17	1233506795	actualizar	Estado cambiado de rechazado a en_revision	\N	2025-12-11 11:04:20.626414	\N
67	17	1233506795	devolver	Estado cambiado de en_revision a rechazado	\N	2025-12-11 11:05:03.040281	\N
68	17	1233506796	devolver	Estado cambiado de en_revision a rechazado, rechazos 2/3	{"version": 2, "comentarios": "Falto x"}	2025-12-11 11:05:03.812221	\N
69	17	1233506795	actualizar	Estado cambiado de rechazado a en_revision	\N	2025-12-11 11:05:52.078102	\N
70	17	1233506795	finalizar	Estado cambiado de en_revision a finalizado	\N	2025-12-11 11:06:26.635194	\N
71	17	1233506796	finalizar	Documento finalizado tras 3 devoluciones	{"version": 3, "comentarios": "Falto x"}	2025-12-11 11:06:27.394445	\N
72	18	1233506795	crear	Documento creado	\N	2025-12-11 11:09:44.762533	\N
73	18	1233506795	crear	Documento creado con 1 revisor(es)	{"revisores": [1233506796]}	2025-12-11 11:09:45.552148	\N
74	18	1233506795	aprobar	Estado cambiado de en_revision a aprobado	\N	2025-12-11 11:10:05.824439	\N
75	18	1233506796	aprobar	Documento aprobado exitosamente	{"version": 1, "comentarios": "Bien"}	2025-12-11 11:10:06.674938	\N
\.


--
-- TOC entry 5090 (class 0 OID 17772)
-- Dependencies: 223
-- Data for Name: documentos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documentos (id, nombre, descripcion, tipo_archivo, usuario_creador_id, fecha_creacion, estado, version_actual, numero_devoluciones, fecha_ultima_actualizacion) FROM stdin;
16	Contrato X	Este documetno x	pdf	1233506795	2025-12-07 21:32:00.281547	aprobado	2	1	2025-12-07 21:35:41.753039
17	Notificaicon	\N	pdf	1233506795	2025-12-11 11:01:51.804015	finalizado	3	3	2025-12-11 11:06:27.38784
18	Comunicacion	\N	pdf	1233506795	2025-12-11 11:09:44.762209	aprobado	1	0	2025-12-11 11:10:06.671109
\.


--
-- TOC entry 5092 (class 0 OID 17791)
-- Dependencies: 225
-- Data for Name: revisiones; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.revisiones (id, documento_id, version_revisada, revisor_id, estado_revision, comentarios, fecha_revision) FROM stdin;
8	16	1	1233506796	devuelto	No cumple con x criterios	2025-12-07 21:33:18.368412
9	16	2	1233506796	aprobado	Aprobado	2025-12-07 21:35:41.766556
10	17	1	1233506796	devuelto	Falto una firma	2025-12-11 11:03:13.140193
11	17	2	1233506796	devuelto	Falto x	2025-12-11 11:05:03.813273
12	17	3	1233506796	devuelto	Falto x	2025-12-11 11:06:27.396868
13	18	1	1233506796	aprobado	Bien	2025-12-11 11:10:06.675945
\.


--
-- TOC entry 5094 (class 0 OID 17804)
-- Dependencies: 227
-- Data for Name: versiones_documento; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.versiones_documento (id, documento_id, numero_version, archivo_url, archivo_nombre_original, archivo_size, usuario_subida_id, fecha_subida, comentario) FROM stdin;
16	16	1	uploads/documentos\\20251207_213200_Propuesta Solución.pdf	Propuesta Solución.pdf	2970609	1233506795	2025-12-07 21:32:01.476845	Versión inicial
17	16	2	uploads/documentos\\20251207_213504_imc3smdnx08py-parcial-2-discretas-ii-pdf-application-pdf (1).pdf	imc3smdnx08py-parcial-2-discretas-ii-pdf-application-pdf (1).pdf	335317	1233506795	2025-12-07 21:35:04.3238	Corregido x cosas
18	17	1	uploads/documentos\\20251211_110151_hoja_77_hoja_95.pdf	hoja_77_hoja_95.pdf	9990883	1233506795	2025-12-11 11:01:52.926588	Versión inicial
19	17	2	uploads/documentos\\20251211_110420_hoja_77_hoja_95.pdf	hoja_77_hoja_95.pdf	9990883	1233506795	2025-12-11 11:04:20.67099	Cambios realizados
20	17	3	uploads/documentos\\20251211_110552_hoja_5_hoja_10.pdf	hoja_5_hoja_10.pdf	2508428	1233506795	2025-12-11 11:05:52.093673	x
21	18	1	uploads/documentos\\20251211_110944_hoja_206_hoja_208.pdf	hoja_206_hoja_208.pdf	818764	1233506795	2025-12-11 11:09:45.552983	Versión inicial
\.


--
-- TOC entry 5101 (class 0 OID 0)
-- Dependencies: 220
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asignaciones_revisores_id_seq', 14, true);


--
-- TOC entry 5102 (class 0 OID 0)
-- Dependencies: 222
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auditoria_documentos_id_seq', 75, true);


--
-- TOC entry 5103 (class 0 OID 0)
-- Dependencies: 224
-- Name: documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.documentos_id_seq', 18, true);


--
-- TOC entry 5104 (class 0 OID 0)
-- Dependencies: 226
-- Name: revisiones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.revisiones_id_seq', 13, true);


--
-- TOC entry 5105 (class 0 OID 0)
-- Dependencies: 228
-- Name: versiones_documento_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.versiones_documento_id_seq', 21, true);


--
-- TOC entry 4896 (class 2606 OID 17823)
-- Name: asignaciones_revisores asignaciones_revisores_documento_id_revisor_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asignaciones_revisores
    ADD CONSTRAINT asignaciones_revisores_documento_id_revisor_id_key UNIQUE (documento_id, revisor_id);


--
-- TOC entry 4898 (class 2606 OID 17825)
-- Name: asignaciones_revisores asignaciones_revisores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asignaciones_revisores
    ADD CONSTRAINT asignaciones_revisores_pkey PRIMARY KEY (id);


--
-- TOC entry 4903 (class 2606 OID 17827)
-- Name: auditoria_documentos auditoria_documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditoria_documentos
    ADD CONSTRAINT auditoria_documentos_pkey PRIMARY KEY (id);


--
-- TOC entry 4910 (class 2606 OID 17829)
-- Name: documentos documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_pkey PRIMARY KEY (id);


--
-- TOC entry 4925 (class 2606 OID 17831)
-- Name: revisiones revisiones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revisiones
    ADD CONSTRAINT revisiones_pkey PRIMARY KEY (id);


--
-- TOC entry 4930 (class 2606 OID 17833)
-- Name: versiones_documento versiones_documento_documento_id_numero_version_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.versiones_documento
    ADD CONSTRAINT versiones_documento_documento_id_numero_version_key UNIQUE (documento_id, numero_version);


--
-- TOC entry 4932 (class 2606 OID 17835)
-- Name: versiones_documento versiones_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.versiones_documento
    ADD CONSTRAINT versiones_documento_pkey PRIMARY KEY (id);


--
-- TOC entry 4899 (class 1259 OID 17836)
-- Name: idx_asignaciones_documento; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asignaciones_documento ON public.asignaciones_revisores USING btree (documento_id);


--
-- TOC entry 4900 (class 1259 OID 17837)
-- Name: idx_asignaciones_revisor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asignaciones_revisor ON public.asignaciones_revisores USING btree (revisor_id);


--
-- TOC entry 4901 (class 1259 OID 17838)
-- Name: idx_asignaciones_revisor_documento; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asignaciones_revisor_documento ON public.asignaciones_revisores USING btree (revisor_id, documento_id);


--
-- TOC entry 4904 (class 1259 OID 17839)
-- Name: idx_auditoria_accion; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auditoria_accion ON public.auditoria_documentos USING btree (accion);


--
-- TOC entry 4905 (class 1259 OID 17840)
-- Name: idx_auditoria_documento; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auditoria_documento ON public.auditoria_documentos USING btree (documento_id);


--
-- TOC entry 4906 (class 1259 OID 17841)
-- Name: idx_auditoria_documento_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auditoria_documento_fecha ON public.auditoria_documentos USING btree (documento_id, fecha_accion);


--
-- TOC entry 4907 (class 1259 OID 17842)
-- Name: idx_auditoria_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auditoria_fecha ON public.auditoria_documentos USING btree (fecha_accion DESC);


--
-- TOC entry 4908 (class 1259 OID 17843)
-- Name: idx_auditoria_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_auditoria_usuario ON public.auditoria_documentos USING btree (usuario_id);


--
-- TOC entry 4911 (class 1259 OID 17844)
-- Name: idx_documentos_creador; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_creador ON public.documentos USING btree (usuario_creador_id);


--
-- TOC entry 4912 (class 1259 OID 17845)
-- Name: idx_documentos_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_estado ON public.documentos USING btree (estado);


--
-- TOC entry 4913 (class 1259 OID 17846)
-- Name: idx_documentos_estado_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_estado_fecha ON public.documentos USING btree (estado, fecha_creacion DESC);


--
-- TOC entry 4914 (class 1259 OID 17847)
-- Name: idx_documentos_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_fecha ON public.documentos USING btree (fecha_creacion DESC);


--
-- TOC entry 4915 (class 1259 OID 17848)
-- Name: idx_documentos_fecha_creacion; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_fecha_creacion ON public.documentos USING btree (fecha_creacion DESC);


--
-- TOC entry 4916 (class 1259 OID 17849)
-- Name: idx_documentos_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_usuario ON public.documentos USING btree (usuario_creador_id);


--
-- TOC entry 4917 (class 1259 OID 17850)
-- Name: idx_documentos_usuario_creador; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_usuario_creador ON public.documentos USING btree (usuario_creador_id);


--
-- TOC entry 4918 (class 1259 OID 17851)
-- Name: idx_documentos_usuario_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documentos_usuario_estado ON public.documentos USING btree (usuario_creador_id, estado);


--
-- TOC entry 4919 (class 1259 OID 17852)
-- Name: idx_revisiones_documento; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_revisiones_documento ON public.revisiones USING btree (documento_id);


--
-- TOC entry 4920 (class 1259 OID 17853)
-- Name: idx_revisiones_documento_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_revisiones_documento_fecha ON public.revisiones USING btree (documento_id, fecha_revision DESC);


--
-- TOC entry 4921 (class 1259 OID 17854)
-- Name: idx_revisiones_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_revisiones_estado ON public.revisiones USING btree (estado_revision);


--
-- TOC entry 4922 (class 1259 OID 17855)
-- Name: idx_revisiones_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_revisiones_fecha ON public.revisiones USING btree (fecha_revision DESC);


--
-- TOC entry 4923 (class 1259 OID 17856)
-- Name: idx_revisiones_revisor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_revisiones_revisor ON public.revisiones USING btree (revisor_id);


--
-- TOC entry 4926 (class 1259 OID 17857)
-- Name: idx_versiones_documento; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_versiones_documento ON public.versiones_documento USING btree (documento_id);


--
-- TOC entry 4927 (class 1259 OID 17858)
-- Name: idx_versiones_documento_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_versiones_documento_id ON public.versiones_documento USING btree (documento_id);


--
-- TOC entry 4928 (class 1259 OID 17859)
-- Name: idx_versiones_documento_numero; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_versiones_documento_numero ON public.versiones_documento USING btree (documento_id, numero_version DESC);


--
-- TOC entry 4937 (class 2620 OID 17860)
-- Name: documentos trigger_auditoria_documentos; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_auditoria_documentos AFTER INSERT OR UPDATE ON public.documentos FOR EACH ROW EXECUTE FUNCTION public.registrar_auditoria();


--
-- TOC entry 4933 (class 2606 OID 17861)
-- Name: asignaciones_revisores asignaciones_revisores_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asignaciones_revisores
    ADD CONSTRAINT asignaciones_revisores_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- TOC entry 4934 (class 2606 OID 17866)
-- Name: auditoria_documentos auditoria_documentos_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditoria_documentos
    ADD CONSTRAINT auditoria_documentos_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- TOC entry 4935 (class 2606 OID 17871)
-- Name: revisiones revisiones_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revisiones
    ADD CONSTRAINT revisiones_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


--
-- TOC entry 4936 (class 2606 OID 17876)
-- Name: versiones_documento versiones_documento_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.versiones_documento
    ADD CONSTRAINT versiones_documento_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos(id) ON DELETE CASCADE;


-- Completed on 2026-02-10 09:11:38

--
-- PostgreSQL database dump complete
--

\unrestrict bzcpPsRPAqP3kghIkY9kw58qYtCFiLDtR0920hEtEIb8wFWKLE9AsJ1UIx0nruM

