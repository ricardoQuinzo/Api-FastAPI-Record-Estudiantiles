from fastapi import APIRouter, Depends
from db import get_connection

router = APIRouter()

@router.get(
    "/retroalimentaciones/{user_id}",
    summary="Historial de recomendaciones IA para el usuario.",
    description="Devuelve la lista de recomendaciones generadas por la IA (histórico)."
)
def historial_retroalimentacion(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT fecha, recomendacion
        FROM retroalimentaciones_ia_log
        WHERE id_usuario=%s
        ORDER BY fecha DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    return [{"fecha": str(fecha), "recomendacion": rec} for (fecha, rec) in rows]
