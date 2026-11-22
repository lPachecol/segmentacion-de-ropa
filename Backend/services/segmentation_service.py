"""
Servicio de procesamiento de segmentación
Ubicación: /services/segmentation_service.py
"""
import cv2
import numpy as np
import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2
from typing import Tuple, List

from config import get_settings
from constants import SEGMENT_COLORS, GARMENT_CLASSES
from utils.logger import setup_logger
from services.model_manager import model_manager

settings = get_settings()
logger = setup_logger(__name__)


class SegmentationService:
    """Servicio para procesar frames con segmentación y tracking"""

    def __init__(self):
        self.device = model_manager.device
        self.seg_model = model_manager.segmentation_model
        self.yolo_model = model_manager.yolo_model

        # Transform igual que camara_segmentation.py
        self.transform = A.Compose([
            A.Resize(settings.INPUT_SIZE, settings.INPUT_SIZE),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])

    def analyze_garments(self, mask_roi: np.ndarray) -> List[str]:
        """Detecta prendas presentes en la máscara"""
        garments: List[str] = []
        total_pixels = mask_roi.size
        threshold = total_pixels * settings.GARMENT_THRESHOLD

        for class_id, garment_name in GARMENT_CLASSES.items():
            pixel_count = np.count_nonzero(mask_roi == class_id)
            if pixel_count > threshold:
                garments.append(garment_name)
                logger.debug(
                    f"   -> {garment_name}: {pixel_count} píxeles ({pixel_count/total_pixels*100:.1f}%)"
                )

        return garments

    def get_dominant_color(self, crop: np.ndarray) -> str:
        """
        Obtiene el color dominante de un recorte de prenda (ignorando fondo blanco)

        Args:
            crop: Imagen BGR del recorte de prenda

        Returns:
            Color en formato hexadecimal (#RRGGBB)
        """
        if crop is None or crop.size == 0:
            return "#CCCCCC"  # Gris por defecto

        # Ignorar píxeles blancos (255, 255, 255) y cercanos
        lower_white = np.array([240, 240, 240])
        upper_white = np.array([255, 255, 255])
        white_mask = cv2.inRange(crop, lower_white, upper_white)

        # Invertir máscara para obtener píxeles NO blancos
        non_white_mask = cv2.bitwise_not(white_mask)

        # Aplicar máscara al crop
        non_white_pixels = crop[non_white_mask == 255]

        if len(non_white_pixels) == 0:
            return "#CCCCCC"  # Si todo es blanco, retornar gris

        # Calcular promedio de píxeles NO blancos (BGR)
        avg_color_bgr = non_white_pixels.mean(axis=0).astype(int)

        # Convertir BGR a RGB
        b, g, r = avg_color_bgr[0], avg_color_bgr[1], avg_color_bgr[2]

        # Convertir a hexadecimal
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        return hex_color

    def preprocess_roi(self, roi: np.ndarray) -> torch.Tensor:
        """Preprocesa ROI con albumentations"""
        img_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        transformed = self.transform(image=img_rgb)
        tensor = transformed["image"]
        return tensor.unsqueeze(0).to(self.device)

    def segment_roi(self, roi: np.ndarray) -> np.ndarray:
        """Segmenta un ROI BGR y devuelve máscara uint8 con índices de clase"""
        h, w = roi.shape[:2]
        tensor = self.preprocess_roi(roi)

        with torch.no_grad():
            out = self.seg_model(tensor)
            out_f = self.seg_model(torch.flip(tensor, dims=[3]))
            out_f = torch.flip(out_f, dims=[3])
            logits = (out + out_f) / 2.0
            mask = torch.argmax(logits, dim=1).squeeze().cpu().numpy().astype(np.uint8)

        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return mask

    def overlay_mask(self, roi: np.ndarray, mask: np.ndarray, alpha: float = 0.4) -> np.ndarray:
        """Superpone máscara coloreada sobre el ROI"""
        h, w = mask.shape
        color_rgb = SEGMENT_COLORS[np.clip(mask, 0, len(SEGMENT_COLORS) - 1)]
        color_bgr = cv2.cvtColor(color_rgb.reshape(1, -1, 3), cv2.COLOR_RGB2BGR).reshape(h, w, 3)

        mask_bool = mask > 0
        if not mask_bool.any():
            return roi

        roi[mask_bool] = cv2.addWeighted(roi[mask_bool], 1 - alpha, color_bgr[mask_bool], alpha, 0)
        return roi

    def extract_garments(self, roi: np.ndarray, mask: np.ndarray) -> dict:
        """Extrae prendas recortadas solo con píxeles de esa clase

        Args:
            roi: Región BGR de la persona
            mask: Máscara uint8 con índices de clase

        Returns:
            Dict con estructura: {
                "topwear": img_recortada_solo_topwear,
                "lowerwear": img_recortada_solo_lowerwear,
                "footwear": img_recortada_solo_footwear
            }
            Los píxeles que no pertenecen a la clase son blancos (255, 255, 255)
        """
        garments_crops = {"topwear": None, "lowerwear": None, "footwear": None}

        # Debug: ver clases presentes en la máscara
        unique_classes = np.unique(mask)
        logger.debug(f"Clases en máscara: {unique_classes}")

        for class_id, garment_name in GARMENT_CLASSES.items():
            # Convertir a lowercase para que coincida con las claves de garments_crops
            garment_name_lower = garment_name.lower()

            if garment_name_lower not in garments_crops:
                continue

            # Obtener máscara de esta clase específica
            class_mask = (mask == class_id).astype(np.uint8)
            pixel_count = np.count_nonzero(class_mask)

            logger.debug(f"  {garment_name_lower} (class_id={class_id}): {pixel_count} píxeles")

            # Si no hay píxeles de esta clase, continuar
            if pixel_count == 0:
                continue

            # Limpieza morfológica para reducir ruido
            kernel = np.ones((3, 3), np.uint8)
            class_mask = cv2.morphologyEx(class_mask, cv2.MORPH_OPEN, kernel, iterations=1)

            # Filtrar componentes pequeñas (connected components)
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(class_mask, connectivity=8)
            if num_labels > 1:
                min_pixels = int(class_mask.size * settings.MIN_GARMENT_PIXELS_RATIO)
                filtered = np.zeros_like(class_mask)
                for i in range(1, num_labels):
                    if stats[i, cv2.CC_STAT_AREA] >= min_pixels:
                        filtered[labels == i] = 1
                class_mask = filtered
                pixel_count = np.count_nonzero(class_mask)
                if pixel_count == 0:
                    logger.debug(f"  {garment_name_lower}: todas las componentes filtradas por pequeñas")
                    continue

            # Encontrar bounding box mínimo de esta clase
            contours, _ = cv2.findContours(class_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                logger.debug(f"  {garment_name_lower}: Sin contornos detectados")
                continue

            # Unir todos los contornos y obtener bbox
            all_points = np.vstack(contours)
            x, y, w, h = cv2.boundingRect(all_points)

            # Recortar la región
            if w > 0 and h > 0:
                # Recortar ROI y máscara al bbox
                roi_crop = roi[y:y+h, x:x+w].copy()
                mask_crop = class_mask[y:y+h, x:x+w]

                # Crear imagen con fondo blanco donde la máscara es 0
                crop_with_mask = np.ones_like(roi_crop) * 255  # Fondo blanco

                # Copiar solo los píxeles donde mask == class_id
                crop_with_mask[mask_crop == 1] = roi_crop[mask_crop == 1]

                garments_crops[garment_name_lower] = crop_with_mask
                logger.debug(f"  {garment_name_lower}: Recortado {w}x{h}px con máscara aplicada (post-limpieza)")
            else:
                logger.debug(f"  {garment_name_lower}: Bbox inválido {w}x{h}")

        return garments_crops

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Tuple[int, List[str]]]]:
        """Procesa un frame completo con tracking + segmentación híbrida

        Enfoque híbrido para mejor calidad:
        1. Segmenta la imagen completa una vez (mejor calidad)
        2. Usa YOLO solo para detectar bounding boxes
        3. Recorta prendas de cada persona desde la máscara completa
        """
        results = self.yolo_model.track(
            frame,
            persist=True,
            classes=[0],
            conf=settings.YOLO_CONFIDENCE,
            verbose=False,
        )

        if not results or len(results[0].boxes) == 0:
            return frame, []

        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)

        if results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        else:
            track_ids = [None] * len(boxes)

        persons_data: List[Tuple[int, List[str]]] = []
        h, w, _ = frame.shape

        # PASO 1: Para cada persona, recortar y segmentar en alta resolución
        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = box

            # Padding configurable para dar contexto (igual que camara_segmentation.py)
            pad = settings.PAD_RATIO
            dx = int((x2 - x1) * pad)
            dy = int((y2 - y1) * pad)

            x1p = max(0, x1 - dx)
            y1p = max(0, y1 - dy)
            x2p = min(w, x2 + dx)
            y2p = min(h, y2 + dy)

            # Clamp box sin padding
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            if (x2 - x1) < settings.MIN_BOX_SIZE or (y2 - y1) < settings.MIN_BOX_SIZE:
                continue

            # PASO 2: Recortar ROI y segmentar el recorte (mejor detalle)
            roi = frame[y1p:y2p, x1p:x2p]
            mask = self.segment_roi(roi)

            garments = self.analyze_garments(mask)

            if track_id is not None and garments:
                persons_data.append((track_id, garments))

            self.overlay_mask(roi, mask)
            frame[y1p:y2p, x1p:x2p] = roi

            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            if track_id is not None:
                label = f"ID {track_id}"
                if garments:
                    label += f": {', '.join(garments)}"

                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        return frame, persons_data
