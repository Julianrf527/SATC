class Permission:
    ASSIGN_REPORTS = "infraccion_asignar_informes"
    # Técnico: proyecta el informe técnico y carga su versión firmada con la
    # matriz de recursos afectados (antes infraccion_informes_subir).
    TECNICO = "infraccion_tecnico"
    # Líder técnico: revisa los informes técnicos (aprueba para firma o
    # devuelve). Antes infraccion_informes_revisar.
    LIDER_TECNICO = "infraccion_lider_tecnico"
    # Líder de proyecto: revisa los actos administrativos (medida preventiva,
    # acoger concepto, cierre): aprueba para firma o devuelve.
    LIDER_PROYECTO = "infraccion_lider_proyecto"
    MANUAL_UPLOAD = "infraccion_super_gestion"
    ASSIGN_PERMISSION = "infraccion_asignar"
    FILE_MANAGE = "infraccion_gestionar"
    FILE_CONSULT = "infraccion_consultar"
    # Pantalla /infraction/alerts (y su filtro "Todos").
    FILE_ALERTS = "infraccion_alertas"
    LOG_PERMISSION = "auditoria_infracciones"
