"""
Catálogo de permisos de SATC: fuente única para el seed inicial y para la
sincronización idempotente que corre en cada arranque (db/permission_sync.py).

- PERMISOS: nombre (slug que validan los servicios), menu_path (pantalla) y
  descripcion corta ("Desbloquea X. Sirve para Y.") que ve el administrador en
  la pantalla de roles. descripcion cabe en permiso.descripcion (VARCHAR 200).
- DEPENDENCIAS: permiso -> permisos que exige tener en el mismo rol. Un solo
  sentido: tener el requerido no obliga a tener el dependiente. Se validan al
  guardar un rol (POST /role/add, PUT /role/update/{id}); los roles existentes
  que incumplan siguen funcionando y se reportan (GET /role/dependencias-incumplidas).
- INCOMPATIBLES: pares de permisos que no pueden ir en el mismo rol (en los dos
  sentidos). Se validan al guardar un rol, igual que DEPENDENCIAS, salvo en los
  roles que administran roles (EXENTO_INCOMPATIBLES): esos necesitan todos los
  permisos para poder repartirlos (anti-escalada) y recibir los nuevos.
- DESCRIPCIONES_ANTERIORES: textos por defecto que tuvo la descripción de un
  permiso. Si la descripción guardada sigue siendo uno de ellos (nadie la editó),
  la sincronización la reemplaza por la actual del catálogo.
- RENOMBRES: (nombre_viejo, nombre_nuevo). La fila se renombra en sitio, así los
  roles que la tenían la conservan (rol_permiso va por id).

Para agregar, describir o encadenar permisos basta con editar este archivo y
redesplegar app-users: no hace falta SQL manual en la VM.
"""

DESCRIPCION_MAX = 200

