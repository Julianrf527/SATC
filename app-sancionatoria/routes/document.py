from fastapi import UploadFile, File, APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pathlib import Path
from datetime import datetime
import shutil
from urllib.parse import unquote
import logging
import pytz

#----- DB -----
from db.deps import get_db
from db.models.etapa import Etapa
from db.models.documento import Documento
from db.models.expediente import Expediente

router = APIRouter()
bogota_tz = pytz.timezone("America/Bogota")

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Subir a ApiCorp
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

#----------- LOGGER ------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from services.crud_file_operations import insert_log_auditoria

# ---------- ENDPOINTS ----------

@router.post("/new")
async def crear_documento(
    request: Request,
    radicado: str = Form(...),
    etapa_id: int = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    nombre: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un nuevo documento asociado a una etapa.
    """
    try:
        usuario_id = verify_gateway_token(request)
        # Validar que el archivo sea PDF
        if not file.content_type == "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF"
            )
        
        # Verificar que el expediente existe y que el usuario tiene permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )
        
        # Verificar que la etapa existe
        stmt = select(Etapa).where(Etapa.id == etapa_id)
        etapa = await db.scalar(stmt)
        
        if not etapa:
            raise HTTPException(status_code=404, detail="Etapa no encontrada")
        
        # 🔹 Crear directorio usando ruta absoluta
        expediente_path = DOCS_DIR / str(id_auxiliar)
        tipo_etapa_path = expediente_path / tipo_etapa
        tipo_etapa_path.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitizar el nombre del documento (remover caracteres especiales)
        nombre_sanitizado = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        nombre_sanitizado = nombre_sanitizado.replace(' ', '_')
        file_name = f"{nombre_sanitizado}_{timestamp}.pdf"
        file_path = tipo_etapa_path / file_name
        
        # Guardar archivo
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 🔹 Guardar ruta relativa en la BD
        url_documento_normalizada = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"
        
        # Crear registro en la base de datos
        nuevo_documento = Documento(
            nombre=nombre,
            url_documento=url_documento_normalizada,
            fecha_subida=datetime.now().date(),
            etapa_id=etapa_id
        )
        
        db.add(nuevo_documento)
        await db.commit()
        await db.refresh(nuevo_documento)
        
        return {
            "ok": True,
            "data": {
                "id": nuevo_documento.id,
                "nombre": nuevo_documento.nombre,
                "url_documento": nuevo_documento.url_documento,
                "fecha_subida": str(nuevo_documento.fecha_subida)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando documento: {e}")
        raise HTTPException(status_code=500, detail="Error al crear documento")

@router.put("/{documento_id}")
async def actualizar_documento(
    request:Request,
    documento_id: int,
    radicado: str = Form(...),
    etapa_id: int = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    nombre: str = Form(...),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        stmt = select(Documento).where(Documento.id == documento_id)
        documento = await db.scalar(stmt)

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        datos_anteriores = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "fecha_subida": str(documento.fecha_subida)
        }

        old_url = documento.url_documento
        old_file_path = BASE_DIR / old_url

        nombre_sanitizado = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        nombre_sanitizado = nombre_sanitizado.replace(' ', '_')

        tipo_etapa_path = DOCS_DIR / str(id_auxiliar) / tipo_etapa
        tipo_etapa_path.mkdir(parents=True, exist_ok=True)

        # Reemplazar archivo si se proporciona uno nuevo
        if file:
            if not file.content_type == "application/pdf":
                raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

            if old_file_path.exists():
                old_file_path.unlink()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_file_name = f"{nombre_sanitizado}_{timestamp}.pdf"
            new_file_path = tipo_etapa_path / new_file_name

            with new_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            documento.url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{new_file_name}"

        # Renombrar archivo existente si solo cambia el nombre
        else:
            if not old_file_path.exists():
                raise HTTPException(status_code=404, detail="Archivo original no encontrado")

            try:
                timestamp = old_file_path.stem.split("_")[-2] + "_" + old_file_path.stem.split("_")[-1]
            except IndexError:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            new_file_name = f"{nombre_sanitizado}_{timestamp}.pdf"
            new_file_path = tipo_etapa_path / new_file_name

            old_file_path.rename(new_file_path)

            documento.url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{new_file_name}"

        documento.nombre = nombre

        datos_nuevos = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "archivo_reemplazado": file is not None
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="documento",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de documento ID {documento_id}: '{nombre}'",
            expediente_radicado=radicado,
            id_registro=str(documento_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()
        await db.refresh(documento)

        return {
            "ok": True,
            "data": {
                "id": documento.id,
                "nombre": documento.nombre,
                "url_documento": documento.url_documento,
                "fecha_subida": str(documento.fecha_subida)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{documento_id}")
async def eliminar_documento(
    request: Request,
    documento_id: int,
    radicado: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )
        
        stmt = select(Documento).where(Documento.id == documento_id)
        documento = await db.scalar(stmt)
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        datos_anteriores = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "fecha_subida": str(documento.fecha_subida)
        }
        
        file_path = BASE_DIR / documento.url_documento
        if file_path.exists():
            file_path.unlink()
        
        await db.delete(documento)
        
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="documento",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de documento ID {documento_id}: '{documento.nombre}'",
            expediente_radicado=radicado,
            id_registro=str(documento_id),
            datos_anteriores=datos_anteriores
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )
        
        await db.commit()
        
        return {
            "ok": True,
            "message": "Documento eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def descargar_archivo(
    request: Request,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga o visualiza un documento PDF desde el servidor.
    """
    try:
        usuario_id = verify_gateway_token(request)
        # Decodificar ruta del query param (por si viene URL encoded)
        file_path = unquote(file_path)
        
        logger.info(f"[DOWNLOAD] Ruta recibida: {file_path}")

        # Normalizar ruta: si viene con prefijo uploads/expedientes/, quitarlo
        if file_path.startswith("uploads/expedientes/"):
            file_path = file_path.replace("uploads/expedientes/", "", 1)
        
        logger.info(f"[DOWNLOAD] Ruta normalizada: {file_path}")
        logger.info(f"[DOWNLOAD] DOCS_DIR: {DOCS_DIR}")

        # Construir ruta absoluta
        full_path = (DOCS_DIR / file_path).resolve()
        
        logger.info(f"[DOWNLOAD] Ruta completa: {full_path}")
        logger.info(f"[DOWNLOAD] Archivo existe: {full_path.exists()}")
        logger.info(f"[DOWNLOAD] Es archivo: {full_path.is_file() if full_path.exists() else 'N/A'}")

        # Validar que esté dentro de DOCS_DIR (seguridad)
        if not str(full_path).startswith(str(DOCS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Acceso no autorizado a esta ruta")

        # Validar existencia del archivo
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        # Extraer id_auxiliar (radicado interno) desde la ruta
        try:
            path_parts = Path(file_path).parts
            id_auxiliar = path_parts[0] if len(path_parts) > 0 else None
        except:
            id_auxiliar = None

        # Verificar permisos
        if id_auxiliar:
            stmt = select(Expediente.encargado_id).where(Expediente.id_auxiliar == int(id_auxiliar))
            encargado_id = await db.scalar(stmt)

            if not encargado_id:
                raise HTTPException(status_code=404, detail="Expediente no encontrado")

            if encargado_id != usuario_id:
                raise HTTPException(status_code=403, detail="No tiene permisos para acceder a este archivo")

        # Devolver PDF para visualizar en el navegador
        return FileResponse(
            path=str(full_path),
            media_type="application/pdf",
            filename=full_path.name,
            headers={
                "Content-Disposition": f'inline; filename="{full_path.name}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al descargar archivo: {e}")
