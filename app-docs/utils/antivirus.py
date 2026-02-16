"""
Integración con ClamAV para escaneo de archivos
"""
import os
import logging
import subprocess
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuración de ClamAV
CLAMAV_HOST = os.getenv("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
CLAMAV_ENABLED = os.getenv("CLAMAV_ENABLED", "false").lower() == "true"


def verificar_clamav_disponible() -> bool:
    """
    Verifica si ClamAV está disponible y corriendo.
    
    Returns:
        True si ClamAV está disponible, False si no
    """
    if not CLAMAV_ENABLED:
        logger.info("ClamAV está deshabilitado en configuración")
        return False
    
    try:
        # Intentar conectar con clamd usando pyclamd
        import pyclamd
        cd = pyclamd.ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT)
        
        # Ping para verificar conexión
        if cd.ping():
            logger.info("ClamAV está disponible y respondiendo")
            return True
        else:
            logger.warning("ClamAV no responde al ping")
            return False
            
    except ImportError:
        logger.warning("pyclamd no está instalado. Instalar con: pip install pyclamd")
        return False
    except Exception as e:
        logger.warning(f"ClamAV no está disponible: {e}")
        return False


def escanear_archivo(file_data: bytes, filename: str) -> Dict[str, any]:
    """
    Escanea un archivo en busca de virus usando ClamAV.
    
    Args:
        file_data: Contenido del archivo en bytes
        filename: Nombre del archivo (para logging)
        
    Returns:
        Dict con:
        - ok: bool - True si el archivo está limpio
        - virus_encontrado: Optional[str] - Nombre del virus si se encuentra
        - mensaje: str - Mensaje descriptivo
        - escaneado: bool - True si se escaneó, False si ClamAV no está disponible
    """
    # Si ClamAV está deshabilitado, permitir el archivo
    if not CLAMAV_ENABLED:
        logger.info(f"ClamAV deshabilitado. Archivo {filename} se considera seguro.")
        return {
            "ok": True,
            "virus_encontrado": None,
            "mensaje": "Escaneo omitido (ClamAV deshabilitado)",
            "escaneado": False
        }
    
    try:
        import pyclamd
        
        # Conectar con ClamAV
        cd = pyclamd.ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT)
        
        # Escanear el archivo desde memoria
        resultado = cd.scan_stream(file_data)
        
        # Si resultado es None, el archivo está limpio
        if resultado is None:
            logger.info(f"Archivo limpio: {filename}")
            return {
                "ok": True,
                "virus_encontrado": None,
                "mensaje": "Archivo verificado y limpio",
                "escaneado": True
            }
        
        # Si hay resultado, se encontró un virus
        # resultado es un dict: {'stream': ('FOUND', 'Virus.Name')}
        virus_info = resultado.get('stream', ('UNKNOWN', 'UNKNOWN'))
        virus_nombre = virus_info[1] if len(virus_info) > 1 else 'Desconocido'
        
        logger.error(f"Virus detectado en {filename}: {virus_nombre}")
        return {
            "ok": False,
            "virus_encontrado": virus_nombre,
            "mensaje": f"Archivo infectado: {virus_nombre}",
            "escaneado": True
        }
        
    except ImportError:
        logger.warning("pyclamd no instalado. Permitiendo archivo sin escaneo.")
        return {
            "ok": True,
            "virus_encontrado": None,
            "mensaje": "Escaneo omitido (pyclamd no instalado)",
            "escaneado": False
        }
    except Exception as e:
        logger.error(f"Error durante escaneo de {filename}: {e}")
        
        # En caso de error, decidir política: ¿permitir o bloquear?
        # Por seguridad, se recomienda BLOQUEAR si ClamAV está habilitado pero falla
        if CLAMAV_ENABLED:
            return {
                "ok": False,
                "virus_encontrado": None,
                "mensaje": f"Error en escaneo: {str(e)}",
                "escaneado": False
            }
        else:
            # Si está deshabilitado, permitir
            return {
                "ok": True,
                "virus_encontrado": None,
                "mensaje": "Escaneo omitido (error en ClamAV)",
                "escaneado": False
            }


def obtener_version_clamav() -> Dict[str, any]:
    """
    Obtiene la versión de ClamAV instalada.
    
    Returns:
        Dict con información de versión o error
    """
    if not CLAMAV_ENABLED:
        return {
            "ok": False,
            "mensaje": "ClamAV está deshabilitado"
        }
    
    try:
        import pyclamd
        cd = pyclamd.ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT)
        version = cd.version()
        
        return {
            "ok": True,
            "version": version,
            "host": CLAMAV_HOST,
            "port": CLAMAV_PORT
        }
    except Exception as e:
        return {
            "ok": False,
            "mensaje": f"Error obteniendo versión: {e}"
        }


def escanear_archivo_desde_path(file_path: Path) -> Dict[str, any]:
    """
    Escanea un archivo desde su ruta en el filesystem.
    
    Args:
        file_path: Ruta del archivo a escanear
        
    Returns:
        Dict con resultado del escaneo
    """
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        return escanear_archivo(file_data, file_path.name)
        
    except Exception as e:
        logger.error(f"Error leyendo archivo para escaneo: {e}")
        return {
            "ok": False,
            "virus_encontrado": None,
            "mensaje": f"Error leyendo archivo: {str(e)}",
            "escaneado": False
        }
