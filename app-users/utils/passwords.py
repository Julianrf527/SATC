from passlib.hash import bcrypt as passlib_bcrypt
import bcrypt as raw_bcrypt
import asyncio
import os
import random
import string
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

# bcrypt es CPU-bound: se acota a 4 workers para serializar de forma controlada
# y no saturar la CPU cuando entran muchos logins a la vez.
_executor = ThreadPoolExecutor(max_workers=4)

# Coste configurable por entorno: ~50ms con 3-5 rounds (desarrollo),
# ~300ms con 10-12 (producción).
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))


def _truncate_to_72_bytes(password: str) -> bytes:
    """Bytes UTF-8 truncados a 72, que es el máximo que acepta bcrypt."""
    if password is None:
        return b""
    b = password.encode("utf-8")[:72]
    return b


def hash_password(password: str) -> str:
    """Hashea con passlib, cayendo a `bcrypt` directo si passlib falla.

    El fallback existe porque algunas plataformas traen builds de `bcrypt`
    incompatibles con el backend de passlib.
    """
    if password is None:
        raise ValueError("Password is required")

    try:
        truncated = _truncate_to_72_bytes(password).decode("utf-8", errors="ignore")
        return passlib_bcrypt.using(rounds=BCRYPT_ROUNDS).hash(truncated)
    except Exception:
        pw_bytes = _truncate_to_72_bytes(password)
        hashed = raw_bcrypt.hashpw(pw_bytes, raw_bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
        return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verifica la contraseña, con truncado seguro y fallback a bcrypt directo."""
    if password is None or hashed is None:
        return False

    try:
        truncated = _truncate_to_72_bytes(password).decode("utf-8", errors="ignore")
        return passlib_bcrypt.verify(truncated, hashed)
    except ValueError:
        pass
    except Exception:
        pass

    try:
        pw_bytes = _truncate_to_72_bytes(password)
        return raw_bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


async def verify_password_async(password: str, hashed: str) -> bool:
    """Corre verify_password en el thread pool para no bloquear el event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, verify_password, password, hashed)


def generate_temp_password(length: int = 10) -> str:
    """Genera una contraseña temporal: 1 mayúscula, 2 dígitos, 1 símbolo y el resto alfanumérico, mezclados."""
    mayuscula = random.choice(string.ascii_uppercase)
    numeros = random.choices(string.digits, k=2)
    simbolo = random.choice("!@#$%^&*()-_=+?¿¡[]{}<>")

    restantes = length - (1 + 2 + 1)
    otros = random.choices(string.ascii_letters + string.digits, k=restantes)

    cont_list = list(mayuscula + "".join(numeros) + simbolo + "".join(otros))
    random.shuffle(cont_list)
    return "".join(cont_list)
