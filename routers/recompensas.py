"""
Endpoints para recompensas obtenidas por el usuario.
"""

from fastapi import APIRouter, Depends
from db import get_connection

router = APIRouter()

@router.get("/recompensas_usuario/{user_id}", summary="Recompensas obtenidas", description="Lista de recompensas que el usuario ha recibido o canjeado.")
def get_recompensas_usuario(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT r.id_recompensa, r.nombre, r.descripcion, ru.fecha_otorgamiento
        FROM recompensas_usuarios ru
        JOIN recompensas r ON ru.id_recompensa = r.id_recompensa
        WHERE ru.id_usuario = %s
    """, (user_id,))
    resultados = cursor.fetchall()
    cursor.close()
    return [
        {
            "id_recompensa": r[0],
            "nombre": r[1],
            "descripcion": r[2],
            "fecha_otorgamiento": str(r[3])
        }
        for r in resultados
    ]
