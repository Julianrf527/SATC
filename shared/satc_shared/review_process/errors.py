"""Errores del proceso de revisión. No dependen de FastAPI: cada uno trae el
``status_code`` HTTP sugerido para que la app lo traduzca a ``HTTPException``::

    except ReviewError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
"""


class ReviewError(Exception):
    status_code: int = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class ProcesoNoEncontrado(ReviewError):
    status_code = 404


class PermisoDenegado(ReviewError):
    status_code = 403


class TransicionInvalida(ReviewError):
    """La acción no aplica en el estado actual del proceso."""

    status_code = 400


class ValidacionError(ReviewError):
    """Datos inválidos: comentario faltante, extensión, regla del flujo..."""

    status_code = 400


class VersionDuplicada(ReviewError):
    status_code = 409


class ErrorUsoArchivo(ReviewError):
    """No se pudo registrar ``numero_usos`` en app-docs. Se lanza ANTES del
    commit para que la app haga rollback: un archivo referenciado con
    numero_usos=0 sería borrado por la limpieza nocturna."""

    status_code = 502