PERMISOS: list[dict] = [
    # ---------- Administración ----------
    {
        "nombre": "admin_roles_y_permisos",
        "menu_path": "/user/role",
        "descripcion": "Desbloquea la pantalla Roles y permisos. Sirve para crear, editar y eliminar roles y permisos (solo puede otorgar permisos que su propio rol tenga).",
    },
    {
        "nombre": "admin_registrar_usuarios",
        "menu_path": "/user/add",
        "descripcion": "Desbloquea la pantalla Registrar usuario. Sirve para crear cuentas de usuario y asignarles un rol.",
    },
    {
        "nombre": "admin_gestionar_usuarios",
        "menu_path": "/user/manage",
        "descripcion": "Desbloquea la pantalla Gestionar usuarios. Sirve para editar datos, cambiar el rol y activar o desactivar usuarios.",
    },
    # ---------- Sancionatorio ----------
    {
        "nombre": "sancionatorio_gestionar",
        "menu_path": "/file/manage",
        "descripcion": "Desbloquea la pantalla Gestionar de sancionatorio. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo.",
    },
    {
        "nombre": "sancionatorio_consultar",
        "menu_path": "/file/consult",
        "descripcion": "Desbloquea la pantalla Consulta de sancionatorio. Sirve para ver cualquier expediente en solo lectura y descargarlo.",
    },
    {
        "nombre": "sancionatorio_alertas",
        "menu_path": "/file/alerts",
        "descripcion": "Desbloquea la pestaña Alertas de sancionatorio. Sirve para ver los vencimientos de sus expedientes o de todos.",
    },
    {
        "nombre": "sancionatorio_asignar",
        "menu_path": "/file/assign_manage",
        "descripcion": "Desbloquea la pantalla Asignar de sancionatorio. Sirve para asignar o cambiar el abogado responsable de un expediente.",
    },
    # ---------- Involucrados ----------
    {
        "nombre": "involucrado_gestionar",
        "menu_path": "/involved/manage",
        "descripcion": "Desbloquea el módulo de Involucrados. Sirve para registrar y editar las personas naturales o jurídicas vinculadas a los expedientes.",
    },
    # ---------- Documentos (flujo genérico de app-docs) ----------
    {
        "nombre": "documento_gestionar",
        "menu_path": "/document/manage",
        "descripcion": "Desbloquea el módulo de Documentos. Sirve para ver y gestionar los documentos del flujo genérico de revisión.",
    },
    {
        "nombre": "documento_crear",
        "menu_path": "",
        "descripcion": "Desbloquea la creación en el módulo de Documentos. Sirve para cargar documentos y sus nuevas versiones en el flujo genérico de revisión.",
    },
    {
        "nombre": "documento_revisar",
        "menu_path": "",
        "descripcion": "Desbloquea la revisión en el módulo de Documentos. Sirve para aprobar o devolver documentos en el flujo genérico de revisión.",
    },
    # ---------- Auditoría ----------
    {
        "nombre": "auditoria_usuarios",
        "menu_path": "/audit/users",
        "descripcion": "Desbloquea la auditoría de usuarios. Sirve para consultar el historial de cambios en usuarios, roles y permisos.",
    },
    {
        "nombre": "auditoria_expedientes",
        "menu_path": "/audit/files",
        "descripcion": "Desbloquea la auditoría de sancionatorio. Sirve para consultar el historial de cambios en los expedientes sancionatorios.",
    },
    {
        "nombre": "auditoria_involucrados",
        "menu_path": "/audit/involved",
        "descripcion": "Desbloquea la auditoría de involucrados. Sirve para consultar el historial de cambios en los involucrados.",
    },
    {
        "nombre": "auditoria_infracciones",
        "menu_path": "/audit/infractions",
        "descripcion": "Desbloquea la auditoría de infracciones. Sirve para consultar el historial de cambios en los expedientes de infracción.",
    },
    # ---------- Infracciones ----------
    {
        "nombre": "infraccion_gestionar",
        "menu_path": "/infraction/manage",
        "descripcion": "Desbloquea la pantalla Gestionar de infracciones. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo.",
    },
    {
        "nombre": "infraccion_consultar",
        "menu_path": "/infraction/consult",
        "descripcion": "Desbloquea la pantalla Consulta de infracciones. Sirve para ver cualquier expediente en solo lectura y descargarlo.",
    },
    {
        "nombre": "infraccion_alertas",
        "menu_path": "/infraction/alerts",
        "descripcion": "Desbloquea la pestaña Alertas de infracciones. Sirve para ver los vencimientos de sus expedientes o de todos.",
    },
    {
        "nombre": "infraccion_asignar",
        "menu_path": "/infraction/assign_manage",
        "descripcion": "Desbloquea la pantalla Asignar de infracciones. Sirve para asignar o cambiar el encargado responsable de un expediente.",
    },
    {
        "nombre": "infraccion_asignar_informes",
        "menu_path": "/infraction/reports",
        "descripcion": "Desbloquea la pantalla Informes de infracciones. Sirve para asignar cada informe técnico a un profesional y a un revisor.",
    },
    {
        "nombre": "infraccion_informes_revisar",
        "menu_path": "/infraction/my-reports",
        "descripcion": "Desbloquea Mis informes de infracciones. Sirve para revisar (aprobar o devolver) los informes técnicos que le asignaron como revisor.",
    },
    {
        "nombre": "infraccion_super_gestion",
        "menu_path": "",
        "descripcion": "Desbloquea el cargue manual de informes técnicos. Sirve para cargar informes históricos o manuales sin pasar por el flujo de revisión.",
    },
    {
        "nombre": "infraccion_informes_subir",
        "menu_path": "/infraction/my-reports",
        "descripcion": "Desbloquea Mis informes de infracciones. Sirve para subir los informes técnicos que le asignaron como profesional.",
    },
    # ---------- Concesiones de Aguas Superficiales (app-recurso, plan §2 y §5) ----------
    {
        "nombre": "recurso_gestionar",
        "menu_path": "/recurso/manage",
        "descripcion": "Desbloquea la pantalla Gestionar de concesiones. Sirve para crear y editar expedientes, asignarse procesos y proyectar los documentos de cada etapa.",
    },
    {
        "nombre": "recurso_consultar",
        "menu_path": "/recurso/consult",
        "descripcion": "Desbloquea la pantalla Consulta de concesiones. Sirve para ver cualquier expediente en solo lectura y descargarlo completo.",
    },
    {
        "nombre": "recurso_super_gestion",
        "menu_path": "",
        "descripcion": "Desbloquea el cargue histórico de concesiones. Sirve para cargar directamente cualquier etapa de expedientes viejos sin revisión ni asignación.",
    },
    {
        "nombre": "recurso_lider_juridico",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como líder jurídico. Sirve para revisar los actos administrativos en el primer paso de su cadena.",
    },
    {
        "nombre": "recurso_lider_proyecto",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como líder del proyecto. Sirve para revisar tras el líder jurídico o técnico/SIG y aprobar para firma.",
    },
    {
        "nombre": "recurso_asesora_subdireccion",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como asesora de subdirección. Sirve para revisar la decisión y el acto del recurso con el líder del proyecto.",
    },
    {
        "nombre": "recurso_lider_tecnico",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como líder técnico. Sirve para revisar los conceptos técnicos.",
    },
    {
        "nombre": "recurso_sig",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como SIG. Sirve para revisar el concepto técnico de la etapa 2 junto con el líder técnico.",
    },
    {
        "nombre": "recurso_tecnico",
        "menu_path": "/recurso/my-reports",
        "descripcion": "Desbloquea Mis actuaciones de concesiones como técnico. Sirve para que el abogado lo elija como técnico y cargar su concepto técnico.",
    },
]

