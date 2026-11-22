"""
Modelo de segmentación profesional con DeepLabV3+
Ubicación: /services/models/segmentation_model.py
"""
import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
from pathlib import Path

from config import get_settings
from utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)

class ProfessionalSegmentationModel(nn.Module):
    """
    Modelo de segmentación basado en DeepLabV3+ con encoder ResNet

    Características:
    - Módulo ASPP para captura de contexto multiescala
    - Ideal para diferenciar prendas largas vs cortas
    - Encoder pre-entrenado en ImageNet
    """

    def __init__(self, n_classes: int, encoder_name: str = "resnet34"):
        super().__init__()

        logger.info(f"🚀 Construyendo DeepLabV3+ con backbone {encoder_name}")
        logger.info("   -> Módulo ASPP activado para captura de contexto multiescala")

        self.model = smp.DeepLabV3Plus(
            encoder_name=encoder_name,
            encoder_weights=None,  # El checkpoint incluye el encoder
            in_channels=3,
            classes=n_classes,
            activation=None,  # Logits puros para la loss
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass del modelo"""
        return self.model(x)

    def count_parameters(self) -> int:
        """Cuenta parámetros entrenables"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    @classmethod
    def load_from_checkpoint(cls, checkpoint_path: Path, device: torch.device):
        """
        Carga modelo desde checkpoint

        Args:
            checkpoint_path: Ruta al archivo .pth
            device: Dispositivo (CPU/CUDA)

        Returns:
            Modelo cargado y en modo evaluación
        """
        model = cls(
            n_classes=settings.NUM_CLASSES,
            encoder_name=settings.ENCODER_NAME
        )

        try:
            logger.info(f"📂 Cargando checkpoint: {checkpoint_path}")
            checkpoint = torch.load(checkpoint_path, map_location=device)

            # Manejar diferentes formatos de checkpoint
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
                logger.info("✅ Checkpoint cargado (formato: model_state_dict)")
            else:
                model.load_state_dict(checkpoint)
                logger.info("✅ Checkpoint cargado (formato: state_dict directo)")

            model.to(device)
            model.eval()

            params = model.count_parameters()
            logger.info(f"📊 Parámetros del modelo: {params:,}")

            return model

        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            raise
