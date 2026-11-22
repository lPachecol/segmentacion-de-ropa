import cv2
import numpy as np
import torch
from ultralytics import YOLO
import albumentations as A
from albumentations.pytorch import ToTensorV2
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt

# ========================
# MATPLOTLIB INIT
# ========================
plt.ion()
fig, ax = plt.subplots(figsize=(8, 8))
img_plot = ax.imshow(np.zeros((480, 640, 3), dtype=np.uint8))
plt.axis("off")

running = True

def on_close(event):
    global running
    running = False

fig.canvas.mpl_connect('close_event', on_close)


# ========================
# CONFIG
# ========================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("🧠 Usando dispositivo:", DEVICE)
NUM_CLASSES = 5

CLASS_COLORS = [
    (0, 0, 0),        # 0 background
    (220, 20, 60),    # 1 topwear
    (30, 144, 255),   # 2 lowerwear
    (138, 43, 226),   # 3 footwear
    (46, 139, 87),    # 4 body
]

# ========================
# LOAD U-NET++
# ========================
model = smp.UnetPlusPlus(
    encoder_name="resnet34",
    encoder_weights=None,
    in_channels=3,
    classes=NUM_CLASSES,
    decoder_attention_type="scse"
).to(DEVICE)

print("📦 Cargando modelo...")
model.load_state_dict(torch.load("models/mejor_modelo_384_fixed_body.pth", map_location=DEVICE))
model.eval()
print("✅ Modelo cargado")

# ========================
# TRANSFORM
# ========================
transform = A.Compose([
    A.Resize(384, 384),
    A.Normalize(mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

# ========================
# SEGMENT FUNCTION
# ========================
def segment_crop(crop_bgr):
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    aug = transform(image=crop_rgb)["image"]
    x = aug.unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(x)
        pred = torch.argmax(logits, dim=1).squeeze().cpu().numpy()

    return pred  # 384x384

# ========================
# YOLO
# ========================
print("🤖 Cargando YOLO...")
yolo = YOLO("yolov8n.pt")

# ========================
# CAMERA
# ========================
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("❌ No se pudo abrir la cámara")
    exit()

print("✅ Cámara iniciada. Cierra la ventana para salir.")

# ========================
# LOOP
# ========================
while running:
    ret, frame = cap.read()
    if not ret:
        break

    img_out = frame.copy()

    results = yolo(frame, conf=0.4, verbose=False)

    person_id = 0

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) != 0:
                continue  # solo personas

            person_id += 1

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # ---- PAD ----
            h, w, _ = frame.shape
            pad = 0.25

            dx = int((x2 - x1) * pad)
            dy = int((y2 - y1) * pad)

            x1p = max(0, x1 - dx)
            y1p = max(0, y1 - dy)
            x2p = min(w, x2 + dx)
            y2p = min(h, y2 + dy)

            crop = frame[y1p:y2p, x1p:x2p]

            if crop.size == 0:
                continue

            # ---- SEGMENT ----
            mask_384 = segment_crop(crop)

            # ---- RESIZE BACK ----
            mask_crop = cv2.resize(
                mask_384.astype(np.uint8),
                (x2p - x1p, y2p - y1p),
                interpolation=cv2.INTER_NEAREST
            )

            # ---- COLORIZE ----
            overlay = crop.copy()
            for cls_idx, color in enumerate(CLASS_COLORS):
                overlay[mask_crop == cls_idx] = color

            blended = cv2.addWeighted(crop, 0.5, overlay, 0.5, 0)

            # ---- PUT BACK ----
            img_out[y1p:y2p, x1p:x2p] = blended

            # ---- DRAW BOX + ID ----
            cv2.rectangle(img_out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_out, f"ID {person_id}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # ========================
    # SHOW WITH MATPLOTLIB
    # ========================
    img_rgb = cv2.cvtColor(img_out, cv2.COLOR_BGR2RGB)
    img_plot.set_data(img_rgb)
    fig.canvas.draw_idle()
    plt.pause(0.001)

# ========================
# CLEAN
# ========================
cap.release()
plt.ioff()
plt.close()