# Permiso -> permisos que exige en el mismo rol (decisión de negocio).
DEPENDENCIAS: dict[str, tuple[str, ...]] = {
    "sancionatorio_alertas": ("sancionatorio_consultar",),
    "sancionatorio_asignar": ("sancionatorio_consultar",),
    "infraccion_alertas": ("infraccion_consultar",),
    "infraccion_asignar": ("infraccion_consultar",),
    "infraccion_asignar_informes": ("infraccion_consultar",),
    "infraccion_informes_subir": ("infraccion_consultar",),
    "infraccion_informes_revisar": ("infraccion_consultar",),
    "infraccion_super_gestion": ("infraccion_gestionar",),
    "documento_crear": ("documento_gestionar",),
    "documento_revisar": ("documento_gestionar",),
    "recurso_super_gestion": ("recurso_gestionar",),
    "recurso_tecnico": ("recurso_consultar",),
    "recurso_lider_juridico": ("recurso_consultar",),
    "recurso_lider_proyecto": ("recurso_consultar",),
    "recurso_asesora_subdireccion": ("recurso_consultar",),
    "recurso_lider_tecnico": ("recurso_consultar",),
    "recurso_sig": ("recurso_consultar",),
}

# Pares que no pueden ir en el mismo rol (decisión de negocio). El técnico de
# concesiones no gestiona: carga sus conceptos desde Mis actuaciones (y, como
# recurso_super_gestion exige gestionar, tampoco puede tener super gestión).
INCOMPATIBLES: tuple[tuple[str, str], ...] = (
    ("recurso_tecnico", "recurso_gestionar"),
)

# Los roles con este permiso (administran roles) no tienen incompatibilidades.
EXENTO_INCOMPATIBLES = "admin_roles_y_permisos"

# Permiso -> descripciones por defecto anteriores (se reemplazan si nadie las editó).
DESCRIPCIONES_ANTERIORES: dict[str, tuple[str, ...]] = {
    "recurso_lider_juridico": (
        "Desbloquea Mis informes de concesiones como líder jurídico. Sirve para revisar los actos administrativos en el primer paso de su cadena.",
    ),
    "recurso_lider_proyecto": (
        "Desbloquea Mis informes de concesiones como líder del proyecto. Sirve para revisar tras el líder jurídico o técnico/SIG y aprobar para firma.",
    ),
    "recurso_asesora_subdireccion": (
        "Desbloquea Mis informes de concesiones como asesora de subdirección. Sirve para revisar la decisión y el acto del recurso con el líder del proyecto.",
    ),
    "recurso_lider_tecnico": (
        "Desbloquea Mis informes de concesiones como líder técnico. Sirve para revisar los conceptos técnicos.",
    ),
    "recurso_sig": (
        "Desbloquea Mis informes de concesiones como SIG. Sirve para revisar el concepto técnico de la etapa 2 junto con el líder técnico.",
    ),
    "recurso_tecnico": (
        "Desbloquea Mis informes de concesiones como técnico. Sirve para que el abogado lo elija como técnico y cargar su concepto técnico.",
    ),
}

# (nombre viejo, nombre nuevo), en orden de aplicación.
RENOMBRES: tuple[tuple[str, str], ...] = (
    ("infraccion_cargue", "infraccion_super_gestion"),
)


def _validar_catalogo() -> None:
    """Falla al importar si el catálogo es inconsistente (error de programación)."""
    nombres = [p["nombre"] for p in PERMISOS]
    if len(nombres) != len(set(nombres)):
        raise ValueError("PERMISOS tiene nombres repetidos")
    conocidos = set(nombres)
    for p in PERMISOS:
        if len(p["descripcion"]) > DESCRIPCION_MAX:
            raise ValueError(f"Descripción de {p['nombre']} supera {DESCRIPCION_MAX} caracteres")
    for permiso, requeridos in DEPENDENCIAS.items():
        for r in (permiso, *requeridos):
            if r not in conocidos:
                raise ValueError(f"DEPENDENCIAS menciona un permiso fuera del catálogo: {r}")
        if permiso in requeridos:
            raise ValueError(f"{permiso} no puede requerirse a sí mismo")
    if EXENTO_INCOMPATIBLES not in conocidos:
        raise ValueError(f"EXENTO_INCOMPATIBLES fuera del catálogo: {EXENTO_INCOMPATIBLES}")
    for a, b in INCOMPATIBLES:
        for r in (a, b):
            if r not in conocidos:
                raise ValueError(f"INCOMPATIBLES menciona un permiso fuera del catálogo: {r}")
        if a == b:
            raise ValueError(f"{a} no puede ser incompatible consigo mismo")
        # Si uno exige al otro, el permiso dependiente no se podría otorgar nunca.
        if b in DEPENDENCIAS.get(a, ()) or a in DEPENDENCIAS.get(b, ()):
            raise ValueError(f"{a} y {b} no pueden ser incompatibles: uno exige al otro")
    for permiso, anteriores in DESCRIPCIONES_ANTERIORES.items():
        if permiso not in conocidos:
            raise ValueError(f"DESCRIPCIONES_ANTERIORES menciona un permiso fuera del catálogo: {permiso}")
        actual = next(p["descripcion"] for p in PERMISOS if p["nombre"] == permiso)
        if actual in anteriores:
            raise ValueError(f"La descripción actual de {permiso} está entre sus anteriores")


_validar_catalogo()
