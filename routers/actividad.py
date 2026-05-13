"""
Endpoints para actividades del usuario, incluyendo filtro por fechas.
"""

from fastapi import APIRouter, Depends, Query
from db import get_connection

router = APIRouter()

@router.get("/actividad_usuario/{user_id}", summary="Historial de actividad", description="Actividades realizadas por el usuario.")
def get_actividad_usuario(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT descripcion, fecha_actividad, puntos_ganados
        FROM actividad_usuario
        WHERE id_usuario = %s
        ORDER BY fecha_actividad DESC
    """, (user_id,))
    resultados = cursor.fetchall()
    cursor.close()
    return [
        {
            "descripcion": r[0],
            "fecha_actividad": str(r[1]),
            "puntos_ganados": r[2]
        }
        for r in resultados
    ]

@router.get("/actividad_usuario/{user_id}/rango", summary="Actividades por rango de fechas", description="Actividades del usuario en un rango de fechas (formato YYYY-MM-DD).")
def actividad_rango(user_id: int, db = Depends(get_connection),
                    fecha_inicio: str = Query(..., example="2024-07-01"),
                    fecha_fin: str = Query(..., example="2024-07-31")):
    cursor = db.cursor()
    cursor.execute("""
        SELECT descripcion, fecha_actividad, puntos_ganados
        FROM actividad_usuario
        WHERE id_usuario=%s AND fecha_actividad BETWEEN %s AND %s
        ORDER BY fecha_actividad DESC
    """, (user_id, fecha_inicio, fecha_fin))
    results = cursor.fetchall()
    cursor.close()
    return [
        {"descripcion": r[0], "fecha_actividad": str(r[1]), "puntos_ganados": r[2]}
        for r in results
    ]
