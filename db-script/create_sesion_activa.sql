CREATE TABLE IF NOT EXISTS public.sesion_activa (
    id SERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES public.usuario(numero_documento) ON DELETE CASCADE ON UPDATE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    fecha_login TIMESTAMPTZ DEFAULT NOW(),
    fecha_ultimo_uso TIMESTAMPTZ DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_sesion_usuario_activo ON public.sesion_activa(usuario_id, activo);
