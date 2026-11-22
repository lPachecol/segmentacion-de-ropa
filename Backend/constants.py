"""
Constantes globales del proyecto
Ubicación: /constants.py
"""
import numpy as np

# === COLORES PARA VISUALIZACIÓN (RGB) ===
SEGMENT_COLORS = np.array([
    [0, 0, 0],         # 0: Background
    [255, 0, 127],     # 1: Topwear (Deep Pink)
    [0, 255, 255],     # 2: Lowerwear (Cyan)
    [255, 255, 0],     # 3: Footwear (Amarillo Neón)
    [50, 205, 50]      # 4: Body (Lime Green)
], dtype=np.uint8)

# === MAPEO DE CLASES ===
CLASS_NAMES = {
    0: "Background",
    1: "Topwear",
    2: "Lowerwear",
    3: "Footwear",
    4: "Body"
}

# Clases de prendas (excluye Background y Body)
GARMENT_CLASSES = {
    1: "Topwear",
    2: "Lowerwear",
    3: "Footwear"
}

# === MENSAJES ===
MSG_MONGO_CONNECTED = "💾 [Database] Conectado a MongoDB"
MSG_MONGO_ERROR = "❌ [Database] Error de conexión a MongoDB"
MSG_MODEL_LOADED = "✅ [Model] {} cargado exitosamente"
MSG_MODEL_ERROR = "❌ [Model] Error cargando {}: {}"
MSG_PROCESSING_ERROR = "⚠️ [Processing] Error procesando frame: {}"
