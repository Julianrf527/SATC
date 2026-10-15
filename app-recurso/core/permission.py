class Permission:
    """Permisos de Concesiones de Aguas (plan §2). Viven en app-users (seeds)."""

    # Acceso
    MANAGE = "recurso_gestionar"
    CONSULT = "recurso_consultar"
    SUPER_MANAGE = "recurso_super_gestion"

    # Revisores
    LIDER_JURIDICO = "recurso_lider_juridico"
    LIDER_PROYECTO = "recurso_lider_proyecto"
    ASESORA_SUBDIRECCION = "recurso_asesora_subdireccion"
    LIDER_TECNICO = "recurso_lider_tecnico"
    SIG = "recurso_sig"

    # Selección como técnico encargado de un concepto
    TECNICO = "recurso_tecnico"

    REVISORES = (LIDER_JURIDICO, LIDER_PROYECTO, ASESORA_SUBDIRECCION, LIDER_TECNICO, SIG)
