"""
Aplicación principal FastAPI
Ubicación: /main.py
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from config import get_settings
from utils.logger import setup_logger
from routes.api_segmentacion import router as api_router
from routes.auth import router as auth_router
from services.model_manager import model_manager
from database.mongo_client import mongodb

settings = get_settings()
logger = setup_logger(__name__, log_file="logs/app.log")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación
    - Startup: Carga modelos y conecta a BD
    - Shutdown: Libera recursos
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info(f" Iniciando {settings.APP_NAME} v{settings.VERSION}")
    logger.info("=" * 60)

    try:
        # Conectar a MongoDB
        await mongodb.connect()

        # Cargar modelos
        logger.info(" Cargando modelos...")
        model_manager.load_models()

        logger.info(" Aplicación lista para recibir peticiones")
        logger.info("=" * 60)

    except Exception as e:
        logger.critical(f" Error crítico durante el startup: {e}", exc_info=True)
        raise

    yield

    # === SHUTDOWN ===
    logger.info(" Cerrando aplicación...")

    try:
        # Descargar modelos
        model_manager.unload_models()

        # Cerrar MongoDB
        mongodb.close()

        logger.info(" Recursos liberados correctamente")

    except Exception as e:
        logger.error(f" Error durante shutdown: {e}", exc_info=True)

# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API de segmentación de prendas de vestir con tracking de personas",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth_router)  # Rutas de autenticación (login, register)
app.include_router(api_router)   # Rutas de segmentación

@app.get("/", tags=["root"])
async def root():
    """Endpoint raíz"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    logger.info(f" Servidor levantándose en {settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
