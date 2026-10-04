class Permisos:
    INVOLVED_MANAGE = "involucrado_gestionar"
    INVOLVED_LOG = "auditoria_involucrados"
    # Permisos de otros microservicios que también pueden buscar/crear
    # involucrados al vincularlos a un expediente propio.
    SANCIONATORIO_MANAGE = "sancionatorio_gestionar"
    INFRACCION_MANAGE = "infraccion_gestionar"