from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class InvolucradoCreate(BaseModel):
    """Modelo para crear un nuevo involucrado."""
    
    numero_documento: int = Field(
        ..., 
        gt=0,
        description="Número de documento de identidad"
    )
    digito_verificacion: Optional[str] = Field(
        None, 
        max_length=2,
        description="Dígito de verificación (solo para NIT)"
    )
    tipo_documento: str = Field(
        ..., 
        max_length=20,
        description="Tipo de documento (CC, NIT, CE, etc.)"
    )
    nombre: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="Nombre completo o razón social"
    )
    celular: Optional[int] = Field(
        None,
        gt=0,
        description="Número de celular (solo dígitos)"
    )
    correo: Optional[EmailStr] = Field(
        None,
        description="Correo electrónico"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=200,
        description="Dirección de residencia o notificación"
    )

    @field_validator('celular')
    @classmethod
    def validate_celular(cls, v):
        if v is None:
            return v
        celular_str = str(v)
        if len(celular_str) < 7 or len(celular_str) > 15:
            raise ValueError('El celular debe tener entre 7 y 15 dígitos')
        return v

    @field_validator('numero_documento')
    @classmethod
    def validate_documento(cls, v):
        """Valida que el número de documento tenga una longitud razonable."""
        doc_str = str(v)
        if len(doc_str) < 6 or len(doc_str) > 15:
            raise ValueError('El documento debe tener entre 6 y 15 dígitos')
        return v


class InvolucradoUpdate(BaseModel):
    """Modelo para actualizar un involucrado existente."""

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre completo o razón social"
    )
    numero_documento: Optional[int] = Field(
        None,
        gt=0,
        description="Nuevo número de documento (opcional, si se desea cambiar)"
    )
    tipo_documento: Optional[str] = Field(
        None,
        max_length=20,
        description="Nuevo tipo de documento (opcional, si se desea cambiar)"
    )
    celular: Optional[int] = Field(
        None,
        gt=0,
        description="Número de celular (solo dígitos)"
    )
    correo: Optional[EmailStr] = Field(
        None,
        description="Correo electrónico"
    )
    digito_verificacion: Optional[str] = Field(
        None,
        max_length=2,
        description="Dígito de verificación (solo para NIT)"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=200,
        description="Dirección de residencia o notificación"
    )

    @field_validator('celular')
    @classmethod
    def validate_celular(cls, v):
        if v is None:
            return v
        celular_str = str(v)
        if len(celular_str) < 7 or len(celular_str) > 15:
            raise ValueError('El celular debe tener entre 7 y 15 dígitos')
        return v

    @field_validator('numero_documento')
    @classmethod
    def validate_documento(cls, v):
        if v is None:
            return v
        doc_str = str(v)
        if len(doc_str) < 6 or len(doc_str) > 15:
            raise ValueError('El documento debe tener entre 6 y 15 dígitos')
        return v


class BulkInvolucradoRequest(BaseModel):
    """Modelo para solicitud de consulta masiva de involucrados."""
    
    ids: list[int] = Field(
        ...,
        min_length=1,
        description="Lista de IDs de involucrados a consultar"
    )
    tipo_documento: Optional[str] = Field(
        None,
        max_length=20,
        description="Filtro opcional por tipo de documento"
    )