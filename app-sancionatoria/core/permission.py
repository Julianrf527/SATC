class Permission:
    ASSIGN_PERMISSION = "sancionatorio_asignar"
    FILE_MANAGE = "sancionatorio_gestionar"
    # Pantalla /file/consult: ver (solo lectura) todos los expedientes.
    FILE_CONSULT = "sancionatorio_consultar"
    FILE_ALERTS = "sancionatorio_alertas"
    LOG_PERMISSION = "auditoria_expedientes"
    # Gestión de involucrados (app-involved): puede ver en qué expedientes
    # aparece una persona.
    INVOLVED_MANAGE = "involucrado_gestionar"
