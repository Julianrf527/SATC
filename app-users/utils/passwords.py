from passlib.hash import bcrypt as passlib_bcrypt
import bcrypt as raw_bcrypt


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
        return passlib_bcrypt.hash(truncated)
    except Exception:
        # Fallback to raw bcrypt
        pw_bytes = _truncate_to_72_bytes(password)
        hashed = raw_bcrypt.hashpw(pw_bytes, raw_bcrypt.gensalt())
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
