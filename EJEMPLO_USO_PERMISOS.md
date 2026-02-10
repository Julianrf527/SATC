# Guía de Uso del Sistema de Permisos

## Resumen de Cambios

Se ha implementado un sistema de seguridad mejorado que permite verificar permisos directamente desde el API Gateway sin consultar la base de datos en cada petición.

### Flujo de Autenticación y Permisos

1. **Login (app-users/auth.py)**
   - Usuario se autentica con email/password
   - Se genera un JWT firmado con `SECRET_KEY` (privada de app-users)
   - El JWT contiene: id, nombres, email, rol y **lista de permisos**
   - Se envía como cookie `access_token` al cliente

2. **API Gateway (api-gateway/main.py)**
   - Recibe requests con la cookie `access_token`
   - Decodifica el JWT usando `SECRET_KEY_GATEWAY` (compartida)
   - Extrae `user_id` y `permissions` del payload
   - Envía a microservicios mediante headers:
     - `X-Gateway-Token`: Token secreto del gateway
     - `X-Gateway-User-Id`: ID del usuario
     - `X-Gateway-Permissions`: JSON array con nombres de permisos

3. **Microservicios**
   - Reciben los headers y pueden:
     - Usar `verify_gateway_token(request)` → valida y retorna user_id
     - Usar `verify_permission(request, "nombre_![alt text](image.png)permiso")` → valida permiso y retorna user_id
     - Usar `get_user_permissions(request)` → obtiene lista de permisos

---

## Funciones Disponibles en Microservicios

### 1. `verify_gateway_token(request: Request) -> int`
Verifica que la petición venga del API Gateway y retorna el user_id.

**Uso:**
```python
from utils.verify_gateway_token import verify_gateway_token

@router.get("/ejemplo")
async def endpoint_simple(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = verify_gateway_token(request)
    # Continuar con la lógica...
```

### 2. `verify_permission(request: Request, required_permission: str) -> int`
Verifica que el usuario tenga un permiso específico. Lanza `HTTPException 403` si no lo tiene.

**Uso:**
```python
from utils.verify_gateway_token import verify_permission

@router.get("/admin-only")
async def endpoint_protegido(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Verifica permiso y retorna user_id si lo tiene
    user_id = verify_permission(request, "expediente_gestionar involucrados")
    # Solo llega aquí si tiene el permiso
```

### 3. `get_user_permissions(request: Request) -> list[str]`
Obtiene la lista completa de permisos del usuario.

**Uso:**
```python
from utils.verify_gateway_token import verify_gateway_token, get_user_permissions

@router.get("/condicional")
async def endpoint_condicional(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = verify_gateway_token(request)
    permissions = get_user_permissions(request)
    
    # Lógica condicional
    if "expediente_gestionar" in permissions:
        # Mostrar datos completos
    else:
        # Mostrar solo resumen
```

---

## Ejemplo Completo: Endpoint de Involucrados

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db.deps import get_db
from utils.verify_gateway_token import verify_permission

router = APIRouter()

# Endpoint que requiere permiso específico
@router.get("/involved/manage")
async def listar_involucrados_paginado(
    request: Request,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    # Verifica automáticamente el permiso "expediente_gestionar involucrados"
    # Si no lo tiene, lanza 403 Forbidden
    user_id = verify_permission(request, "expediente_gestionar involucrados")
    
    # Si llegamos aquí, el usuario tiene el permiso
    # Continuar con la lógica de paginación...
    
    return {
        "ok": True,
        "data": [...],
        "page": page,
        "totalPages": total_pages
    }

# Endpoint PUT para editar
@router.put("/involved/{id}")
async def editar_involucrado(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db)
):
    # También verifica el mismo permiso para editar
    user_id = verify_permission(request, "expediente_gestionar involucrados")
    
    # Lógica de edición...
    
    return {"ok": True, "message": "Actualizado correctamente"}
```

---

## Ventajas del Nuevo Sistema

✅ **Sin consultas a BD para permisos**: Los permisos vienen en el JWT, no se consulta la tabla `rol_permiso` en cada request

✅ **Validación centralizada**: El API Gateway decodifica una sola vez el JWT y distribuye la info

✅ **Cache inteligente**: Tokens se cachean 120 segundos en el gateway para mayor velocidad

✅ **Seguridad mejorada**: Dos claves secretas separadas (una para auth, otra para gateway)

✅ **Fácil de usar**: Una sola función `verify_permission()` en los endpoints

---

## Configuración de Variables de Entorno

### app-users/.env
```env
SECRET_KEY=kj39D!f82jd#sU29vL8pQxE7yMa4@wDl
SECRET_KEY_GATEWAY=Xp9Kl2Nm5Qr8Tv1Yw4Zb7Dc0Fg3Hj6Mk9Pn2Rs5Uv8Xy1
JWT_ALGORITHM=HS256
SECRET_GATEWAY=js877QE95l3H1Qq4OgGuEA0uZoRQLojG1EcGke7MtJE=
```

### api-gateway/.env
```env
SECRET_KEY_GATEWAY=Xp9Kl2Nm5Qr8Tv1Yw4Zb7Dc0Fg3Hj6Mk9Pn2Rs5Uv8Xy1
JWT_ALGORITHM=HS256
SECRET_GATEWAY=js877QE95l3H1Qq4OgGuEA0uZoRQLojG1EcGke7MtJE=
```

### app-sancionatoria/.env, app-docs/.env
```env
SECRET_GATEWAY=js877QE95l3H1Qq4OgGuEA0uZoRQLojG1EcGke7MtJE=
```

---

## Nombres de Permisos Disponibles

Basado en tu estructura actual:

### Usuarios
- `admin_registrar usuario`
- `admin_gestionar usuarios`
- `admin_roles y permisos`
- `admin_auditoria usuarios`

### Expedientes
- `expediente_gestionar`
- `expediente_consular`
- `expediente_alertas`
- `expediente_asignar encargados`
- `expediente_gestionar involucrados` ← **NUEVO**
- `admin_auditoria expedientes`

### Documentos
- `documento_gestionar`

---

## Migración de Endpoints Existentes

### Antes:
```python
@router.get("/endpoint")
async def ejemplo(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = verify_gateway_token(request)
    # No se verifica permiso específico
```

### Después (con verificación de permiso):
```python
@router.get("/endpoint")
async def ejemplo(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = verify_permission(request, "expediente_gestionar")
    # Ahora verifica automáticamente el permiso
```

---

## Testing

Para probar que funciona:

1. Hacer login con un usuario que tenga el permiso
2. Hacer request al endpoint protegido → debe funcionar
3. Hacer login con usuario sin el permiso
4. Hacer request al mismo endpoint → debe retornar 403 Forbidden

---

## Notas Importantes

⚠️ **SECRET_KEY vs SECRET_KEY_GATEWAY:**
- `SECRET_KEY`: Solo en app-users, firma los JWT en el login
- `SECRET_KEY_GATEWAY`: En app-users y api-gateway, permite al gateway leer los JWT

⚠️ **SECRET_GATEWAY:**
- Usado para autenticar requests entre gateway y microservicios
- Debe ser el mismo en todos los componentes

⚠️ **Formato del permiso:**
- Usar el nombre exacto como está en la tabla `permiso`
- Sensible a mayúsculas/minúsculas y espacios
