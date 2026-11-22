"""
Gestor centralizado de modelos (Singleton)
Ubicación: /services/model_manager.py
"""
import torch
from pathlib import Path
from typing import Optional
from ultralytics import YOLO

from config import get_settings
from utils.logger import setup_logger
from services.models.segmentation_model import ProfessionalSegmentationModel
from services.models.unet_model import UNetPlusPlusSegmentationModel

settings = get_settings()
logger = setup_logger(__name__)

class ModelManager:
    """
    Singleton para gestionar la carga y acceso a los modelos
    Evita cargar modelos múltiples veces en memoria
    """

    _instance: Optional['ModelManager'] = None
    _seg_model: Optional[ProfessionalSegmentationModel] = None
    _yolo_model: Optional[YOLO] = None
    _device: Optional[torch.device] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._device is None:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"🖥️  Dispositivo detectado: {self._device}")

    def load_models(self):
        """Carga todos los modelos necesarios"""
        self._load_segmentation_model()
        self._load_yolo_model()

    def _load_segmentation_model(self):
        """Carga el modelo de segmentación"""
        if self._seg_model is not None:
            logger.warning("⚠️ Modelo de segmentación ya está cargado")
            return

        model_path = Path(settings.MODEL_DIR) / settings.SEG_MODEL_NAME

        if not model_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")

        try:
            # Seleccionar el modelo según la configuración
            if settings.SEG_MODEL_TYPE == "unet++":
                logger.info("🔧 Cargando modelo U-Net++ custom...")
                self._seg_model = UNetPlusPlusSegmentationModel.load_from_checkpoint(
                    checkpoint_path=model_path,
                    device=self._device
                )
            else:
                logger.info("🔧 Cargando modelo DeepLabV3+...")
                self._seg_model = ProfessionalSegmentationModel.load_from_checkpoint(
                    checkpoint_path=model_path,
                    device=self._device
                )

            logger.info("✅ Modelo de segmentación listo")
        except Exception as e:
            logger.error(f"❌ Error cargando modelo de segmentación: {e}")
            raise

    def _load_yolo_model(self):
        """Carga el modelo YOLO para tracking"""
        if self._yolo_model is not None:
            logger.warning("⚠️ Modelo YOLO ya está cargado")
            return

        model_path = Path(settings.MODEL_DIR) / settings.YOLO_MODEL_NAME

        try:
            self._yolo_model = YOLO(str(model_path))
            logger.info("✅ Modelo YOLO listo")
        except Exception as e:
            logger.error(f"❌ Error cargando YOLO: {e}")
            raise

    @property
    def segmentation_model(self) -> ProfessionalSegmentationModel:
        """Obtiene el modelo de segmentación"""
        if self._seg_model is None:
            raise RuntimeError("Modelo de segmentación no cargado. Llama a load_models() primero.")
        return self._seg_model

    @property
    def yolo_model(self) -> YOLO:
        """Obtiene el modelo YOLO"""
        if self._yolo_model is None:
            raise RuntimeError("Modelo YOLO no cargado. Llama a load_models() primero.")
        return self._yolo_model

    @property
    def device(self) -> torch.device:
        """Obtiene el dispositivo actual"""
        return self._device

    def unload_models(self):
        """Libera memoria de los modelos"""
        self._seg_model = None
        self._yolo_model = None
        torch.cuda.empty_cache()
        logger.info("🗑️  Modelos descargados de memoria")

# Instancia global
model_manager = ModelManager()
