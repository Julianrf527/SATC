from http.client import HTTPException

def verify_permission(token_data: dict, permiso: str) -> None:
    if permiso not in token_data["permisos"]:
        raise HTTPException(status_code=403, detail="No cuenta con permisos")