"""
Modelo U-Net++ con encoder ResNet34 y SCSE attention
Ubicación: /services/models/unet_model.py
"""
import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
from pathlib import Path

from config import get_settings
from utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)

class UNetPlusPlusSegmentationModel(nn.Module):
    """
    Modelo de segmentación basado en U-Net++ con encoder ResNet34

    Características:
    - Encoder: ResNet34 pre-entrenado en ImageNet
    - Decoder: U-Net++ con conexiones densas
    - Attention: SCSE (Spatial and Channel Squeeze & Excitation)
    - Input: 384x384 (mejor resolución que DeepLab)
    - Output: 5 clases (Background, Topwear, Lowerwear, Footwear, Body)
    """

    def __init__(self, n_classes: int, encoder_name: str = "resnet34"):
        super().__init__()

        logger.info(f"🚀 Construyendo U-Net++ con backbone {encoder_name}")
        logger.info("   -> Attention SCSE activada para mejor precisión")
        logger.info("   -> Resolución: 384x384 (mejor calidad)")

        self.model = smp.UnetPlusPlus(
            encoder_name=encoder_name,
            encoder_weights=None,  # El checkpoint incluye el encoder
            in_channels=3,
            classes=n_classes,
            activation=None,  # Logits puros para la loss
            decoder_attention_type="scse"  # Spatial and Channel Squeeze & Excitation
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

            # Cargar state_dict directamente (sin envoltura)
            state_dict = torch.load(checkpoint_path, map_location=device)

            # Verificar si es dict o OrderedDict directo
            if isinstance(state_dict, dict) and 'model_state_dict' in state_dict:
                state_dict = state_dict['model_state_dict']
                logger.info("✅ Checkpoint detectado (formato: model_state_dict)")

            # Verificar si necesita agregar prefijo "model."
            # El checkpoint puede tener claves como "encoder.conv1.weight"
            # pero el modelo espera "model.encoder.conv1.weight"
            if state_dict and not any(k.startswith('model.') for k in list(state_dict.keys())[:5]):
                logger.info("🔄 Agregando prefijo 'model.' a las claves del checkpoint")
                state_dict = {f'model.{k}': v for k, v in state_dict.items()}

            model.load_state_dict(state_dict)
            logger.info("✅ Checkpoint cargado correctamente")

            model.to(device)
            model.eval()

            params = model.count_parameters()
            logger.info(f"📊 Parámetros del modelo: {params:,}")

            return model

        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            raise
