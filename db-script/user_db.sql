-- ============================================================
-- user_db — esquema y datos iniciales de app-users
-- Generado desde los modelos actuales (create_all + db/migrations.py + db/seeds.py + db/permission_sync.py) sobre una BD vacía, el 2026-11-17.
-- Uso: createdb user_db && psql -U postgres -d user_db -f user_db.sql
-- La app también crea y actualiza todo esto sola al arrancar.
-- Sin usuarios: el administrador inicial lo crea app-users desde .env.user_admin.
-- ============================================================

--
-- PostgreSQL database dump
--

\restrict CVedmY9C7ogFjF977cpREQ6fWjDjSicS0L2mC8QH5s3kHVhL90vc3gxSZgZmJwr


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
-- Name: codigo_recuperacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.codigo_recuperacion (
    id integer NOT NULL,
    codigo character varying(60) NOT NULL,
    fecha_expiracion timestamp with time zone NOT NULL,
    fecha_creacion timestamp with time zone,
    usuario_id integer NOT NULL,
    intentos_fallidos integer
);


--
-- Name: codigo_recuperacion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.codigo_recuperacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: codigo_recuperacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.codigo_recuperacion_id_seq OWNED BY public.codigo_recuperacion.id;


--
-- Name: notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notificacion (
    id integer NOT NULL,
    mensaje text NOT NULL,
    id_vinculada character varying(20),
    usuario_id integer NOT NULL,
    fecha_creacion timestamp with time zone,
    tipo character varying(15),
    leida boolean,
    fecha_leida timestamp with time zone
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
-- Name: permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permiso (
    id integer NOT NULL,
    nombre character varying(40) NOT NULL,
    menu_path character varying(50),
    descripcion character varying(200) NOT NULL
);


--
-- Name: permiso_excluye; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permiso_excluye (
    permiso_id integer NOT NULL,
    excluye_id integer NOT NULL
);


--
-- Name: permiso_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permiso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permiso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permiso_id_seq OWNED BY public.permiso.id;


--
-- Name: permiso_requiere; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permiso_requiere (
    permiso_id integer NOT NULL,
    requiere_id integer NOT NULL
);


--
-- Name: rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol (
    id integer NOT NULL,
    nombre character varying(20) NOT NULL
);


--
-- Name: rol_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rol_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_id_seq OWNED BY public.rol.id;


--
-- Name: rol_permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_permiso (
    rol_id integer NOT NULL,
    permiso_id integer NOT NULL
);


--
-- Name: seed_lock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seed_lock (
    id integer DEFAULT 1 NOT NULL,
    locked_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT seed_lock_id_check CHECK ((id = 1))
);


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id integer NOT NULL,
    numero_documento bigint NOT NULL,
    primer_nombre character varying(20) NOT NULL,
    segundo_nombre character varying(20),
    primer_apellido character varying(20) NOT NULL,
    segundo_apellido character varying(20),
    correo character varying(100) NOT NULL,
    hash_contrasena character varying(255) NOT NULL,
    activo boolean,
    fecha_registro timestamp with time zone,
    rol_id integer
);


--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: auditoria id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria ALTER COLUMN id SET DEFAULT nextval('public.auditoria_id_seq'::regclass);


--
-- Name: codigo_recuperacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.codigo_recuperacion ALTER COLUMN id SET DEFAULT nextval('public.codigo_recuperacion_id_seq'::regclass);


--
-- Name: notificacion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion ALTER COLUMN id SET DEFAULT nextval('public.notificacion_id_seq'::regclass);


--
-- Name: permiso id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso ALTER COLUMN id SET DEFAULT nextval('public.permiso_id_seq'::regclass);


