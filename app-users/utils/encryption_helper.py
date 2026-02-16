"""
Helper para encriptación de datos sensibles en PostgreSQL
Usa pgcrypto para AES-256 encryption/decryption
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Clave de encriptación desde .env
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY no configurada en .env - Requerida para encriptación de datos")


async def encrypt_field(db: AsyncSession, plaintext: str) -> bytes:
    """
    Encripta un campo de texto usando pgcrypto
    
    Args:
        db: Sesión de base de datos
        plaintext: Texto a encriptar
    
    Returns:
        bytes: Datos encriptados (bytea)
    
    Ejemplo:
        encrypted_email = await encrypt_field(db, "user@example.com")
    """
    if not plaintext:
        return None
    
    query = text("SELECT pgp_sym_encrypt(:plaintext, :key)")
    result = await db.execute(query, {"plaintext": plaintext, "key": ENCRYPTION_KEY})
    encrypted = result.scalar()
    
    return encrypted


async def decrypt_field(db: AsyncSession, ciphertext: bytes) -> Optional[str]:
    """
    Desencripta un campo bytea usando pgcrypto
    
    Args:
        db: Sesión de base de datos
        ciphertext: Datos encriptados (bytea)
    
    Returns:
        str: Texto desencriptado
    
    Ejemplo:
        email = await decrypt_field(db, usuario.correo_encrypted)
    """
    if not ciphertext:
        return None
    
    query = text("SELECT pgp_sym_decrypt(:ciphertext, :key)")
    try:
        result = await db.execute(query, {"ciphertext": ciphertext, "key": ENCRYPTION_KEY})
        decrypted = result.scalar()
        return decrypted
    except Exception as e:
        # Error de desencriptación (clave incorrecta o datos corruptos)
        raise ValueError(f"Error desencriptando datos: {str(e)}")


def hash_for_search(plaintext: str) -> str:
    """
    Genera hash SHA-256 para búsqueda de datos encriptados
    
    Args:
        plaintext: Texto original
    
    Returns:
        str: Hash hexadecimal (64 caracteres)
    
    Uso:
        # Almacenar
        usuario.correo_hash = hash_for_search(email.lower())
        
        # Buscar
        email_search = "user@example.com"
        email_hash = hash_for_search(email_search.lower())
        stmt = select(Usuario).where(Usuario.correo_hash == email_hash)
    """
    import hashlib
    return hashlib.sha256(plaintext.encode('utf-8')).hexdigest()


# ══════════════════════════════════════════════════════════════
# Funciones de Alto Nivel para Modelos
# ══════════════════════════════════════════════════════════════

async def save_encrypted_user(
    db: AsyncSession,
    numero_documento: str,
    correo: str,
    **other_fields
) -> dict:
    """
    Guarda usuario con campos encriptados
    
    Returns:
        dict con campos encriptados y hashes
    """
    return {
        "numero_documento_encrypted": await encrypt_field(db, numero_documento),
        "numero_documento_hash": hash_for_search(numero_documento),
        "correo_encrypted": await encrypt_field(db, correo.lower()),
        "correo_hash": hash_for_search(correo.lower()),
        **other_fields
    }


async def get_decrypted_user(db: AsyncSession, usuario) -> dict:
    """
    Obtiene datos de usuario desencriptados
    
    Args:
        usuario: Objeto Usuario con campos encriptados
    
    Returns:
        dict con campos desencriptados
    """
    return {
        "id": usuario.numero_documento,
        "numero_documento": await decrypt_field(db, usuario.numero_documento_encrypted) if hasattr(usuario, 'numero_documento_encrypted') else usuario.numero_documento,
        "correo": await decrypt_field(db, usuario.correo_encrypted) if hasattr(usuario, 'correo_encrypted') else usuario.correo,
        "primer_nombre": usuario.primer_nombre,
        "segundo_nombre": usuario.segundo_nombre,
        "primer_apellido": usuario.primer_apellido,
        "segundo_apellido": usuario.segundo_apellido,
        "rol_id": usuario.rol_id,
        "activo": usuario.activo
    }


# ══════════════════════════════════════════════════════════════
# Funciones de Búsqueda en Datos Encriptados
# ══════════════════════════════════════════════════════════════

async def find_user_by_email_encrypted(db: AsyncSession, email: str):
    """
    Busca usuario por email usando hash (búsqueda rápida indexada)
    
    Ejemplo:
        from db.models.usuario import Usuario
        from sqlalchemy import select
        
        email_hash = hash_for_search(email.lower())
        stmt = select(Usuario).where(Usuario.correo_hash == email_hash)
        result = await db.execute(stmt)
        usuario = result.scalar_one_or_none()
    """
    from db.models.usuario import Usuario
    from sqlalchemy import select
    
    email_hash = hash_for_search(email.lower())
    stmt = select(Usuario).where(Usuario.correo_hash == email_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_user_by_document_encrypted(db: AsyncSession, numero_documento: str):
    """
    Busca usuario por número de documento usando hash
    """
    from db.models.usuario import Usuario
    from sqlalchemy import select
    
    documento_hash = hash_for_search(numero_documento)
    stmt = select(Usuario).where(Usuario.numero_documento_hash == documento_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ══════════════════════════════════════════════════════════════
# Migración de Datos (Ejecutar una sola vez)
# ══════════════════════════════════════════════════════════════

async def migrate_existing_users_to_encrypted(db: AsyncSession, batch_size: int = 100):
    """
    Migra usuarios existentes a formato encriptado
    
    Uso:
        # Ejecutar una sola vez
        from utils.encryption_helper import migrate_existing_users_to_encrypted
        await migrate_existing_users_to_encrypted(db)
    
    ADVERTENCIA: Solo ejecutar en migración inicial
    """
    from db.models.usuario import Usuario
    from sqlalchemy import select, update
    
    # Obtener usuarios sin encriptar
    stmt = select(Usuario).where(Usuario.correo_encrypted == None)
    result = await db.execute(stmt)
    usuarios = result.scalars().all()
    
    total = len(usuarios)
    print(f"Migrando {total} usuarios a formato encriptado...")
    
    migrated = 0
    for usuario in usuarios:
        try:
            # Encriptar campos
            usuario.numero_documento_encrypted = await encrypt_field(db, usuario.numero_documento)
            usuario.numero_documento_hash = hash_for_search(usuario.numero_documento)
            usuario.correo_encrypted = await encrypt_field(db, usuario.correo.lower())
            usuario.correo_hash = hash_for_search(usuario.correo.lower())
            
            migrated += 1
            
            if migrated % batch_size == 0:
                await db.commit()
                print(f"  Progreso: {migrated}/{total} ({migrated*100//total}%)")
        
        except Exception as e:
            print(f"  Error migrando usuario {usuario.numero_documento}: {e}")
            await db.rollback()
    
    await db.commit()
    print(f"✅ Migración completada: {migrated}/{total} usuarios")


# ══════════════════════════════════════════════════════════════
# NOTAS DE USO
# ══════════════════════════════════════════════════════════════

"""
USO EN MODELOS SQLAlchemy:

