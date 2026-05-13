# utils/analisis_ia.py
import os
import random
import pickle
import numpy as np
import mysql.connector

# =========================
# Cargar modelo (Pipeline)
# =========================
MODELO_PATH = os.path.join(os.path.dirname(__file__), "../modelos/modelo_tesis.pkl")
with open(MODELO_PATH, "rb") as f:
    modelo_data = pickle.load(f)

modelo_ml = modelo_data["modelo"]                         # pipeline con scaler dentro
labels_map = modelo_data.get("labels", {0: "Básico", 1: "Intermedio", 2: "Avanzado"})
mensajes_por_nivel = modelo_data.get("mensajes", {
    0: ["Estás en nivel Básico. Completa más actividades para subir."],
    1: ["Nivel Intermedio. Buen trabajo, sigue así."],
    2: ["Nivel Avanzado. ¡Excelente!"]
})

# =========================
# Métricas desde la BD
# =========================
def _fetch_metricas_usuario(conn, user_id: int):
    """
    Devuelve: puntos, n_logros, dias_activo, dias_ultima (este último es para reglas, no para el modelo)
    Ajusta nombres de columnas si en tu BD cambian.
    """
    cur = conn.cursor()

    # Cambia a 'puntos_otorgados' si así se llama en tu tabla
    cur.execute("SELECT COALESCE(SUM(puntos_ganados), 0) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    puntos = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(DISTINCT id_logro) FROM usuarios_logros WHERE id_usuario=%s", (user_id,))
    n_logros = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(DISTINCT DATE(fecha_actividad)) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    dias_activo = cur.fetchone()[0] or 0

    # Solo para reglas:
    cur.execute("SELECT DATEDIFF(NOW(), MAX(fecha_actividad)) FROM actividad_usuario WHERE id_usuario=%s", (user_id,))
    dias_ultima = cur.fetchone()[0]
    dias_ultima = 999 if dias_ultima is None else int(dias_ultima)

    cur.close()
    return float(puntos), int(n_logros), int(dias_activo), int(dias_ultima)

# =========================
# IA + reglas
# =========================
def generar_recomendacion_ia(conn, user_id: int):
    """
    1) Lee métricas reales del usuario.
    2) Predice nivel con el modelo (usa [puntos, n_logros, dias_activo]).
    3) Construye un mensaje combinando IA + reglas.
    4) Devuelve también las probabilidades por clase.
    """
    puntos, n_logros, dias_activo, dias_ultima = _fetch_metricas_usuario(conn, user_id)

    # ---- Predicción robusta (maneja modelos con 2 o 3 clases) ----
    X = np.array([[puntos, n_logros, dias_activo]], dtype=float)

    proba = modelo_ml.predict_proba(X)[0]
    pred  = int(modelo_ml.predict(X)[0])

    # Orden real de clases del modelo
    classes = np.array(getattr(modelo_ml, "classes_", []))

    # Probabilidad de la clase predicha
    if classes.size:
        idxs = np.where(classes == pred)[0]
        if idxs.size:
            conf = float(proba[int(idxs[0])])
        else:
            idx = int(np.argmax(proba))
            conf = float(proba[idx])
            pred = int(classes[idx])
    else:
        idx = int(np.argmax(proba))
        conf = float(proba[idx])

    # ---- Probabilidades por clase como dict legible ----
    if classes.size:
        probabilidades = {
            labels_map.get(int(c), str(c)): round(float(p) * 100, 2)
            for c, p in zip(classes, proba)
        }
    else:
        # Fallback raro: enumerar posiciones
        probabilidades = {
            labels_map.get(i, str(i)): round(float(p) * 100, 2)
            for i, p in enumerate(proba)
        }

    # ---- Mensaje base por nivel ----
    msgs = mensajes_por_nivel.get(pred, mensajes_por_nivel.get(0, "Sigue practicando."))
    if isinstance(msgs, list) and msgs:
        msg_base = random.choice(msgs)
    else:
        msg_base = str(msgs)

    # ---- Reglas complementarias (no sustituyen la IA) ----
    reglas = []
    if puntos >= 500 and n_logros >= 3:
        reglas.append("Prueba desafíos avanzados y comparte tu estrategia con el grupo.")
    elif puntos >= 200:
        reglas.append("Mantén tu racha y considera retos semanales para acelerar tu progreso.")
    elif puntos > 0:
        reglas.append("Completa dos desafíos cortos hoy para sumar puntos rápidos.")
    else:
        reglas.append("Empieza por los desafíos introductorios y revisa la guía rápida.")
    if dias_ultima > 7:
        reglas.append("Vuelve a conectarte esta semana para no perder el ritmo.")

    mensaje = msg_base + (" " + " ".join(reglas) if reglas else "")
    if conf < 0.6:
        mensaje += " (ajustado con reglas por baja confianza del modelo)"

    nombre_nivel = labels_map.get(pred, f"Clase {pred}")
    promedio = int(round(conf * 100))  # 0..100

    # ⬇⬇⬇ ahora devolvemos 5 valores (incluye probabilidades)
    return mensaje, nombre_nivel, promedio, pred, probabilidades


# =========================
# Persistencia
# =========================
def guardar_feedback_ia(conn, user_id: int, nivel_txt: str, promedio: int, mensaje: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback_ia (id_usuario, nivel, promedio, mensaje)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          nivel=VALUES(nivel),
          promedio=VALUES(promedio),
          mensaje=VALUES(mensaje),
          fecha=CURRENT_TIMESTAMP
    """, (user_id, nivel_txt, int(promedio), mensaje))
    conn.commit()
    cur.close()

def _deberia_loguear(conn, user_id: int, mensaje: str, ventana_min: int = 5) -> bool:
    cur = conn.cursor()
    cur.execute("""
        SELECT recomendacion, fecha
        FROM retroalimentaciones_ia_log
        WHERE id_usuario=%s
        ORDER BY fecha DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return True
    ult_msg, ult_fecha = row
    if ult_msg != mensaje:
        return True

    cur = conn.cursor()
    cur.execute("SELECT TIMESTAMPDIFF(MINUTE, %s, NOW())", (ult_fecha,))
    mins = cur.fetchone()[0] or 999
    cur.close()
    return mins >= ventana_min

def guardar_retroalimentacion_log(conn, user_id: int, mensaje: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO retroalimentaciones_ia_log (id_usuario, recomendacion)
        VALUES (%s, %s)
    """, (user_id, mensaje))
    conn.commit()
    cur.close()


def procesar_feedback(user_id: int, do_log: bool = True):
    """
    Ejecuta IA y persiste resultados.
    - do_log=True: guarda en 'retroalimentaciones_ia_log' (histórico, anti-duplicados)
    - siempre hace upsert en 'feedback_ia' (último estado)
    """
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='moodle')
    try:
        mensaje, nivel_txt, promedio, clase, probabilidades = generar_recomendacion_ia(conn, user_id)

        if do_log and _deberia_loguear(conn, user_id, mensaje, ventana_min=5):
            guardar_retroalimentacion_log(conn, user_id, mensaje)

        guardar_feedback_ia(conn, user_id, nivel_txt, promedio, mensaje)

        return {
            "user_id": user_id,
            "ia": {
                "nivel": nivel_txt,           # "Básico/Intermedio/Avanzado"
                "clase": int(clase),          # 0 / 1 / 2
                "promedio": int(promedio),    # confianza en %
                "mensaje": mensaje,
                "probabilidades": probabilidades  # dict con % por clase
            }
        }
    finally:
        conn.close()

