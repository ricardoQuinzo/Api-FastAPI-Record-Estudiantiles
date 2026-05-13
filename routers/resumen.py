from fastapi import APIRouter, Depends, HTTPException
from db import get_connection

router = APIRouter()

@router.get("/resumen/{user_id}", summary="Resumen rápido del usuario", description="Devuelve puntos, total logros, días activos y último acceso del usuario.")
def resumen_usuario(user_id: int, db = Depends(get_connection)):
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM mdl_user WHERE id=%s", (user_id,))
    if not cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    cursor.execute("SELECT COALESCE(SUM(puntos_ganados),0) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    puntos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM usuarios_logros WHERE id_usuario=%s", (user_id,))
    total_logros = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT fecha_actividad) FROM actividad_usuario
        WHERE id_usuario=%s AND fecha_actividad >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """, (user_id,))
    dias_activos = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(fecha_actividad) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    ultimo = cursor.fetchone()[0]

    cursor.close()
    return {
        "user_id": user_id,
        "puntos_totales": puntos,
        "total_logros": total_logros,
        "dias_activos_ultima_semana": dias_activos,
        "ultimo_acceso": str(ultimo) if ultimo else None
    }
