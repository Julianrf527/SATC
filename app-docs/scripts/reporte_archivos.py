"""Reporte (solo lectura) para decidir cuándo cerrar el acceso a archivos.

Uso, dentro del contenedor de app-docs:

    docker exec satc-app-docs python -m scripts.reporte_archivos [--dias 7]

Responde tres preguntas:

1. ¿Se puede pasar ARCHIVOS_VALIDAR_ASOCIACION a "on"?
   Asociaciones de los últimos N días (file_uso con usuario_id) que la regla
   habría rechazado: el usuario no subió el archivo dentro de la ventana. Si
   aparecen casos legítimos (p. ej. un flujo que reutiliza archivos de otra
   entidad), hay que ajustar la regla o el módulo antes de activarla.

2. ¿Se puede pasar LIMPIEZA_CRITERIO a "duenos"?
   Archivos en uso según numero_usos pero sin ningún dueño en file_uso: con
   "duenos" la limpieza los borraría. Tiene que dar 0 (por servicio: falta la
   carga inicial con registrar-usos o el módulo aún usa el formato anterior).

3. ¿Se puede pasar ARCHIVOS_ACCESO_DIRECTO_USUARIOS a "false"?
   Lo decide el tráfico, no la BD: cada lectura directa de un usuario deja
   "Acceso directo de usuario" en el log de app-docs. Tiene que dar 0:

       docker logs satc-app-docs --since 168h 2>&1 | grep -c "Acceso directo de usuario"
"""
import argparse
import asyncio
import os

from sqlalchemy import text

from db.database import engine

VENTANA_HORAS = float(os.getenv("ARCHIVOS_VENTANA_SUBIDA_HORAS", "24"))

SQL_RECHAZOS = text("""
SELECT u.servicio, u.entidad, COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NOT EXISTS (
           SELECT 1 FROM file_subida s
           WHERE s.file_id = u.file_id AND s.usuario_id = u.usuario_id
             AND s.fecha BETWEEN u.creado_en - make_interval(secs => :ventana) AND u.creado_en
       )) AS rechazaria
FROM file_uso u
WHERE u.usuario_id IS NOT NULL AND u.creado_en >= now() - make_interval(days => :dias)
GROUP BY u.servicio, u.entidad
ORDER BY u.servicio, u.entidad
""")

SQL_SIN_DUENO = text("""
SELECT COUNT(*) AS archivos, COALESCE(SUM(fh.file_size), 0) AS bytes
FROM file_hash fh
WHERE fh.numero_usos > 0
  AND NOT EXISTS (SELECT 1 FROM file_uso u WHERE u.file_id = fh.id)
""")

SQL_DUENOS = text("""
SELECT servicio, COUNT(DISTINCT file_id) AS archivos, COUNT(*) AS asociaciones
FROM file_uso GROUP BY servicio ORDER BY servicio
""")


async def generar(dias: int, motor=None) -> str:
    lineas = []
    async with (motor or engine).connect() as conn:
        lineas.append(f"1. Validación de asociaciones (últimos {dias} días, ventana {VENTANA_HORAS:g} h)")
        filas = (await conn.execute(SQL_RECHAZOS, {"dias": dias, "ventana": VENTANA_HORAS * 3600})).all()
        if not filas:
            lineas.append("   Sin asociaciones con usuario en el periodo (ningún módulo usa aún el formato nuevo).")
        for f in filas:
            lineas.append(f"   {f.servicio}/{f.entidad}: {f.rechazaria} de {f.total} se habrían rechazado")
        total_rechazos = sum(f.rechazaria for f in filas)
        lineas.append(f"   -> {'listo para on' if filas and total_rechazos == 0 else 'revisar antes de on'}")

        sin = (await conn.execute(SQL_SIN_DUENO)).one()
        lineas.append("2. Limpieza por dueños")
        lineas.append(f"   Archivos en uso sin dueño registrado: {sin.archivos} ({sin.bytes / 1048576:.1f} MB)")
        for f in (await conn.execute(SQL_DUENOS)).all():
            lineas.append(f"   {f.servicio}: {f.archivos} archivos con dueño ({f.asociaciones} asociaciones)")
        lineas.append(f"   -> {'listo para duenos' if sin.archivos == 0 else 'NO cambiar a duenos'}")

        lineas.append('3. Acceso directo de usuarios: docker logs satc-app-docs --since 168h 2>&1 '
                      '| grep -c "Acceso directo de usuario"  (tiene que dar 0)')
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dias", type=int, default=7)
    dias = parser.parse_args().dias

    async def _correr():
        try:
            return await generar(dias)
        finally:
            await engine.dispose()

    print(asyncio.run(_correr()))


if __name__ == "__main__":
    main()
