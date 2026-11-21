"""Respuesta de descarga de archivos: rangos (Range/If-Range), tipos que se
pueden mostrar en el navegador y cabeceras de seguridad.

pdf.js pide los PDF por rangos y, en la primera respuesta (200), comprueba
``Accept-Ranges: bytes`` y ``Content-Length``; por eso ambas van siempre.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional

# Únicos tipos que se sirven ``inline`` con su content-type real. Todo lo demás
# va como ``attachment`` y application/octet-stream, para que el navegador no
# lo renderice en el origen de la app. SVG queda fuera a propósito (puede
# llevar scripts), aunque hoy no se acepte al subir.
TIPOS_INLINE = frozenset({"application/pdf", "image/jpeg", "image/png", "image/gif"})

TAMANO_BLOQUE = 256 * 1024

_RANGO = re.compile(r"^bytes=(\d*)-(\d*)$")


class RangoNoSatisfacible(Exception):
    """El rango pedido cae fuera del archivo (responder 416)."""


def parse_range(cabecera: Optional[str], tamano: int) -> Optional[tuple[int, int]]:
    """(inicio, fin) inclusivos del rango pedido, o None para servir el archivo
    completo: sin cabecera, sintaxis inválida o varios rangos (el RFC 9110
    permite ignorarlos). Lanza ``RangoNoSatisfacible`` si no cabe en el archivo."""
    if not cabecera or tamano <= 0:
        return None
    m = _RANGO.match(cabecera.strip().replace(" ", ""))
    if not m:
        return None
    inicio_txt, fin_txt = m.groups()
    if not inicio_txt and not fin_txt:
        return None
    if not inicio_txt:  # sufijo: los últimos N bytes
        sufijo = int(fin_txt)
        if sufijo == 0:
            raise RangoNoSatisfacible()
        return max(tamano - sufijo, 0), tamano - 1
    inicio = int(inicio_txt)
    if inicio >= tamano:
        raise RangoNoSatisfacible()
    fin = min(int(fin_txt), tamano - 1) if fin_txt else tamano - 1
    if fin < inicio:
        return None
    return inicio, fin


def etag(file_hash: str) -> str:
    """ETag fuerte: el SHA-256 del contenido ya identifica los bytes."""
    return f'"{file_hash}"'


def rango_vigente(if_range: Optional[str], etag_actual: str) -> bool:
    """If-Range: el rango solo aplica si el cliente tiene la misma versión."""
    return not if_range or if_range.strip() == etag_actual


def tipo_y_disposicion(content_type: Optional[str]) -> tuple[str, str]:
    """(content-type con el que se sirve, 'inline' | 'attachment')."""
    if content_type in TIPOS_INLINE:
        return content_type, "inline"
    return "application/octet-stream", "attachment"


def cabeceras_seguridad() -> dict[str, str]:
    return {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "private, no-cache",
    }


def iterar_objeto(respuesta) -> Iterator[bytes]:
    """Lee por bloques una respuesta de MinIO y la cierra al terminar (o si el
    cliente corta). Es síncrono: StreamingResponse lo corre en el threadpool."""
    try:
        yield from respuesta.stream(TAMANO_BLOQUE)
    finally:
        respuesta.close()
        respuesta.release_conn()
