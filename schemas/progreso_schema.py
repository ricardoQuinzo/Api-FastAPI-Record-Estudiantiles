
from pydantic import BaseModel

class RecomendacionResponse(BaseModel):
    id_usuario: int
    nivel: str
    recomendacion: str
