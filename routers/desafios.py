# backend/routers/desafios.py
from fastapi import APIRouter, Query, HTTPException
from db import get_connection
from utils.analisis_ia import procesar_feedback

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

def tiene_columna(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
    """, (table, column))
    ok = cur.fetchone()[0] > 0
    cur.close()
    return ok

@router.get("/desafios")
def listar_desafios(nivel: str | None = Query(None), limit: int = 20, offset: int = 0):
    conn = get_connection()
    cur = conn.cursor(buffered=True)
    try:
        cols = "id, titulo, descripcion, nivel, puntos, enlace"
        order = "id DESC"
        if tiene_columna(conn, "desafios", "fecha_creacion"):
            cols += ", fecha_creacion"
            order = "fecha_creacion DESC, id DESC"

        if nivel:
            cur.execute(
                f"""
                SELECT {cols}
                FROM desafios
                WHERE nivel=%s
                ORDER BY {order}
                LIMIT %s OFFSET %s
                """,
                (nivel, int(limit), int(offset)),
            )
        else:
            cur.execute(
                f"""
                SELECT {cols}
                FROM desafios
                ORDER BY {order}
                LIMIT %s OFFSET %s
                """,
                (int(limit), int(offset)),
            )

        rows = cur.fetchall()          
        data = rows_to_dicts(cur, rows)
        return {"items": data, "count": len(data)}
    finally:
        cur.close()
        conn.close()


@router.get("/desafios/sugeridos/{user_id}")
def desafios_sugeridos(user_id: int, limit: int = 20, offset: int = 0):
    """
    Usa/actualiza feedback_ia y devuelve desafíos del nivel.
    procesar_feedback abre su propia conexión (no bloquea esta).
    """
    procesar_feedback(user_id, do_log=False)  # conexión independiente; no reusa la de abajo

    conn = get_connection()
    cur = conn.cursor(buffered=True)
    try:
        cur.execute("SELECT nivel FROM feedback_ia WHERE id_usuario=%s", (user_id,))
        row = cur.fetchone()        
        if not row:
            raise HTTPException(status_code=404, detail="No hay feedback de IA para el usuario.")
        nivel = row[0]

        cols = "id, titulo, descripcion, nivel, puntos, enlace"
        order = "id DESC"
        if tiene_columna(conn, "desafios", "fecha_creacion"):
            cols += ", fecha_creacion"
            order = "fecha_creacion DESC, id DESC"

        cur.execute(
            f"""
            SELECT {cols}
            FROM desafios
            WHERE nivel=%s
            ORDER BY {order}
            LIMIT %s OFFSET %s
            """,
            (nivel, int(limit), int(offset)),
        )

        rows = cur.fetchall()          
        data = rows_to_dicts(cur, rows)
        return {"nivel": nivel, "items": data, "count": len(data)}
    finally:
        cur.close()
        conn.close()


