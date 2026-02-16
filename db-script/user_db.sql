--
-- PostgreSQL database dump
--

\restrict w7jesmkYhwI3cBMdbJwu8f5cLeaLxPzAUKQteex40Ausiky1S7VQeRlLkm101so

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2026-02-10 09:12:08

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
-- SET transaction_timeout = 0;  -- Comentado: requiere PostgreSQL 17+, contenedor usa PG 15
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
-- TOC entry 219 (class 1259 OID 18287)
-- Name: auditoria; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auditoria (
    id integer NOT NULL,
    tabla_afectada character varying(30),
    id_registro character varying(20),
    tipo_operacion character varying(10) NOT NULL,
    usuario_id bigint,
    fecha timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    descripcion text,
    datos_anteriores json,
    datos_nuevos json
);


ALTER TABLE public.auditoria OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 18295)
-- Name: auditoria_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auditoria ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.auditoria_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 18296)
-- Name: codigo_recuperacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.codigo_recuperacion (
    codigo character varying(60),
    fecha_expiracion timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    usuario_id bigint,
    id integer NOT NULL
);


ALTER TABLE public.codigo_recuperacion OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 18301)
-- Name: codigo_recuperacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.codigo_recuperacion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.codigo_recuperacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 18302)
-- Name: notificacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notificacion (
    id integer NOT NULL,
    mensaje text NOT NULL,
    id_vinculada character varying(20),
    usuario_id bigint,
    fecha_creacion timestamp with time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Bogota'::text),
    tipo character varying(15)
);


ALTER TABLE public.notificacion OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 18310)
-- Name: notificacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.notificacion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.notificacion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 225 (class 1259 OID 18311)
-- Name: permiso; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permiso (
    id integer NOT NULL,
    nombre character varying(40) NOT NULL,
    menu_path character varying(50)
);


ALTER TABLE public.permiso OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 18316)
-- Name: permiso_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.permiso ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.permiso_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 227 (class 1259 OID 18317)
-- Name: rol; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rol (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL
);


ALTER TABLE public.rol OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 18322)
-- Name: rol_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.rol ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.rol_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 229 (class 1259 OID 18323)
-- Name: rol_permiso; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rol_permiso (
    rol_id integer NOT NULL,
    permiso_id integer NOT NULL
);


ALTER TABLE public.rol_permiso OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 18328)
-- Name: usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuario (
    numero_documento bigint NOT NULL,
    primer_nombre character varying(20) NOT NULL,
    segundo_nombre character varying(20),
    primer_apellido character varying(20) NOT NULL,
    segundo_apellido character varying(20),
    correo text NOT NULL,
    hash_contrasena text NOT NULL,
    activo boolean DEFAULT true,
    ultimo_ingreso timestamp with time zone,
    fecha_registro timestamp with time zone DEFAULT now(),
    rol_id integer
);


ALTER TABLE public.usuario OWNER TO postgres;


--
-- TOC entry 5061 (class 0 OID 18296)
-- Dependencies: 221
-- Data for Name: codigo_recuperacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.codigo_recuperacion (codigo, fecha_expiracion, usuario_id, id) FROM stdin;
\.


--
-- TOC entry 5063 (class 0 OID 18302)
-- Dependencies: 223
-- Data for Name: notificacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notificacion (id, mensaje, id_vinculada, usuario_id, fecha_creacion, tipo) FROM stdin;
\.


--
-- TOC entry 5065 (class 0 OID 18311)
-- Dependencies: 225
-- Data for Name: permiso; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permiso (id, nombre, menu_path) FROM stdin;
1	admin_roles y permisos	/user/role
2	admin_registrar usuario	/user/add
3	admin_gestionar usuarios	/user/manage
4	admin_auditoria expedientes	/file/log
5	expediente_gestionar	/file/manage
6	expediente_asignar encargados	/file/assign_manage
7	expediente_consultar	/file/consult
8	expediente_alertas	/file/alerts
9	admin_auditoria usuarios	/user/log
10	revisor_doc	/
11	creador_doc	/./
12	documento_gestionar	/document/manage
13	expediente_gestionar involucrados	/file/involved/manage
\.


