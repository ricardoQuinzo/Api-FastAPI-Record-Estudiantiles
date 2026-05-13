"""
Endpoints para logros: obtenidos y pendientes.
"""

from fastapi import APIRouter, Depends
from db import get_connection

router = APIRouter()

@router.get("/logros/{user_id}", summary="Logros obtenidos", description="Lista de logros ya conseguidos por el usuario.")
def get_logros_usuario(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT l.id_logro, l.nombre_logro, l.descripcion, l.icono_url, l.puntos_otorgados
        FROM usuarios_logros ul
        JOIN logros l ON ul.id_logro = l.id_logro
        WHERE ul.id_usuario = %s
    """, (user_id,))
    resultados = cursor.fetchall()
    cursor.close()
    return [
        {
            "id_logro": r[0],
            "nombre_logro": r[1],
            "descripcion": r[2],
            "icono_url": r[3],
            "puntos_otorgados": r[4]
        }
        for r in resultados
    ]

@router.get("/logros_pendientes/{user_id}", summary="Logros pendientes", description="Logros que el usuario aún no ha desbloqueado.")
def logros_pendientes(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT l.id_logro, l.nombre_logro, l.descripcion, l.icono_url
        FROM logros l
        WHERE l.id_logro NOT IN (
            SELECT id_logro FROM usuarios_logros WHERE id_usuario=%s
        )
    """, (user_id,))
    results = cursor.fetchall()
    cursor.close()
    return [
        {
            "id_logro": r[0],
            "nombre_logro": r[1],
            "descripcion": r[2],
            "icono_url": r[3]
        }
        for r in results
    ]
