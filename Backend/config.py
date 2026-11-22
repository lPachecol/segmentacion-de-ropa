"""
Configuración centralizada del backend
Ubicación: /config.py
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # === BASE ===
    APP_NAME: str = "Backend Segmentación Ropa"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # === SERVER ===
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # === DATABASE ===
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "fashion_analytics"
    COLLECTION_NAME: str = "historial_personas"
    USERS_COLLECTION: str = "usuarios"

    # === AUTENTICACIÓN ===
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # === MODELOS ===
    MODEL_DIR: str = "./models"
    SEG_MODEL_NAME: str = "mejor_modelo_384_fixed_body.pth"  # U-Net++ custom
    SEG_MODEL_TYPE: str = "unet++"  # Tipo: "unet++" o "deeplabv3+"
    YOLO_MODEL_NAME: str = "yolov8n.pt"
    ENCODER_NAME: str = "resnet34"
    NUM_CLASSES: int = 5

    # === PROCESAMIENTO ===
    INPUT_SIZE: int = 384  # Cambiado de 256 a 384 para U-Net++
    YOLO_CONFIDENCE: float = 0.5
    MIN_BOX_SIZE: int = 10
    GARMENT_THRESHOLD: float = 0.015  # 1.5% del área
    JPEG_QUALITY: int = 70
    PAD_RATIO: float = 0.5  # Padding alrededor del ROI para dar contexto
    MIN_GARMENT_PIXELS_RATIO: float = 0.002  # 0.2% mínimo de píxeles para considerar recorte
    USE_TTA: bool = True  # Test Time Augmentation con flip horizontal

    # === SEGMENTACIÓN ===
    IMAGENET_MEAN: list = [0.485, 0.456, 0.406]
    IMAGENET_STD: list = [0.229, 0.224, 0.225]

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Singleton para obtener settings"""
    return Settings()
