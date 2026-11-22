"""
Paquete de servicios de negocio
"""
from .model_manager import model_manager
from .segmentation_service import SegmentationService

__all__ = ["model_manager", "SegmentationService"]