# db/models/usuario.py
from sqlalchemy import Column, String, LargeBinary

class Usuario(Base):
    __tablename__ = "usuarios"
    
    # Campos originales (mantener por compatibilidad)
    numero_documento = Column(String(20), primary_key=True)
    correo = Column(String(100), unique=True, nullable=False)
    
    # Campos encriptados (nuevos)
    numero_documento_encrypted = Column(LargeBinary, nullable=True)
    correo_encrypted = Column(LargeBinary, nullable=True)
    
    # Hashes para búsqueda rápida
    numero_documento_hash = Column(String(64), index=True)
    correo_hash = Column(String(64), index=True, unique=True)


USO EN RUTAS:

# routes/auth.py
from utils.encryption_helper import find_user_by_email_encrypted, get_decrypted_user

@router.post("/login")
async def login(data: LoginData, db: AsyncSession = Depends(get_db)):
    # Buscar por email encriptado (usando hash indexado)
    usuario = await find_user_by_email_encrypted(db, data.email)
    
    if not usuario:
        raise HTTPException(401, "Usuario no encontrado")
    
    # Obtener datos desencriptados
    user_data = await get_decrypted_user(db, usuario)
    
    # ...resto de lógica de login


CREACIÓN DE USUARIO:

# routes/user.py
from utils.encryption_helper import save_encrypted_user

@router.post("/register")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Preparar datos encriptados
    encrypted_data = await save_encrypted_user(
        db,
        numero_documento=data.numero_documento,
        correo=data.email,
        primer_nombre=data.primer_nombre,
        # ...otros campos
    )
    
    nuevo_usuario = Usuario(**encrypted_data)
    db.add(nuevo_usuario)
    await db.commit()


MIGRACIÓN RED LOCAL:

Para red local, la encriptación protege contra:
- Robo físico de servidores/discos
- Acceso no autorizado a backups
- Inspección de bases de datos por personal no autorizado
- Cumplimiento normativo (GDPR, ISO 27001)

Impacto en rendimiento:
- Encriptación: ~1-2ms por operación
- Búsquedas: Sin impacto (usan hash indexado)
- Desencriptación para mostrar: ~1-2ms

Total: ~2-4ms adicional por request (aceptable en red local)
"""
