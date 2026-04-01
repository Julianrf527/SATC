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
-- SET transaction_timeout = 0;  -- Comentado: requiere PostgreSQL 17+, contenedor usa PG 15
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'public', false);
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
-- TOC entry 5101 (class 0 OID 0)
-- Dependencies: 220
-- Name: asignaciones_revisores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asignaciones_revisores_id_seq', 1, false);


--
-- TOC entry 5102 (class 0 OID 0)
-- Dependencies: 222
-- Name: auditoria_documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auditoria_documentos_id_seq', 1, false);


--
-- TOC entry 5103 (class 0 OID 0)
-- Dependencies: 224
-- Name: documentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.documentos_id_seq', 1, false);


--
-- TOC entry 5104 (class 0 OID 0)
-- Dependencies: 226
-- Name: revisiones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.revisiones_id_seq', 1, false);


--
-- TOC entry 5105 (class 0 OID 0)
-- Dependencies: 228
-- Name: versiones_documento_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.versiones_documento_id_seq', 1, false);


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


--
-- TOC entry - Tabla file_hash para deduplicación de archivos
-- Name: file_hash; Type: TABLE; Schema: public; Owner: postgres
--

-- Migración: Crear tabla file_hash para deduplicación de archivos
-- Fecha: 2026-02-12
-- Descripción: Esta tabla almacena hashes SHA256 de archivos para evitar duplicados en MinIO

-- Crear tabla file_hash
CREATE TABLE IF NOT EXISTS public.file_hash (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) NOT NULL UNIQUE,  -- Hash SHA256 (64 caracteres hexadecimales)
    file_url TEXT NOT NULL,                 -- URL del archivo en MinIO (bucket/path)
    original_filename VARCHAR(255),         -- Nombre original del primer archivo con este hash
    content_type VARCHAR(100),              -- MIME type del archivo (application/pdf, image/jpeg, etc.)
    file_size INTEGER,                      -- Tamaño del archivo en bytes
    reference_count INTEGER DEFAULT 1,      -- Contador de referencias (cuántas veces se usa)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_referenced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

ALTER TABLE public.file_hash OWNER TO postgres;

-- Crear índice único para búsquedas rápidas por hash
CREATE UNIQUE INDEX IF NOT EXISTS ix_file_hash_unique ON public.file_hash(file_hash);

-- Crear índice para búsquedas de archivos huérfanos (sin referencias)
CREATE INDEX IF NOT EXISTS ix_file_hash_ref_count ON public.file_hash(reference_count);

-- Crear índice para búsquedas por fecha de creación
CREATE INDEX IF NOT EXISTS ix_file_hash_created ON public.file_hash(created_at);

-- Comentarios para documentación
COMMENT ON TABLE public.file_hash IS 'Tabla de deduplicación de archivos. Almacena hashes SHA256 para evitar duplicados en MinIO';
COMMENT ON COLUMN public.file_hash.file_hash IS 'Hash SHA256 del contenido del archivo (64 caracteres hexadecimales)';
COMMENT ON COLUMN public.file_hash.file_url IS 'URL del archivo en MinIO en formato bucket/path';
COMMENT ON COLUMN public.file_hash.reference_count IS 'Número de veces que este archivo está siendo referenciado. 0 = archivo huérfano que puede ser eliminado';
COMMENT ON COLUMN public.file_hash.last_referenced_at IS 'Última vez que se creó o reutilizó una referencia a este archivo';

-- Función para actualizar last_referenced_at y reference_count cuando se reutiliza un archivo
CREATE OR REPLACE FUNCTION update_file_hash_reference()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_referenced_at = CURRENT_TIMESTAMP;
    NEW.reference_count = COALESCE(NEW.reference_count, 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Permisos
GRANT SELECT, INSERT, UPDATE ON public.file_hash TO PUBLIC;
GRANT USAGE ON SEQUENCE public.file_hash_id_seq TO PUBLIC;


-- Completed on 2026-02-10 09:11:38

--
-- PostgreSQL database dump complete
--

\unrestrict bzcpPsRPAqP3kghIkY9kw58qYtCFiLDtR0920hEtEIb8wFWKLE9AsJ1UIx0nruM

