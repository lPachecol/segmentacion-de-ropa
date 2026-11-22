"""
Paquete de modelos de ML
"""
from .segmentation_model import ProfessionalSegmentationModel
from .unet_model import UNetPlusPlusSegmentationModel

__all__ = ["ProfessionalSegmentationModel", "UNetPlusPlusSegmentationModel"]
