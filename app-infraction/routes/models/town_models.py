from pydantic import BaseModel

class BusinessDaysRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str