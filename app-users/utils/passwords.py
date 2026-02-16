from passlib.hash import bcrypt as passlib_bcrypt
import bcrypt as raw_bcrypt
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

# Thread pool para operaciones bcrypt (CPU-bound)
# CRÍTICO: 4 workers = serialización controlada (evita CPU thrashing)
# Con 50 logins: 50/4 = 12.5 batches × 100ms = 1.25s teórico
_executor = ThreadPoolExecutor(max_workers=4)

# Configuración de bcrypt rounds desde .env
# Desarrollo: 3-5 rounds (~50ms)
# Producción: 10-12 rounds (~300ms)
# Red local: 8-10 rounds (balance seguridad/performance)
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))


def _truncate_to_72_bytes(password: str) -> bytes:
    """Return UTF-8 bytes truncated to 72 bytes (bcrypt limit).

    We slice the encoded bytes and drop any partial multi-byte sequences by
    decoding with 'ignore' if needed when converting back to str for
    passlib usage. For direct `bcrypt` calls we use the bytes slice.
    """
    if password is None:
        return b""
    b = password.encode("utf-8")[:72]
    return b


def hash_password(password: str) -> str:
    """Hash a password with bcrypt, using passlib when possible.

    Falls back to using the `bcrypt` package directly if passlib encounters
    backend/version issues (some platforms have incompatible `bcrypt` builds).
    """
    if password is None:
        raise ValueError("Password is required")

    # Try passlib first (higher-level API)
    try:
        truncated = _truncate_to_72_bytes(password).decode("utf-8", errors="ignore")
        # Usar rounds configurado desde .env
        # Producción/Red Local: 10 rounds = 1024 iteraciones (~300ms por hash)
        # Desarrollo: 3 rounds = 8 iteraciones (~50ms por hash)
        return passlib_bcrypt.using(rounds=BCRYPT_ROUNDS).hash(truncated)
    except Exception:
        # Fallback to raw bcrypt con rounds configurados
        pw_bytes = _truncate_to_72_bytes(password)
        hashed = raw_bcrypt.hashpw(pw_bytes, raw_bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
        return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hashed value with safe truncation and fallbacks."""
    if password is None or hashed is None:
        return False

    # Try passlib first
    try:
        truncated = _truncate_to_72_bytes(password).decode("utf-8", errors="ignore")
        return passlib_bcrypt.verify(truncated, hashed)
    except ValueError:
        # Specific case where underlying bcrypt rejects >72 bytes
        pass
    except Exception:
        # Any other passlib/backend issues fall back to raw bcrypt
        pass

    # Fallback: use raw bcrypt.checkpw with truncated bytes
    try:
        pw_bytes = _truncate_to_72_bytes(password)
        return raw_bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


async def verify_password_async(password: str, hashed: str) -> bool:
    """
    Versión ASYNC de verify_password - ejecuta bcrypt en thread pool.
    
    Esto evita bloquear el event loop, permitiendo procesar múltiples
    logins concurrentes sin esperas. Crítico para rendimiento bajo carga.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, verify_password, password, hashed)
