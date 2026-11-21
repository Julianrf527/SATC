-- ============================================================
-- recurso_db — esquema y datos iniciales de app-recurso
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb recurso_db && psql -U postgres -d recurso_db -f recurso_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict HgYFOkDNsUJsbpt1iICtj6D9R8lXKU5wl20yfQ3qkTw4mdYgreczGgHX7WAPoKd


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

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: resultado_recurso; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resultado_recurso AS ENUM (
    'REPONE',
    'CONFIRMA',
    'MODIFICA',
    'ADICIONA'
);


--
-- Name: tipo_decision; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_decision AS ENUM (
    'OTORGADA',
    'NEGADA',
    'DESISTIDA'
);


--
-- Name: tipo_vinculo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_vinculo AS ENUM (
    'SOLICITANTE',
    'TERCERO_INTERVINIENTE'
);


--
-- Name: uso_agua; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.uso_agua AS ENUM (
    'DOMESTICO',
    'PECUARIO',
    'ABREVADERO',
    'AGRICOLA',
    'RIEGO',
    'INDUSTRIAL',
    'ACUICULTURA',
    'SILVICULTURA',
    'RECREATIVO',
    'INSTITUCIONAL',
    'OTRO'
);


--
-- Name: trg_concepto_fecha_version_final(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_concepto_fecha_version_final() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF NEW.doc_concepto_tecnico_id IS NULL THEN
            NEW.fecha_version_final := NULL;
        ELSIF TG_OP = 'INSERT' OR OLD.doc_concepto_tecnico_id IS NULL THEN
            NEW.fecha_version_final := COALESCE(NEW.fecha_version_final, now());
        END IF;
        RETURN NEW;
    END $$;


--
-- Name: trg_requerimiento_fecha_respuesta(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_requerimiento_fecha_respuesta() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF NEW.doc_oficio_entrada_id IS NULL THEN
            NEW.fecha_registro_respuesta := NULL;
        ELSIF TG_OP = 'INSERT' OR OLD.doc_oficio_entrada_id IS NULL THEN
            NEW.fecha_registro_respuesta := COALESCE(NEW.fecha_registro_respuesta, now());
        END IF;
        RETURN NEW;
    END $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acto_administrativo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acto_administrativo (
    id integer NOT NULL,
    medio character varying(10) NOT NULL,
    clase_acto character varying(4),
    numerado integer NOT NULL,
    fecha_numerado date NOT NULL,
    documento_acto_administrativo_id integer NOT NULL,
    fecha_creacion timestamp with time zone NOT NULL,
    CONSTRAINT ck_acto_admin_clase_acto CHECK (((clase_acto)::text = ANY ((ARRAY['AUTO'::character varying, 'RES'::character varying])::text[]))),
    CONSTRAINT ck_acto_admin_medio CHECK (((medio)::text = ANY ((ARRAY['COMUNICA'::character varying, 'NOTIFICA'::character varying])::text[])))
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
-- Name: acto_admite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acto_admite (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    encargado_acto_id integer,
    acto_admin_id integer,
    doc_oficio_alcaldia_id integer,
    doc_fijacion_aviso_id integer,
    doc_constancia_fijacion_aviso_id integer,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: acto_admite_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acto_admite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acto_admite_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acto_admite_id_seq OWNED BY public.acto_admite.id;


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
    numerado integer NOT NULL,
    fecha_numerado date NOT NULL,
    fecha_envio date NOT NULL,
    documento_comunicacion_id integer NOT NULL,
    acto_administrativo_id integer NOT NULL,
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
-- Name: concepto_tecnico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.concepto_tecnico (
    id integer NOT NULL,
    expediente_id integer,
    fecha_visita_tecnica date,
    tecnico_encargado_id integer NOT NULL,
    fecha_aceptacion date,
    caudal_fuente double precision,
    caudal_disponible double precision,
    caudal_otorgado double precision,
    num_usuarios integer,
    cumple boolean,
    doc_concepto_tecnico_id integer,
    fecha_version_final timestamp with time zone,
    accion character varying(10),
    version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_concepto_tecnico_accion CHECK (((accion)::text = ANY ((ARRAY['DECIDE'::character varying, 'REQUIERE'::character varying])::text[])))
);


--
-- Name: concepto_tecnico_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.concepto_tecnico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: concepto_tecnico_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.concepto_tecnico_id_seq OWNED BY public.concepto_tecnico.id;


--
-- Name: decision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.decision (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    encargado_acto_id integer,
    acto_admin_id integer,
    decision public.tipo_decision,
    requiere_memorias boolean,
    fecha_ejecutoria date,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: decision_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.decision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: decision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.decision_id_seq OWNED BY public.decision.id;


--
-- Name: documento_proceso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_proceso (
    expediente_id integer NOT NULL,
    tipo_documento character varying(40) NOT NULL,
    etapa_tipo character varying(50) NOT NULL,
    etapa_ref_id integer NOT NULL,
    paso_actual integer DEFAULT 0 NOT NULL,
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
-- Name: documento_proceso_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_proceso_auditoria (
    id integer NOT NULL,
    accion character varying(50) NOT NULL,
    usuario_id integer,
    descripcion text,
    datos_adicionales json,
    fecha_accion timestamp with time zone NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: documento_proceso_auditoria_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_proceso_auditoria_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_proceso_auditoria_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_proceso_auditoria_id_seq OWNED BY public.documento_proceso_auditoria.id;


--
-- Name: documento_proceso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_proceso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_proceso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_proceso_id_seq OWNED BY public.documento_proceso.id;


--
-- Name: documento_proceso_revision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_proceso_revision (
    paso integer,
    permiso character varying(50),
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
-- Name: documento_proceso_revision_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_proceso_revision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_proceso_revision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_proceso_revision_id_seq OWNED BY public.documento_proceso_revision.id;


--
-- Name: documento_proceso_revisor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_proceso_revisor (
    id integer NOT NULL,
    revisor_id integer NOT NULL,
    fecha_asignacion timestamp with time zone NOT NULL,
    notificado boolean NOT NULL,
    proceso_id integer NOT NULL
);


--
-- Name: documento_proceso_revisor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_proceso_revisor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_proceso_revisor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_proceso_revisor_id_seq OWNED BY public.documento_proceso_revisor.id;


--
-- Name: documento_proceso_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_proceso_version (
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
-- Name: documento_proceso_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_proceso_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_proceso_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_proceso_version_id_seq OWNED BY public.documento_proceso_version.id;


--
-- Name: documentos_anexos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos_anexos (
    id integer NOT NULL,
    etapa_tipo character varying(50) NOT NULL,
    etapa_ref_id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    documento_anexo_id integer NOT NULL,
    fecha_subida timestamp with time zone NOT NULL
);


--
-- Name: documentos_anexos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_anexos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentos_anexos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentos_anexos_id_seq OWNED BY public.documentos_anexos.id;


--
-- Name: envio_alertas_semanal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.envio_alertas_semanal (
    semana date NOT NULL,
    fecha_inicio timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: expediente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente (
    id integer NOT NULL,
    radicado character varying(15) NOT NULL,
    fecha_radicado date NOT NULL,
    expediente character varying(9) NOT NULL,
    numero_vital character varying(20) NOT NULL,
    nombre_predio character varying(50) NOT NULL,
    matricula_inmobiliaria character varying(20) NOT NULL,
    codigo_catastral character varying(30) NOT NULL,
    radicado_oficio_entrada character varying(20) NOT NULL,
    fecha_oficio_entrada date NOT NULL,
    doc_comprobante_pago_id integer NOT NULL,
    vereda_id integer NOT NULL,
    tipo_fuente_id integer NOT NULL,
    nombre_fuente character varying(50) NOT NULL,
    fecha_creacion timestamp with time zone NOT NULL,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: expediente_fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_fuente (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    fuente_id integer NOT NULL
);


--
-- Name: expediente_fuente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expediente_fuente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expediente_fuente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expediente_fuente_id_seq OWNED BY public.expediente_fuente.id;


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
    involucrado_id integer NOT NULL,
    tipo_vinculo public.tipo_vinculo DEFAULT 'SOLICITANTE'::public.tipo_vinculo NOT NULL,
    representante_id integer,
    acto_admin_id integer,
    fecha_vinculacion timestamp with time zone NOT NULL,
    version integer DEFAULT 1 NOT NULL
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
-- Name: expediente_uso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_uso (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    uso public.uso_agua NOT NULL
);


--
-- Name: expediente_uso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.expediente_uso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: expediente_uso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.expediente_uso_id_seq OWNED BY public.expediente_uso.id;


--
-- Name: fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fuente (
    id integer NOT NULL,
    nombre character varying(30) NOT NULL
);


--
-- Name: fuente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.fuente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fuente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.fuente_id_seq OWNED BY public.fuente.id;


--
-- Name: informe_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.informe_usuario (
    id integer NOT NULL,
    radicado character varying(15) NOT NULL,
    fecha_radicado date NOT NULL,
    doc_informe_usuario_id integer NOT NULL
);


--
-- Name: informe_usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.informe_usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: informe_usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.informe_usuario_id_seq OWNED BY public.informe_usuario.id;


--
-- Name: memorias_calculo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memorias_calculo (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    radicado character varying(15) NOT NULL,
    fecha_radicado date NOT NULL,
    doc_planos_id integer NOT NULL,
    concepto_tecnico_id integer,
    requerimiento_id integer,
    subsanacion_id integer,
    encargado_acto_id integer,
    acto_admin_id integer,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: memorias_calculo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.memorias_calculo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memorias_calculo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.memorias_calculo_id_seq OWNED BY public.memorias_calculo.id;


--
-- Name: municipio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipio (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL
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
    acto_admin_id integer NOT NULL,
    numerado integer NOT NULL,
    involucrado_id integer NOT NULL,
    fecha_numerado date NOT NULL,
    fecha_envio_citacion date NOT NULL,
    fecha_constancia_citacion date NOT NULL,
    documento_citacion_id integer,
    notificacion_exitosa boolean,
    tipo_notificacion_id integer,
    fecha_notificacion date,
    documento_notificacion_id integer,
    fecha_creacion timestamp with time zone NOT NULL,
    version integer DEFAULT 1 NOT NULL
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
-- Name: practica_pruebas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.practica_pruebas (
    id integer NOT NULL,
    recurso_id integer NOT NULL,
    encargado_acto_id integer,
    acto_admin_id integer,
    concepto_tecnico_id integer,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: practica_pruebas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.practica_pruebas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: practica_pruebas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.practica_pruebas_id_seq OWNED BY public.practica_pruebas.id;


--
-- Name: recibo_satisfaccion_obras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recibo_satisfaccion_obras (
    id integer NOT NULL,
    expediente_id integer NOT NULL,
    informe_usuario_id integer NOT NULL,
    concepto_tecnico_id integer,
    requerimiento_id integer,
    nuevo_informe_usuario_id integer,
    concepto_tecnico_segundo_id integer,
    encargado_acto_id integer,
    acto_admin_id integer,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: recibo_satisfaccion_obras_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.recibo_satisfaccion_obras_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: recibo_satisfaccion_obras_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.recibo_satisfaccion_obras_id_seq OWNED BY public.recibo_satisfaccion_obras.id;


--
-- Name: recurso_reposicion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recurso_reposicion (
    id integer NOT NULL,
    decision_id integer,
    encargado_acto_id integer,
    acto_admin_id integer,
    radicado character varying(15) NOT NULL,
    fecha_radicado date NOT NULL,
    resultado public.resultado_recurso,
    doc_recurso_id integer NOT NULL,
    requiere_pruebas boolean DEFAULT false NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT now() NOT NULL,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: recurso_reposicion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.recurso_reposicion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: recurso_reposicion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.recurso_reposicion_id_seq OWNED BY public.recurso_reposicion.id;


--
-- Name: requerimiento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requerimiento (
    id integer NOT NULL,
    expediente_id integer,
    encargado_acto_id integer,
    acto_admin_id integer,
    radicado_oficio_entrada character varying(15),
    fecha_oficio_entrada date,
    doc_oficio_entrada_id integer,
    fecha_registro_respuesta timestamp with time zone,
    concepto_tecnico_id integer,
    version integer DEFAULT 1 NOT NULL
);


--
-- Name: requerimiento_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.requerimiento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: requerimiento_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.requerimiento_id_seq OWNED BY public.requerimiento.id;


--
-- Name: subsanacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subsanacion (
    id integer NOT NULL,
    radicado character varying(15) NOT NULL,
    fecha_radicado date NOT NULL,
    doc_planos_ajustados_id integer NOT NULL,
    concepto_tecnico_id integer
);


--
-- Name: subsanacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subsanacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subsanacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subsanacion_id_seq OWNED BY public.subsanacion.id;


--
-- Name: tipo_fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_fuente (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL
);


--
-- Name: tipo_fuente_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_fuente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_fuente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_fuente_id_seq OWNED BY public.tipo_fuente.id;


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
    nombre character varying(25) NOT NULL,
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
-- Name: acto_admite id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite ALTER COLUMN id SET DEFAULT nextval('public.acto_admite_id_seq'::regclass);


--
-- Name: auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria ALTER COLUMN id SET DEFAULT nextval('public.auditoria_id_seq'::regclass);


--
-- Name: comunicacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion ALTER COLUMN id SET DEFAULT nextval('public.comunicacion_id_seq'::regclass);


--
-- Name: concepto_tecnico id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_tecnico ALTER COLUMN id SET DEFAULT nextval('public.concepto_tecnico_id_seq'::regclass);


--
-- Name: decision id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision ALTER COLUMN id SET DEFAULT nextval('public.decision_id_seq'::regclass);


--
-- Name: documento_proceso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso ALTER COLUMN id SET DEFAULT nextval('public.documento_proceso_id_seq'::regclass);


--
-- Name: documento_proceso_auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_auditoria ALTER COLUMN id SET DEFAULT nextval('public.documento_proceso_auditoria_id_seq'::regclass);


--
-- Name: documento_proceso_revision id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revision ALTER COLUMN id SET DEFAULT nextval('public.documento_proceso_revision_id_seq'::regclass);


--
-- Name: documento_proceso_revisor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revisor ALTER COLUMN id SET DEFAULT nextval('public.documento_proceso_revisor_id_seq'::regclass);


--
-- Name: documento_proceso_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_version ALTER COLUMN id SET DEFAULT nextval('public.documento_proceso_version_id_seq'::regclass);


--
-- Name: documentos_anexos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_anexos ALTER COLUMN id SET DEFAULT nextval('public.documentos_anexos_id_seq'::regclass);


--
-- Name: expediente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente ALTER COLUMN id SET DEFAULT nextval('public.expediente_id_seq'::regclass);


--
-- Name: expediente_fuente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_fuente ALTER COLUMN id SET DEFAULT nextval('public.expediente_fuente_id_seq'::regclass);


--
-- Name: expediente_involucrado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado ALTER COLUMN id SET DEFAULT nextval('public.expediente_involucrado_id_seq'::regclass);


--
-- Name: expediente_uso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_uso ALTER COLUMN id SET DEFAULT nextval('public.expediente_uso_id_seq'::regclass);


--
-- Name: fuente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fuente ALTER COLUMN id SET DEFAULT nextval('public.fuente_id_seq'::regclass);


--
-- Name: informe_usuario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_usuario ALTER COLUMN id SET DEFAULT nextval('public.informe_usuario_id_seq'::regclass);


--
-- Name: memorias_calculo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo ALTER COLUMN id SET DEFAULT nextval('public.memorias_calculo_id_seq'::regclass);


--
-- Name: municipio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio ALTER COLUMN id SET DEFAULT nextval('public.municipio_id_seq'::regclass);


--
-- Name: notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- Name: practica_pruebas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas ALTER COLUMN id SET DEFAULT nextval('public.practica_pruebas_id_seq'::regclass);


--
-- Name: recibo_satisfaccion_obras id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras ALTER COLUMN id SET DEFAULT nextval('public.recibo_satisfaccion_obras_id_seq'::regclass);


--
-- Name: recurso_reposicion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion ALTER COLUMN id SET DEFAULT nextval('public.recurso_reposicion_id_seq'::regclass);


--
-- Name: requerimiento id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento ALTER COLUMN id SET DEFAULT nextval('public.requerimiento_id_seq'::regclass);


--
-- Name: subsanacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subsanacion ALTER COLUMN id SET DEFAULT nextval('public.subsanacion_id_seq'::regclass);


--
-- Name: tipo_fuente id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_fuente ALTER COLUMN id SET DEFAULT nextval('public.tipo_fuente_id_seq'::regclass);


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

COPY public.acto_administrativo (id, medio, clase_acto, numerado, fecha_numerado, documento_acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: acto_admite; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.acto_admite (id, expediente_id, encargado_acto_id, acto_admin_id, doc_oficio_alcaldia_id, doc_fijacion_aviso_id, doc_constancia_fijacion_aviso_id, version) FROM stdin;
\.


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auditoria (id, expediente_id, expediente_radicado, usuario_id, tipo_evento, resultado, ip_address, user_agent, fecha, detalle, datos_anteriores, datos_nuevos) FROM stdin;
\.


--
-- Data for Name: comunicacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comunicacion (id, numerado, fecha_numerado, fecha_envio, documento_comunicacion_id, acto_administrativo_id, fecha_creacion) FROM stdin;
\.


--
-- Data for Name: concepto_tecnico; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.concepto_tecnico (id, expediente_id, fecha_visita_tecnica, tecnico_encargado_id, fecha_aceptacion, caudal_fuente, caudal_disponible, caudal_otorgado, num_usuarios, cumple, doc_concepto_tecnico_id, fecha_version_final, accion, version) FROM stdin;
\.


--
-- Data for Name: decision; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.decision (id, expediente_id, encargado_acto_id, acto_admin_id, decision, requiere_memorias, fecha_ejecutoria, version) FROM stdin;
\.


--
-- Data for Name: documento_proceso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_proceso (expediente_id, tipo_documento, etapa_tipo, etapa_ref_id, paso_actual, activo, id, nombre, descripcion, estado, creador_id, version_actual, numero_devoluciones, fecha_creacion, fecha_ultima_actualizacion) FROM stdin;
\.


--
-- Data for Name: documento_proceso_auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_proceso_auditoria (id, accion, usuario_id, descripcion, datos_adicionales, fecha_accion, proceso_id) FROM stdin;
\.


--
-- Data for Name: documento_proceso_revision; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_proceso_revision (paso, permiso, id, version_revisada, revisor_id, accion, comentarios, adjunto_file_id, adjunto_url, adjunto_nombre, adjunto_size, fecha_revision, proceso_id) FROM stdin;
\.


--
-- Data for Name: documento_proceso_revisor; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_proceso_revisor (id, revisor_id, fecha_asignacion, notificado, proceso_id) FROM stdin;
\.


--
-- Data for Name: documento_proceso_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documento_proceso_version (id, numero_version, file_id, archivo_url, archivo_nombre, archivo_size, usuario_subida_id, comentario, fecha_subida, proceso_id) FROM stdin;
\.


--
-- Data for Name: documentos_anexos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documentos_anexos (id, etapa_tipo, etapa_ref_id, nombre, documento_anexo_id, fecha_subida) FROM stdin;
\.


--
-- Data for Name: expediente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente (id, radicado, fecha_radicado, expediente, numero_vital, nombre_predio, matricula_inmobiliaria, codigo_catastral, radicado_oficio_entrada, fecha_oficio_entrada, doc_comprobante_pago_id, vereda_id, tipo_fuente_id, nombre_fuente, fecha_creacion, version) FROM stdin;
\.


--
-- Data for Name: expediente_fuente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_fuente (id, expediente_id, fuente_id) FROM stdin;
\.


--
-- Data for Name: expediente_involucrado; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_involucrado (id, expediente_id, involucrado_id, tipo_vinculo, representante_id, acto_admin_id, fecha_vinculacion, version) FROM stdin;
\.


--
-- Data for Name: expediente_uso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.expediente_uso (id, expediente_id, uso) FROM stdin;
\.


--
-- Data for Name: fuente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.fuente (id, nombre) FROM stdin;
1	NACIMIENTO
2	QUEBRADA
3	RÍO
4	MANANTIAL
5	CAÑADA
6	CAÑO
7	CHORRO
8	AFLUENTE
9	ALJIBE
10	RESERVORIO
11	OJO DE AGUA
12	NACEDERO
13	LAGUNA
14	LAGO
15	ZANJA
16	AGUAS LLUVIAS
17	AGUAS DE DRENAJE
18	AGUAS DE INFILTRACIÓN
19	AGUAS RESIDUALES
\.


--
-- Data for Name: informe_usuario; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.informe_usuario (id, radicado, fecha_radicado, doc_informe_usuario_id) FROM stdin;
\.


--
-- Data for Name: memorias_calculo; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.memorias_calculo (id, expediente_id, radicado, fecha_radicado, doc_planos_id, concepto_tecnico_id, requerimiento_id, subsanacion_id, encargado_acto_id, acto_admin_id, version) FROM stdin;
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

COPY public.notificacion (id, acto_admin_id, numerado, involucrado_id, fecha_numerado, fecha_envio_citacion, fecha_constancia_citacion, documento_citacion_id, notificacion_exitosa, tipo_notificacion_id, fecha_notificacion, documento_notificacion_id, fecha_creacion, version) FROM stdin;
\.


--
-- Data for Name: practica_pruebas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.practica_pruebas (id, recurso_id, encargado_acto_id, acto_admin_id, concepto_tecnico_id, version) FROM stdin;
\.


--
-- Data for Name: recibo_satisfaccion_obras; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.recibo_satisfaccion_obras (id, expediente_id, informe_usuario_id, concepto_tecnico_id, requerimiento_id, nuevo_informe_usuario_id, concepto_tecnico_segundo_id, encargado_acto_id, acto_admin_id, version) FROM stdin;
\.


--
-- Data for Name: recurso_reposicion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.recurso_reposicion (id, decision_id, encargado_acto_id, acto_admin_id, radicado, fecha_radicado, resultado, doc_recurso_id, requiere_pruebas, fecha_creacion, version) FROM stdin;
\.


--
-- Data for Name: requerimiento; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.requerimiento (id, expediente_id, encargado_acto_id, acto_admin_id, radicado_oficio_entrada, fecha_oficio_entrada, doc_oficio_entrada_id, fecha_registro_respuesta, concepto_tecnico_id, version) FROM stdin;
\.


--
-- Data for Name: subsanacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subsanacion (id, radicado, fecha_radicado, doc_planos_ajustados_id, concepto_tecnico_id) FROM stdin;
\.


--
-- Data for Name: tipo_fuente; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_fuente (id, nombre) FROM stdin;
1	SUPERFICIAL
2	LÓTICO
3	LÉNTICO
4	SUBTERRÁNEO
\.


--
-- Data for Name: tipo_notificacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tipo_notificacion (id, nombre) FROM stdin;
1	PERSONAL
2	ELECTRÓNICA
3	AVISO
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
-- Name: acto_admite_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.acto_admite_id_seq', 1, false);


--
-- Name: auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auditoria_id_seq', 1, false);


--
-- Name: comunicacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comunicacion_id_seq', 1, false);


--
-- Name: concepto_tecnico_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.concepto_tecnico_id_seq', 1, false);


--
-- Name: decision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.decision_id_seq', 1, false);


--
-- Name: documento_proceso_auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_proceso_auditoria_id_seq', 1, false);


--
-- Name: documento_proceso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_proceso_id_seq', 1, false);


--
-- Name: documento_proceso_revision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_proceso_revision_id_seq', 1, false);


--
-- Name: documento_proceso_revisor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_proceso_revisor_id_seq', 1, false);


--
-- Name: documento_proceso_version_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documento_proceso_version_id_seq', 1, false);


--
-- Name: documentos_anexos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documentos_anexos_id_seq', 1, false);


--
-- Name: expediente_fuente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_fuente_id_seq', 1, false);


--
-- Name: expediente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_id_seq', 1, false);


--
-- Name: expediente_involucrado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_involucrado_id_seq', 1, false);


--
-- Name: expediente_uso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.expediente_uso_id_seq', 1, false);


--
-- Name: fuente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.fuente_id_seq', 19, true);


--
-- Name: informe_usuario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.informe_usuario_id_seq', 1, false);


--
-- Name: memorias_calculo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.memorias_calculo_id_seq', 1, false);


--
-- Name: municipio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.municipio_id_seq', 25, true);


--
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 1, false);


--
-- Name: practica_pruebas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.practica_pruebas_id_seq', 1, false);


--
-- Name: recibo_satisfaccion_obras_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.recibo_satisfaccion_obras_id_seq', 1, false);


--
-- Name: recurso_reposicion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.recurso_reposicion_id_seq', 1, false);


--
-- Name: requerimiento_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.requerimiento_id_seq', 1, false);


--
-- Name: subsanacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.subsanacion_id_seq', 1, false);


--
-- Name: tipo_fuente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_fuente_id_seq', 4, true);


--
-- Name: tipo_notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tipo_notificacion_id_seq', 3, true);


--
-- Name: vereda_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.vereda_id_seq', 467, true);


--
-- Name: acto_administrativo acto_administrativo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_administrativo
    ADD CONSTRAINT acto_administrativo_pkey PRIMARY KEY (id);


--
-- Name: acto_admite acto_admite_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite
    ADD CONSTRAINT acto_admite_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: acto_admite acto_admite_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite
    ADD CONSTRAINT acto_admite_expediente_id_key UNIQUE (expediente_id);


--
-- Name: acto_admite acto_admite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite
    ADD CONSTRAINT acto_admite_pkey PRIMARY KEY (id);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);


--
-- Name: comunicacion comunicacion_acto_administrativo_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion
    ADD CONSTRAINT comunicacion_acto_administrativo_id_key UNIQUE (acto_administrativo_id);


--
-- Name: comunicacion comunicacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion
    ADD CONSTRAINT comunicacion_pkey PRIMARY KEY (id);


--
-- Name: concepto_tecnico concepto_tecnico_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_tecnico
    ADD CONSTRAINT concepto_tecnico_expediente_id_key UNIQUE (expediente_id);


--
-- Name: concepto_tecnico concepto_tecnico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_tecnico
    ADD CONSTRAINT concepto_tecnico_pkey PRIMARY KEY (id);


--
-- Name: decision decision_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision
    ADD CONSTRAINT decision_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: decision decision_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision
    ADD CONSTRAINT decision_expediente_id_key UNIQUE (expediente_id);


--
-- Name: decision decision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision
    ADD CONSTRAINT decision_pkey PRIMARY KEY (id);


--
-- Name: documento_proceso_auditoria documento_proceso_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_auditoria
    ADD CONSTRAINT documento_proceso_auditoria_pkey PRIMARY KEY (id);


--
-- Name: documento_proceso documento_proceso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso
    ADD CONSTRAINT documento_proceso_pkey PRIMARY KEY (id);


--
-- Name: documento_proceso_revision documento_proceso_revision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revision
    ADD CONSTRAINT documento_proceso_revision_pkey PRIMARY KEY (id);


--
-- Name: documento_proceso_revisor documento_proceso_revisor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revisor
    ADD CONSTRAINT documento_proceso_revisor_pkey PRIMARY KEY (id);


--
-- Name: documento_proceso_version documento_proceso_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_version
    ADD CONSTRAINT documento_proceso_version_pkey PRIMARY KEY (id);


--
-- Name: documentos_anexos documentos_anexos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_anexos
    ADD CONSTRAINT documentos_anexos_pkey PRIMARY KEY (id);


--
-- Name: expediente expediente_expediente_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_expediente_key UNIQUE (expediente);


--
-- Name: expediente_fuente expediente_fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_fuente
    ADD CONSTRAINT expediente_fuente_pkey PRIMARY KEY (id);


--
-- Name: expediente_involucrado expediente_involucrado_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: expediente_involucrado expediente_involucrado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_pkey PRIMARY KEY (id);


--
-- Name: envio_alertas_semanal envio_alertas_semanal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.envio_alertas_semanal
    ADD CONSTRAINT envio_alertas_semanal_pkey PRIMARY KEY (semana);


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
-- Name: expediente_uso expediente_uso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_uso
    ADD CONSTRAINT expediente_uso_pkey PRIMARY KEY (id);


--
-- Name: fuente fuente_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fuente
    ADD CONSTRAINT fuente_nombre_key UNIQUE (nombre);


--
-- Name: fuente fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fuente
    ADD CONSTRAINT fuente_pkey PRIMARY KEY (id);


--
-- Name: informe_usuario informe_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_usuario
    ADD CONSTRAINT informe_usuario_pkey PRIMARY KEY (id);


--
-- Name: informe_usuario informe_usuario_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.informe_usuario
    ADD CONSTRAINT informe_usuario_radicado_key UNIQUE (radicado);


--
-- Name: memorias_calculo memorias_calculo_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: memorias_calculo memorias_calculo_concepto_tecnico_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_concepto_tecnico_id_key UNIQUE (concepto_tecnico_id);


--
-- Name: memorias_calculo memorias_calculo_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_expediente_id_key UNIQUE (expediente_id);


--
-- Name: memorias_calculo memorias_calculo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_pkey PRIMARY KEY (id);


--
-- Name: memorias_calculo memorias_calculo_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_radicado_key UNIQUE (radicado);


--
-- Name: memorias_calculo memorias_calculo_requerimiento_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_requerimiento_id_key UNIQUE (requerimiento_id);


--
-- Name: memorias_calculo memorias_calculo_subsanacion_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_subsanacion_id_key UNIQUE (subsanacion_id);


--
-- Name: municipio municipio_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_nombre_key UNIQUE (nombre);


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
-- Name: practica_pruebas practica_pruebas_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: practica_pruebas practica_pruebas_concepto_tecnico_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_concepto_tecnico_id_key UNIQUE (concepto_tecnico_id);


--
-- Name: practica_pruebas practica_pruebas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_pkey PRIMARY KEY (id);


--
-- Name: practica_pruebas practica_pruebas_recurso_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_recurso_id_key UNIQUE (recurso_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_concepto_tecnico_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_concepto_tecnico_id_key UNIQUE (concepto_tecnico_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_concepto_tecnico_segundo_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_concepto_tecnico_segundo_id_key UNIQUE (concepto_tecnico_segundo_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_expediente_id_key UNIQUE (expediente_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_informe_usuario_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_informe_usuario_id_key UNIQUE (informe_usuario_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_nuevo_informe_usuario_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_nuevo_informe_usuario_id_key UNIQUE (nuevo_informe_usuario_id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_pkey PRIMARY KEY (id);


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_requerimiento_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_requerimiento_id_key UNIQUE (requerimiento_id);


--
-- Name: recurso_reposicion recurso_reposicion_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion
    ADD CONSTRAINT recurso_reposicion_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: recurso_reposicion recurso_reposicion_decision_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion
    ADD CONSTRAINT recurso_reposicion_decision_id_key UNIQUE (decision_id);


--
-- Name: recurso_reposicion recurso_reposicion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion
    ADD CONSTRAINT recurso_reposicion_pkey PRIMARY KEY (id);


--
-- Name: requerimiento requerimiento_acto_admin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_acto_admin_id_key UNIQUE (acto_admin_id);


--
-- Name: requerimiento requerimiento_concepto_tecnico_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_concepto_tecnico_id_key UNIQUE (concepto_tecnico_id);


--
-- Name: requerimiento requerimiento_expediente_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_expediente_id_key UNIQUE (expediente_id);


--
-- Name: requerimiento requerimiento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_pkey PRIMARY KEY (id);


--
-- Name: subsanacion subsanacion_concepto_tecnico_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subsanacion
    ADD CONSTRAINT subsanacion_concepto_tecnico_id_key UNIQUE (concepto_tecnico_id);


--
-- Name: subsanacion subsanacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subsanacion
    ADD CONSTRAINT subsanacion_pkey PRIMARY KEY (id);


--
-- Name: subsanacion subsanacion_radicado_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subsanacion
    ADD CONSTRAINT subsanacion_radicado_key UNIQUE (radicado);


--
-- Name: tipo_fuente tipo_fuente_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_fuente
    ADD CONSTRAINT tipo_fuente_nombre_key UNIQUE (nombre);


--
-- Name: tipo_fuente tipo_fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_fuente
    ADD CONSTRAINT tipo_fuente_pkey PRIMARY KEY (id);


--
-- Name: tipo_notificacion tipo_notificacion_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_notificacion
    ADD CONSTRAINT tipo_notificacion_nombre_key UNIQUE (nombre);


--
-- Name: tipo_notificacion tipo_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_notificacion
    ADD CONSTRAINT tipo_notificacion_pkey PRIMARY KEY (id);


--
-- Name: expediente_fuente uq_exp_fuente; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_fuente
    ADD CONSTRAINT uq_exp_fuente UNIQUE (expediente_id, fuente_id);


--
-- Name: expediente_involucrado uq_exp_inv; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT uq_exp_inv UNIQUE (expediente_id, involucrado_id);


--
-- Name: expediente_uso uq_exp_uso; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_uso
    ADD CONSTRAINT uq_exp_uso UNIQUE (expediente_id, uso);


--
-- Name: vereda uq_vereda_municipio_nombre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT uq_vereda_municipio_nombre UNIQUE (municipio_id, nombre);


--
-- Name: vereda vereda_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_pkey PRIMARY KEY (id);


--
-- Name: ix_acto_admin_clase_numerado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acto_admin_clase_numerado ON public.acto_administrativo USING btree (clase_acto, numerado);


--
-- Name: ix_acto_admin_fecha_numerado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acto_admin_fecha_numerado ON public.acto_administrativo USING btree (fecha_numerado);


--
-- Name: ix_acto_admite_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acto_admite_encargado ON public.acto_admite USING btree (encargado_acto_id);


--
-- Name: ix_concepto_tecnico_tecnico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_concepto_tecnico_tecnico ON public.concepto_tecnico USING btree (tecnico_encargado_id);


--
-- Name: ix_decision_decision; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_decision_decision ON public.decision USING btree (decision);


--
-- Name: ix_decision_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_decision_encargado ON public.decision USING btree (encargado_acto_id);


--
-- Name: ix_documento_proceso_auditoria_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_auditoria_proceso_id ON public.documento_proceso_auditoria USING btree (proceso_id);


--
-- Name: ix_documento_proceso_creador_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_creador_id ON public.documento_proceso USING btree (creador_id);


--
-- Name: ix_documento_proceso_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_estado ON public.documento_proceso USING btree (estado);


--
-- Name: ix_documento_proceso_etapa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_etapa ON public.documento_proceso USING btree (etapa_tipo, etapa_ref_id);


--
-- Name: ix_documento_proceso_expediente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_expediente_id ON public.documento_proceso USING btree (expediente_id);


--
-- Name: ix_documento_proceso_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_fecha_creacion ON public.documento_proceso USING btree (fecha_creacion);


--
-- Name: ix_documento_proceso_revision_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_revision_proceso_id ON public.documento_proceso_revision USING btree (proceso_id);


--
-- Name: ix_documento_proceso_revision_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_revision_revisor_id ON public.documento_proceso_revision USING btree (revisor_id);


--
-- Name: ix_documento_proceso_revisor_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_revisor_proceso_id ON public.documento_proceso_revisor USING btree (proceso_id);


--
-- Name: ix_documento_proceso_revisor_revisor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_revisor_revisor_id ON public.documento_proceso_revisor USING btree (revisor_id);


--
-- Name: ix_documento_proceso_tipo_documento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_tipo_documento ON public.documento_proceso USING btree (tipo_documento);


--
-- Name: ix_documento_proceso_version_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_version_file_id ON public.documento_proceso_version USING btree (file_id);


--
-- Name: ix_documento_proceso_version_proceso_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_proceso_version_proceso_id ON public.documento_proceso_version USING btree (proceso_id);


--
-- Name: ix_documentos_anexos_etapa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_anexos_etapa ON public.documentos_anexos USING btree (etapa_tipo, etapa_ref_id);


--
-- Name: ix_expediente_expediente_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_expediente_trgm ON public.expediente USING gin (expediente public.gin_trgm_ops);


--
-- Name: ix_expediente_fecha_radicado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_fecha_radicado ON public.expediente USING btree (fecha_radicado);


--
-- Name: ix_expediente_fuente_fuente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_fuente_fuente ON public.expediente_fuente USING btree (fuente_id);


--
-- Name: ix_expediente_involucrado_involucrado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_involucrado_involucrado ON public.expediente_involucrado USING btree (involucrado_id);


--
-- Name: ix_expediente_numero_vital; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_numero_vital ON public.expediente USING btree (numero_vital);


--
-- Name: ix_expediente_numero_vital_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_numero_vital_trgm ON public.expediente USING gin (numero_vital public.gin_trgm_ops);


--
-- Name: ix_expediente_radicado_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_radicado_trgm ON public.expediente USING gin (radicado public.gin_trgm_ops);


--
-- Name: ix_expediente_tipo_fuente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_tipo_fuente ON public.expediente USING btree (tipo_fuente_id);


--
-- Name: ix_expediente_uso_uso; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_uso_uso ON public.expediente_uso USING btree (uso);


--
-- Name: ix_expediente_vereda; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_expediente_vereda ON public.expediente USING btree (vereda_id);


--
-- Name: ix_memorias_calculo_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memorias_calculo_encargado ON public.memorias_calculo USING btree (encargado_acto_id);


--
-- Name: ix_notificacion_acto_involucrado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_acto_involucrado ON public.notificacion USING btree (acto_admin_id, involucrado_id);


--
-- Name: ix_notificacion_involucrado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_involucrado ON public.notificacion USING btree (involucrado_id);


--
-- Name: ix_practica_pruebas_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_practica_pruebas_encargado ON public.practica_pruebas USING btree (encargado_acto_id);


--
-- Name: ix_recibo_obras_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_recibo_obras_encargado ON public.recibo_satisfaccion_obras USING btree (encargado_acto_id);


--
-- Name: ix_recurso_reposicion_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_recurso_reposicion_encargado ON public.recurso_reposicion USING btree (encargado_acto_id);


--
-- Name: ix_requerimiento_encargado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requerimiento_encargado ON public.requerimiento USING btree (encargado_acto_id);


--
-- Name: uq_documento_proceso_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_documento_proceso_activo ON public.documento_proceso USING btree (etapa_tipo, etapa_ref_id) WHERE activo;


--
-- Name: concepto_tecnico concepto_fecha_version_final; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER concepto_fecha_version_final BEFORE INSERT OR UPDATE OF doc_concepto_tecnico_id ON public.concepto_tecnico FOR EACH ROW EXECUTE FUNCTION public.trg_concepto_fecha_version_final();


--
-- Name: requerimiento requerimiento_fecha_respuesta; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER requerimiento_fecha_respuesta BEFORE INSERT OR UPDATE OF doc_oficio_entrada_id ON public.requerimiento FOR EACH ROW EXECUTE FUNCTION public.trg_requerimiento_fecha_respuesta();


--
-- Name: acto_admite acto_admite_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite
    ADD CONSTRAINT acto_admite_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: acto_admite acto_admite_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acto_admite
    ADD CONSTRAINT acto_admite_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: auditoria auditoria_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: comunicacion comunicacion_acto_administrativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comunicacion
    ADD CONSTRAINT comunicacion_acto_administrativo_id_fkey FOREIGN KEY (acto_administrativo_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: concepto_tecnico concepto_tecnico_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_tecnico
    ADD CONSTRAINT concepto_tecnico_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: decision decision_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision
    ADD CONSTRAINT decision_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: decision decision_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decision
    ADD CONSTRAINT decision_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: documento_proceso_auditoria documento_proceso_auditoria_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_auditoria
    ADD CONSTRAINT documento_proceso_auditoria_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.documento_proceso(id) ON DELETE CASCADE;


--
-- Name: documento_proceso documento_proceso_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso
    ADD CONSTRAINT documento_proceso_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: documento_proceso_revision documento_proceso_revision_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revision
    ADD CONSTRAINT documento_proceso_revision_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.documento_proceso(id) ON DELETE CASCADE;


--
-- Name: documento_proceso_revisor documento_proceso_revisor_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_revisor
    ADD CONSTRAINT documento_proceso_revisor_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.documento_proceso(id) ON DELETE CASCADE;


--
-- Name: documento_proceso_version documento_proceso_version_proceso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_proceso_version
    ADD CONSTRAINT documento_proceso_version_proceso_id_fkey FOREIGN KEY (proceso_id) REFERENCES public.documento_proceso(id) ON DELETE CASCADE;


--
-- Name: expediente_fuente expediente_fuente_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_fuente
    ADD CONSTRAINT expediente_fuente_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente_fuente expediente_fuente_fuente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_fuente
    ADD CONSTRAINT expediente_fuente_fuente_id_fkey FOREIGN KEY (fuente_id) REFERENCES public.fuente(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: expediente_involucrado expediente_involucrado_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: expediente_involucrado expediente_involucrado_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_involucrado
    ADD CONSTRAINT expediente_involucrado_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente expediente_tipo_fuente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_tipo_fuente_id_fkey FOREIGN KEY (tipo_fuente_id) REFERENCES public.tipo_fuente(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: expediente_uso expediente_uso_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_uso
    ADD CONSTRAINT expediente_uso_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: expediente expediente_vereda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente
    ADD CONSTRAINT expediente_vereda_id_fkey FOREIGN KEY (vereda_id) REFERENCES public.vereda(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: memorias_calculo memorias_calculo_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: memorias_calculo memorias_calculo_concepto_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_concepto_tecnico_id_fkey FOREIGN KEY (concepto_tecnico_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: memorias_calculo memorias_calculo_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: memorias_calculo memorias_calculo_requerimiento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_requerimiento_id_fkey FOREIGN KEY (requerimiento_id) REFERENCES public.requerimiento(id) ON UPDATE CASCADE;


--
-- Name: memorias_calculo memorias_calculo_subsanacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memorias_calculo
    ADD CONSTRAINT memorias_calculo_subsanacion_id_fkey FOREIGN KEY (subsanacion_id) REFERENCES public.subsanacion(id) ON UPDATE CASCADE;


--
-- Name: notificacion notificacion_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: notificacion notificacion_tipo_notificacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_tipo_notificacion_id_fkey FOREIGN KEY (tipo_notificacion_id) REFERENCES public.tipo_notificacion(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: practica_pruebas practica_pruebas_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: practica_pruebas practica_pruebas_concepto_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_concepto_tecnico_id_fkey FOREIGN KEY (concepto_tecnico_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: practica_pruebas practica_pruebas_recurso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.practica_pruebas
    ADD CONSTRAINT practica_pruebas_recurso_id_fkey FOREIGN KEY (recurso_id) REFERENCES public.recurso_reposicion(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_concepto_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_concepto_tecnico_id_fkey FOREIGN KEY (concepto_tecnico_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_concepto_tecnico_segundo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_concepto_tecnico_segundo_id_fkey FOREIGN KEY (concepto_tecnico_segundo_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_informe_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_informe_usuario_id_fkey FOREIGN KEY (informe_usuario_id) REFERENCES public.informe_usuario(id) ON UPDATE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_nuevo_informe_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_nuevo_informe_usuario_id_fkey FOREIGN KEY (nuevo_informe_usuario_id) REFERENCES public.informe_usuario(id) ON UPDATE CASCADE;


--
-- Name: recibo_satisfaccion_obras recibo_satisfaccion_obras_requerimiento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recibo_satisfaccion_obras
    ADD CONSTRAINT recibo_satisfaccion_obras_requerimiento_id_fkey FOREIGN KEY (requerimiento_id) REFERENCES public.requerimiento(id) ON UPDATE CASCADE;


--
-- Name: recurso_reposicion recurso_reposicion_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion
    ADD CONSTRAINT recurso_reposicion_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: recurso_reposicion recurso_reposicion_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurso_reposicion
    ADD CONSTRAINT recurso_reposicion_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.decision(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: requerimiento requerimiento_acto_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_acto_admin_id_fkey FOREIGN KEY (acto_admin_id) REFERENCES public.acto_administrativo(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: requerimiento requerimiento_concepto_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_concepto_tecnico_id_fkey FOREIGN KEY (concepto_tecnico_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: requerimiento requerimiento_expediente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requerimiento
    ADD CONSTRAINT requerimiento_expediente_id_fkey FOREIGN KEY (expediente_id) REFERENCES public.expediente(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: subsanacion subsanacion_concepto_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subsanacion
    ADD CONSTRAINT subsanacion_concepto_tecnico_id_fkey FOREIGN KEY (concepto_tecnico_id) REFERENCES public.concepto_tecnico(id) ON UPDATE CASCADE;


--
-- Name: vereda vereda_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vereda
    ADD CONSTRAINT vereda_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipio(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict HgYFOkDNsUJsbpt1iICtj6D9R8lXKU5wl20yfQ3qkTw4mdYgreczGgHX7WAPoKd

