-- ============================================================
-- involucrados_db — esquema y datos iniciales de app-involved
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb involucrados_db && psql -U postgres -d involucrados_db -f involucrados_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict cR0UukA9VpaCOME7oy4gqE7eSNV7JzzrkC2z7KnyomOaLL0VzPKEmcoaloYxTOI


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
-- Name: auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auditoria (
    id integer NOT NULL,
    usuario_id bigint,
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
-- Name: involucrado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.involucrado (
    id integer NOT NULL,
    numero_documento bigint,
    digito_verificacion character varying(2),
    tipo_documento character varying(20),
    nombre character varying(100),
    celular bigint,
    correo character varying(254),
    direccion character varying(200)
);


--
-- Name: involucrado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.involucrado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: involucrado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.involucrado_id_seq OWNED BY public.involucrado.id;


--
-- Name: auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria ALTER COLUMN id SET DEFAULT nextval('public.auditoria_id_seq'::regclass);


--
-- Name: involucrado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.involucrado ALTER COLUMN id SET DEFAULT nextval('public.involucrado_id_seq'::regclass);


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auditoria (id, usuario_id, tipo_evento, resultado, ip_address, user_agent, fecha, detalle, datos_anteriores, datos_nuevos) FROM stdin;
\.


--
-- Data for Name: involucrado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.involucrado (id, numero_documento, digito_verificacion, tipo_documento, nombre, celular, correo, direccion) FROM stdin;
\.


--
-- Name: auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auditoria_id_seq', 1, false);


--
-- Name: involucrado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.involucrado_id_seq', 1, false);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);


--
-- Name: involucrado involucrado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.involucrado
    ADD CONSTRAINT involucrado_pkey PRIMARY KEY (id);


--
-- Name: ix_auditoria_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_fecha ON public.auditoria USING btree (fecha);


--
-- Name: ix_auditoria_tipo_evento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_tipo_evento ON public.auditoria USING btree (tipo_evento);


--
-- Name: ix_auditoria_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_usuario_id ON public.auditoria USING btree (usuario_id);


--
-- Name: ix_involucrado_documento; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_involucrado_documento ON public.involucrado USING btree (numero_documento, tipo_documento);


--
-- PostgreSQL database dump complete
--

\unrestrict cR0UukA9VpaCOME7oy4gqE7eSNV7JzzrkC2z7KnyomOaLL0VzPKEmcoaloYxTOI