--
-- TOC entry 5067 (class 0 OID 18317)
-- Dependencies: 227
-- Data for Name: rol; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rol (id, nombre) FROM stdin;
1	admin
\.


--
-- TOC entry 5069 (class 0 OID 18323)
-- Dependencies: 229
-- Data for Name: rol_permiso; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rol_permiso (rol_id, permiso_id) FROM stdin;
1	1
1	2
1	3
1	4
1	5
1	6
1	7
1	8
1	9
1	10
1	11
1	12
1	13
\.


--
-- TOC entry 5070 (class 0 OID 18328)
-- Dependencies: 230
-- Data for Name: usuario; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuario (numero_documento, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, correo, hash_contrasena, activo, ultimo_ingreso, fecha_registro, rol_id) FROM stdin;
1233506795	Julian	\N	Rodriguez	\N	julianrf527@gmail.com	$2b$12$TmKaey9KQ5Y.LtWDu4.FqeawBRP.Cc0rwV5W/CsxuXBNHaqvEncue	t	2026-01-29 19:22:16.271407-05	2025-11-13 14:47:43.472071-05	1
\.


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 220
-- Name: auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auditoria_id_seq', 1, false);


--
-- TOC entry 5077 (class 0 OID 0)
-- Dependencies: 222
-- Name: codigo_recuperacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.codigo_recuperacion_id_seq', 1, false);


--
-- TOC entry 5078 (class 0 OID 0)
-- Dependencies: 224
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 1, false);


--
-- TOC entry 5079 (class 0 OID 0)
-- Dependencies: 226
-- Name: permiso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.permiso_id_seq', 13, true);


--
-- TOC entry 5080 (class 0 OID 0)
-- Dependencies: 228
-- Name: rol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rol_id_seq', 1, true);


--
-- TOC entry 4890 (class 2606 OID 18341)
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);


--
-- TOC entry 4892 (class 2606 OID 18343)
-- Name: codigo_recuperacion codigo_recuperacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.codigo_recuperacion
    ADD CONSTRAINT codigo_recuperacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4895 (class 2606 OID 18345)
-- Name: notificacion notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_pkey PRIMARY KEY (id);


--
-- TOC entry 4897 (class 2606 OID 18347)
-- Name: permiso permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_pkey PRIMARY KEY (id);


--
-- TOC entry 4901 (class 2606 OID 18349)
-- Name: rol_permiso rol_permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_pkey PRIMARY KEY (rol_id, permiso_id);


--
-- TOC entry 4899 (class 2606 OID 18351)
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id);


--
-- TOC entry 4903 (class 2606 OID 18353)
-- Name: usuario usuario_correo_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_correo_key UNIQUE (correo);


--
-- TOC entry 4905 (class 2606 OID 18355)
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (numero_documento);


--
-- TOC entry 4893 (class 1259 OID 18356)
-- Name: unique_codigo_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_codigo_usuario ON public.codigo_recuperacion USING btree (usuario_id);


--
-- TOC entry 4907 (class 2606 OID 18357)
-- Name: codigo_recuperacion fk_codigo_usuario; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.codigo_recuperacion
    ADD CONSTRAINT fk_codigo_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuario(numero_documento) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4906 (class 2606 OID 18362)
-- Name: auditoria fk_usuario; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT fk_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuario(numero_documento) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 4908 (class 2606 OID 18367)
-- Name: notificacion notificacion_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(numero_documento);


--
-- TOC entry 4909 (class 2606 OID 18372)
-- Name: rol_permiso rol_permiso_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permiso(id) ON DELETE CASCADE;


--
-- TOC entry 4910 (class 2606 OID 18377)
-- Name: rol_permiso rol_permiso_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id) ON DELETE CASCADE;


--
-- TOC entry 4911 (class 2606 OID 18382)
-- Name: usuario usuario_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id);


-- Completed on 2026-02-10 09:12:08

--
-- PostgreSQL database dump complete
--

\unrestrict w7jesmkYhwI3cBMdbJwu8f5cLeaLxPzAUKQteex40Ausiky1S7VQeRlLkm101so

