class Permisos:
    PERMISO_ROL="admin_roles_y_permisos"
    PERMISO_USER="admin_registrar_usuarios"
    GESTION_USER="admin_gestionar_usuarios"
    USER_LOG="auditoria_usuarios"

    # Catálogos de solo lectura de app-users y las pantallas que los usan.
    # GET /user/all: /user/manage (gestionar) y /user/add (registrar).
    VER_USUARIOS = ("admin_gestionar_usuarios", "admin_registrar_usuarios")
    # GET /role/all y /role/permissions (nombres para mostrar): editor de roles,
    # selector de rol de /user/add y /user/manage, y el modal de detalle de las
    # pantallas de auditoría. Las escrituras de roles siguen exigiendo
    # admin_roles_y_permisos.
    AUDITORIA = (
        "auditoria_usuarios", "auditoria_expedientes",
        "auditoria_involucrados", "auditoria_infracciones",
    )
    VER_ROLES = ("admin_roles_y_permisos", "admin_registrar_usuarios", "admin_gestionar_usuarios") + AUDITORIA
    VER_PERMISOS = ("admin_roles_y_permisos",) + AUDITORIA