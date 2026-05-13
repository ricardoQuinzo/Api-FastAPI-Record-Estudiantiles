# routers/progreso.py
from fastapi import APIRouter, HTTPException, Query
from db import get_connection
from utils.analisis_ia import procesar_feedback

router = APIRouter()

@router.get("/progreso/{user_id}")
def progreso(user_id: int, log: int = Query(1, description="1=guardar en histórico, 0=no")):
    conn = get_connection()
    cur = conn.cursor()

    # valida estudiante en Moodle (ajusta si tu check es distinto)
    cur.execute("""
        SELECT u.id
        FROM mdl_user u
        JOIN mdl_role_assignments ra ON ra.userid = u.id
        JOIN mdl_role r ON r.id = ra.roleid
        WHERE u.id=%s AND r.shortname='student' AND u.deleted=0 AND u.suspended=0
    """, (user_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Usuario no válido o no es estudiante")

    cur.execute("SELECT COALESCE(SUM(puntos_ganados),0) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    puntos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM usuarios_logros WHERE id_usuario=%s", (user_id,))
    logros = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM historial_recompensas WHERE id_usuario=%s", (user_id,))
    recompensas = cur.fetchone()[0]
    cur.execute("SELECT MAX(fecha_actividad) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    ultimo_acceso = cur.fetchone()[0]
    cur.close(); conn.close()

    # corre IA (guarda en feedback_ia + retroalimentaciones_ia_log)
    resultado = procesar_feedback(user_id, do_log=bool(log)) 

    return {
        "user_id": user_id,
        "resumen": {
            "puntos": int(puntos),
            "logros": int(logros),
            "recompensas": int(recompensas),
            "ultimo_acceso": str(ultimo_acceso) if ultimo_acceso else None
        },
        "ia": resultado["ia"]
    }