--
-- Name: rol id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol ALTER COLUMN id SET DEFAULT nextval('public.rol_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auditoria (id, usuario_id, tipo_evento, resultado, ip_address, user_agent, fecha, detalle, datos_anteriores, datos_nuevos) FROM stdin;
\.


--
-- Data for Name: codigo_recuperacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.codigo_recuperacion (id, codigo, fecha_expiracion, fecha_creacion, usuario_id, intentos_fallidos) FROM stdin;
\.


--
-- Data for Name: notificacion; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notificacion (id, mensaje, id_vinculada, usuario_id, fecha_creacion, tipo, leida, fecha_leida) FROM stdin;
\.


--
-- Data for Name: permiso; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permiso (id, nombre, menu_path, descripcion) FROM stdin;
1	admin_roles_y_permisos	/user/role	Desbloquea la pantalla Roles y permisos. Sirve para crear, editar y eliminar roles y permisos (solo puede otorgar permisos que su propio rol tenga).
2	admin_registrar_usuarios	/user/add	Desbloquea la pantalla Registrar usuario. Sirve para crear cuentas de usuario y asignarles un rol.
3	admin_gestionar_usuarios	/user/manage	Desbloquea la pantalla Gestionar usuarios. Sirve para editar datos, cambiar el rol y activar o desactivar usuarios.
4	sancionatorio_gestionar	/file/manage	Desbloquea la pantalla Gestionar de sancionatorio. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo.
5	sancionatorio_consultar	/file/consult	Desbloquea la pantalla Consulta de sancionatorio. Sirve para ver cualquier expediente en solo lectura y descargarlo.
6	sancionatorio_alertas	/file/alerts	Desbloquea la pestaña Alertas de sancionatorio. Sirve para ver los vencimientos de sus expedientes o de todos.
7	sancionatorio_asignar	/file/assign_manage	Desbloquea la pantalla Asignar de sancionatorio. Sirve para asignar o cambiar el abogado responsable de un expediente.
8	involucrado_gestionar	/involved/manage	Desbloquea el módulo de Involucrados. Sirve para registrar y editar las personas naturales o jurídicas vinculadas a los expedientes.
9	documento_gestionar	/document/manage	Desbloquea el módulo de Documentos. Sirve para ver y gestionar los documentos del flujo genérico de revisión.
10	documento_crear		Desbloquea la creación en el módulo de Documentos. Sirve para cargar documentos y sus nuevas versiones en el flujo genérico de revisión.
11	documento_revisar		Desbloquea la revisión en el módulo de Documentos. Sirve para aprobar o devolver documentos en el flujo genérico de revisión.
12	auditoria_usuarios	/audit/users	Desbloquea la auditoría de usuarios. Sirve para consultar el historial de cambios en usuarios, roles y permisos.
13	auditoria_expedientes	/audit/files	Desbloquea la auditoría de sancionatorio. Sirve para consultar el historial de cambios en los expedientes sancionatorios.
14	auditoria_involucrados	/audit/involved	Desbloquea la auditoría de involucrados. Sirve para consultar el historial de cambios en los involucrados.
15	auditoria_infracciones	/audit/infractions	Desbloquea la auditoría de infracciones. Sirve para consultar el historial de cambios en los expedientes de infracción.
16	infraccion_gestionar	/infraction/manage	Desbloquea la pantalla Gestionar de infracciones. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo.
17	infraccion_consultar	/infraction/consult	Desbloquea la pantalla Consulta de infracciones. Sirve para ver cualquier expediente en solo lectura y descargarlo.
18	infraccion_alertas	/infraction/alerts	Desbloquea la pestaña Alertas de infracciones. Sirve para ver los vencimientos de sus expedientes o de todos.
19	infraccion_asignar	/infraction/assign_manage	Desbloquea la pantalla Asignar de infracciones. Sirve para asignar o cambiar el encargado responsable de un expediente.
20	infraccion_asignar_informes	/infraction/reports	Desbloquea la pantalla Informes de infracciones. Sirve para asignar cada informe técnico a un profesional y a un revisor.
21	infraccion_informes_revisar	/infraction/my-reports	Desbloquea Mis informes de infracciones. Sirve para revisar (aprobar o devolver) los informes técnicos que le asignaron como revisor.
22	infraccion_super_gestion		Desbloquea el cargue manual de informes técnicos. Sirve para cargar informes históricos o manuales sin pasar por el flujo de revisión.
23	infraccion_informes_subir	/infraction/my-reports	Desbloquea Mis informes de infracciones. Sirve para subir los informes técnicos que le asignaron como profesional.
24	recurso_gestionar	/recurso/manage	Desbloquea la pantalla Gestionar de concesiones. Sirve para crear y editar expedientes, asignarse procesos y proyectar los documentos de cada etapa.
25	recurso_consultar	/recurso/consult	Desbloquea la pantalla Consulta de concesiones. Sirve para ver cualquier expediente en solo lectura y descargarlo completo.
26	recurso_super_gestion		Desbloquea el cargue histórico de concesiones. Sirve para cargar directamente cualquier etapa de expedientes viejos sin revisión ni asignación.
27	recurso_lider_juridico	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como líder jurídico. Sirve para revisar los actos administrativos en el primer paso de su cadena.
28	recurso_lider_proyecto	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como líder del proyecto. Sirve para revisar tras el líder jurídico o técnico/SIG y aprobar para firma.
29	recurso_asesora_subdireccion	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como asesora de subdirección. Sirve para revisar la decisión y el acto del recurso con el líder del proyecto.
30	recurso_lider_tecnico	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como líder técnico. Sirve para revisar los conceptos técnicos.
31	recurso_sig	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como SIG. Sirve para revisar el concepto técnico de la etapa 2 junto con el líder técnico.
32	recurso_tecnico	/recurso/my-reports	Desbloquea Mis actuaciones de concesiones como técnico. Sirve para que el abogado lo elija como técnico y cargar su concepto técnico.
\.


--
-- Data for Name: permiso_excluye; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permiso_excluye (permiso_id, excluye_id) FROM stdin;
24	32
32	24
\.


--
-- Data for Name: permiso_requiere; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permiso_requiere (permiso_id, requiere_id) FROM stdin;
6	5
7	5
10	9
11	9
18	17
19	17
20	17
21	17
22	16
23	17
26	24
27	25
28	25
29	25
30	25
31	25
32	25
\.


--
-- Data for Name: rol; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rol (id, nombre) FROM stdin;
1	admin
\.


--
-- Data for Name: rol_permiso; Type: TABLE DATA; Schema: public; Owner: -
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
1	14
1	15
1	16
1	17
1	18
1	19
1	20
1	21
1	22
1	23
1	24
1	25
1	26
1	27
1	28
1	29
1	30
1	31
1	32
\.


--
-- Data for Name: seed_lock; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seed_lock (id, locked_at) FROM stdin;
1	2026-11-17 00:40:00.183071
\.


--
-- Data for Name: usuario; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.usuario (id, numero_documento, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, correo, hash_contrasena, activo, fecha_registro, rol_id) FROM stdin;
\.


--
-- Name: auditoria_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auditoria_id_seq', 1, false);


--
-- Name: codigo_recuperacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.codigo_recuperacion_id_seq', 1, false);


--
-- Name: notificacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notificacion_id_seq', 1, false);


--
-- Name: permiso_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permiso_id_seq', 32, true);


--
-- Name: rol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.rol_id_seq', 1, false);


--
-- Name: usuario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.usuario_id_seq', 1, false);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);


--
-- Name: codigo_recuperacion codigo_recuperacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.codigo_recuperacion
    ADD CONSTRAINT codigo_recuperacion_pkey PRIMARY KEY (id);


--
-- Name: notificacion notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_pkey PRIMARY KEY (id);


--
-- Name: permiso_excluye permiso_excluye_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_excluye
    ADD CONSTRAINT permiso_excluye_pkey PRIMARY KEY (permiso_id, excluye_id);


--
-- Name: permiso permiso_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_nombre_key UNIQUE (nombre);


--
-- Name: permiso permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_pkey PRIMARY KEY (id);


--
-- Name: permiso_requiere permiso_requiere_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_requiere
    ADD CONSTRAINT permiso_requiere_pkey PRIMARY KEY (permiso_id, requiere_id);


--
-- Name: rol_permiso rol_permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_pkey PRIMARY KEY (rol_id, permiso_id);


--
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id);


