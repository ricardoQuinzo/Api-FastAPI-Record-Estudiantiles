from fastapi import FastAPI
from routers import progreso, resumen, logros, recompensas, actividad, retroalimentacion, desafios
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Middleware de la plataforma",
    description="Conectado a base Moodle y análisis IA",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(progreso.router)
app.include_router(resumen.router)
app.include_router(logros.router)
app.include_router(recompensas.router)
app.include_router(actividad.router)
app.include_router(retroalimentacion.router)
app.include_router(desafios.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
