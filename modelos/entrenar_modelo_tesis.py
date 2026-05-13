import os
import pickle
import mysql.connector
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

# ----------------------------
# 1) Conexión a la BD
# ----------------------------
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'moodle'),
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# ----------------------------
# 2) Consulta SQL real
# ----------------------------
query = """
SELECT u.id AS user_id,
       COALESCE(SUM(l.puntos_otorgados), 0) AS puntos,
       COUNT(DISTINCT ul.id_logro) AS n_logros,
       COUNT(DISTINCT DATE(au.fecha_actividad)) AS dias_activo,
       COALESCE(un.id_nivel, 1) AS id_nivel
FROM mdl_user u
LEFT JOIN usuarios_logros ul ON ul.id_usuario = u.id
LEFT JOIN logros l ON l.id_logro = ul.id_logro
LEFT JOIN actividad_usuario au ON au.id_usuario = u.id
LEFT JOIN (
    SELECT t.id_usuario,
           SUBSTRING_INDEX(GROUP_CONCAT(t.id_nivel ORDER BY t.fecha_asignacion DESC), ',', 1) AS id_nivel
    FROM usuarios_niveles t
    GROUP BY t.id_usuario
) un ON un.id_usuario = u.id
GROUP BY u.id, un.id_nivel
"""

cursor.execute(query)
rows = cursor.fetchall()
cursor.close()
conn.close()

df = pd.DataFrame(rows, columns=['user_id', 'puntos', 'n_logros', 'dias_activo', 'id_nivel'])
print(f"📊 Registros cargados: {len(df)}")

# ----------------------------
# 3) Conversión a float/int
# ----------------------------
num_cols = ['puntos', 'n_logros', 'dias_activo', 'id_nivel']
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

df['id_nivel'] = df['id_nivel'].round().astype(int)
print(df.dtypes)

# ----------------------------
# 4) Preparar variables
# ----------------------------
nivel_map = {1: 0, 2: 1, 3: 2}
y = df['id_nivel'].map(nivel_map).fillna(0).astype(int).values
X = df[['puntos', 'n_logros', 'dias_activo']].values

# Fallback si solo hay una clase
clases_unicas = np.unique(y)
if len(clases_unicas) < 2:
    print("Solo se detectó una clase; aplicando fallback por percentiles.")
    p33 = df['puntos'].quantile(0.33)
    p66 = df['puntos'].quantile(0.66)

    def by_percentile(p):
        if p < p33: return 0
        elif p < p66: return 1
        else: return 2

    y = df['puntos'].apply(by_percentile).astype(int).values


pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(max_iter=500))
])

counts = np.bincount(y)
min_class = int(counts[counts > 0].min())
cv_splits = max(2, min(5, min_class))

if len(np.unique(y)) >= 2 and cv_splits >= 2:
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv)
    acc_cv = float(scores.mean())
    print(f"✅ Exactitud (CV {cv_splits} folds): {acc_cv:.3f}")
else:
    acc_cv = None
    print("ℹ️ No se pudo hacer CV estratificado (muy pocas clases).")


sss = StratifiedShuffleSplit(n_splits=1, test_size=max(0.2, 1/len(y)), random_state=42)
for train_idx, test_idx in sss.split(X, y):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]


pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

labels_full = [0, 1, 2]
names_full = ['Básico', 'Intermedio', 'Avanzado']

rep = classification_report(
    y_test, y_pred,
    labels=labels_full,
    target_names=names_full,
    zero_division=0
)
print("\n📄 Reporte de clasificación:\n", rep)

mensajes = {
    0: "Estás en nivel Básico. Te sugerimos completar más actividades para subir.",
    1: "Estás en nivel Intermedio. Buen trabajo, sigue así para llegar a Avanzado.",
    2: "¡Excelente! Estás en nivel Avanzado. Mantén tu rendimiento y apoya a otros."
}

payload = {
    "modelo": pipeline,
    "accuracy_cv": acc_cv,
    "mensajes": mensajes,
    "labels": {0: "Básico", 1: "Intermedio", 2: "Avanzado"}
}

out = os.path.join(os.path.dirname(__file__), "modelo_tesis.pkl")
with open(out, "wb") as f:
    pickle.dump(payload, f)

print(f" Guardado: {out}")
