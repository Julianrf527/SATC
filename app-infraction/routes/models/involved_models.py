from pydantic import BaseModel

class InvolucradoExpedienteCreate(BaseModel):
    expediente_id: int
    involucrado_id: int