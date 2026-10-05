class permission:
    PERMISO_CREADOR = "documento_crear"
    PERMISO_REVISOR = "documento_revisar"


# Acceso de usuario (vía gateway) a /files/upload, /files/{id} y
# /files/download/{id}: basta con UNO de estos permisos de módulo. Son los de
# las pantallas que suben o muestran archivos (visores de etapas y actos de
# sancionatorio e infracciones, informes técnicos, documentos). Control
# provisional: app-docs no sabe a qué expediente pertenece cada archivo; el
# cierre definitivo son URLs firmadas emitidas por el servicio dueño.
# Orden: primero los más comunes, para cortar antes (cada consulta va a caché).
PERMISOS_ARCHIVOS: tuple[str, ...] = (
    "sancionatorio_gestionar",
    "infraccion_gestionar",
    "sancionatorio_consultar",
    "infraccion_consultar",
    "infraccion_informes_subir",
    "infraccion_informes_revisar",
    "infraccion_asignar_informes",
    "infraccion_cargue",
    "documento_crear",
    "documento_revisar",
    "documento_gestionar",
)