--
-- Name: seed_lock seed_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seed_lock
    ADD CONSTRAINT seed_lock_pkey PRIMARY KEY (id);


--
-- Name: codigo_recuperacion uq_codigo_usuario; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.codigo_recuperacion
    ADD CONSTRAINT uq_codigo_usuario UNIQUE (usuario_id);


--
-- Name: usuario usuario_correo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_correo_key UNIQUE (correo);


--
-- Name: usuario usuario_numero_documento_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_numero_documento_key UNIQUE (numero_documento);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: ix_auditoria_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_fecha ON public.auditoria USING btree (fecha);


--
-- Name: ix_auditoria_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auditoria_usuario_id ON public.auditoria USING btree (usuario_id);


--
-- Name: ix_notificacion_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notificacion_usuario_id ON public.notificacion USING btree (usuario_id);


--
-- Name: auditoria auditoria_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id) ON DELETE SET NULL;


--
-- Name: codigo_recuperacion codigo_recuperacion_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.codigo_recuperacion
    ADD CONSTRAINT codigo_recuperacion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: notificacion notificacion_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificacion
    ADD CONSTRAINT notificacion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: permiso_excluye permiso_excluye_excluye_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_excluye
    ADD CONSTRAINT permiso_excluye_excluye_id_fkey FOREIGN KEY (excluye_id) REFERENCES public.permiso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: permiso_excluye permiso_excluye_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_excluye
    ADD CONSTRAINT permiso_excluye_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permiso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: permiso_requiere permiso_requiere_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_requiere
    ADD CONSTRAINT permiso_requiere_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permiso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: permiso_requiere permiso_requiere_requiere_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso_requiere
    ADD CONSTRAINT permiso_requiere_requiere_id_fkey FOREIGN KEY (requiere_id) REFERENCES public.permiso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rol_permiso rol_permiso_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permiso(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rol_permiso rol_permiso_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permiso
    ADD CONSTRAINT rol_permiso_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: usuario usuario_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.rol(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict CVedmY9C7ogFjF977cpREQ6fWjDjSicS0L2mC8QH5s3kHVhL90vc3gxSZgZmJwr

