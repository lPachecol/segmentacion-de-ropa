"""
Endpoints de la API de segmentación
Ubicación: /routes/api_segmentacion.py
"""
from fastapi import APIRouter, File, UploadFile, Response, HTTPException, status, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import numpy as np
import cv2
import base64
import os
from pathlib import Path
from datetime import datetime
from typing import List
import zipfile
import io

from utils.logger import setup_logger
from services.segmentation_service import SegmentationService
from database.mongo_client import save_garment_extraction, get_extraction_history, get_extraction_analytics
from routes.auth import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/v1", tags=["segmentacion"])
logger = setup_logger(__name__)
settings = get_settings()
BODY_CLASS_ID = 4  # Clase 'Body' para aislar la persona y evitar mezcla de prendas

# Directorio para guardar imágenes extraídas
EXTRACTED_GARMENTS_DIR = Path("extracted_garments")
EXTRACTED_GARMENTS_DIR.mkdir(exist_ok=True)

def get_segmentation_service():
    """Obtiene la instancia del servicio de segmentación"""
    return SegmentationService()

@router.post(
    "/procesar_frame",
    summary="Procesa un frame con segmentación de ropa",
    description="Recibe una imagen, detecta personas, segmenta sus prendas y retorna JSON con imagen y metadata"
)
async def procesar_frame(file: UploadFile = File(...), payload: dict = Depends(get_current_user)):
    """
    Procesa un frame de video/imagen para segmentar prendas de vestir

    - **file**: Imagen en formato JPEG/PNG

    Retorna: JSON con imagen procesada (base64), número de personas y datos de prendas
    """
    try:
        logger.info(f"🎬 [procesar_frame] Usuario: {payload.get('username', 'unknown')}")

        # Obtener el servicio
        segmentation_service = get_segmentation_service()

        # 1. Leer imagen
        contents = await file.read()
        logger.debug(f"📸 Frame recibido: {len(contents)} bytes")

        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error("❌ Imagen inválida o corrupta")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagen inválida o corrupta"
            )

        logger.debug(f"📸 Frame decodificado: {frame.shape}")

        # 2. Procesar con el servicio
        logger.info("🔄 Procesando frame con segmentación...")
        processed_frame, persons_data = segmentation_service.process_frame(frame)
        logger.info(f"✅ Procesadas {len(persons_data)} personas")

        # 3. Codificar imagen de respuesta
        success, buffer = cv2.imencode(
            '.jpg',
            processed_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), settings.JPEG_QUALITY]
        )

        if not success:
            logger.error("❌ Error codificando imagen")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error codificando imagen de respuesta"
            )

        logger.debug(f"🖼️ Imagen codificada: {len(buffer)} bytes")

        # 4. Convertir imagen a base64
        image_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
        logger.debug(f"📊 Base64 length: {len(image_base64)}")

        # 5. Preparar datos de personas (asegurando tipos JSON serializables)
        persons_info = [
            {
                "track_id": int(track_id) if track_id is not None else None,
                "garments": [str(g) for g in garments]
            }
            for track_id, garments in persons_data
        ]

        # 6. Retornar JSON con metadata
        response_data = {
            "success": True,
            "image": f"data:image/jpeg;base64,{image_base64}",
            "persons_count": int(len(persons_data)),
            "persons": persons_info,
            "frame_shape": [int(x) for x in frame.shape]
        }

        logger.info(f"📤 Retornando respuesta: {len(response_data['image'])} bytes de imagen")

        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando frame: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post(
    "/extraer_prendas",
    summary="Extrae prendas recortadas por categoría",
    description="Procesa una imagen y retorna las prendas (topwear, lowerwear, footwear) recortadas en base64"
)
async def extraer_prendas(file: UploadFile = File(...), payload: dict = Depends(get_current_user)):
    """
    Procesa un frame y extrae las prendas recortadas por categoría
    Usa segmentación global (como procesar_frame) para consistencia

    - **file**: Imagen en formato JPEG/PNG

    Retorna: JSON con prendas recortadas en base64 por cada persona detectada
    """
    try:
        # Obtener el servicio
        segmentation_service = get_segmentation_service()

        # 1. Leer imagen
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagen inválida o corrupta"
            )

        logger.debug(f"📸 Frame recibido: {frame.shape}")

        # 2. Detectar personas con YOLO
        results = segmentation_service.yolo_model.track(
            frame,
            persist=True,
            classes=[0],
            conf=settings.YOLO_CONFIDENCE,
            verbose=False,
        )

        if not results or len(results[0].boxes) == 0:
            return JSONResponse(
                content={
                    "success": True,
                    "persons_count": 0,
                    "persons": []
                }
            )

        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)

        if results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        else:
            track_ids = [None] * len(boxes)

        h, w, _ = frame.shape

        # GUARDAR EN DISCO y MongoDB con rutas (sin timestamp para sobrescribir)
        persons_list = []

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = box

            # Aplicar padding igual que en procesar_frame
            pad = settings.PAD_RATIO
            dx = int((x2 - x1) * pad)
            dy = int((y2 - y1) * pad)

            x1p = max(0, x1 - dx)
            y1p = max(0, y1 - dy)
            x2p = min(w, x2 + dx)
            y2p = min(h, y2 + dy)

            # Clamp box sin padding para rect de visualización
            x1c = max(0, x1)
            y1c = max(0, y1)
            x2c = min(w, x2)
            y2c = min(h, y2)

            if (x2c - x1c) < settings.MIN_BOX_SIZE or (y2c - y1c) < settings.MIN_BOX_SIZE:
                continue

            # ⭐ PASO CRÍTICO: Recortar ROI y segmentarlo individualmente (igual que process_frame)
            # Esto garantiza consistencia con lo que ves en preview en vivo
            roi = frame[y1p:y2p, x1p:x2p]
            mask_roi = segmentation_service.segment_roi(roi)

            # DEBUG: Ver clases presentes en este ROI
            person_classes = np.unique(mask_roi).tolist()
            logger.info(f"🔍 Persona {track_id}: Clases detectadas: {person_classes}")

            # Extraer prendas por categoría desde la máscara global
            garments_crops = segmentation_service.extract_garments(roi, mask_roi)

            # Codificar prendas en base64 para respuesta HTTP
            garments_b64 = {}
            for garment_name, crop in garments_crops.items():
                if crop is not None:
                    success, buffer = cv2.imencode(
                        '.png',
                        crop,
                        [int(cv2.IMWRITE_PNG_COMPRESSION), 9]
                    )
                    if success:
                        garments_b64[garment_name] = base64.b64encode(buffer.tobytes()).decode('utf-8')
                    else:
                        garments_b64[garment_name] = None
                else:
                    garments_b64[garment_name] = None

            # Agregar a lista de personas (solo datos serializables en JSON)
            if track_id is not None:
                persons_list.append({
                    "track_id": int(track_id),
                    "prendas": garments_b64,
                    "debug_mask_classes": person_classes
                })

                # ⭐ GUARDAR INMEDIATAMENTE en disco y MongoDB
                try:
                    # Crear carpeta para esta persona
                    person_dir = EXTRACTED_GARMENTS_DIR / f"persona_{track_id}"
                    person_dir.mkdir(exist_ok=True)

                    # Guardar imagen de entrada (recorte de la persona dentro de la caja, SIN timestamp)
                    entrada_filename = "entrada.jpg"
                    entrada_path = person_dir / entrada_filename
                    # Recorte exacto de la caja (sin padding) para la imagen de entrada
                    entrada_roi = frame[y1c:y2c, x1c:x2c]
                    cv2.imwrite(str(entrada_path), entrada_roi)
                    entrada_relative_path = str(entrada_path).replace("\\", "/")
                    logger.info(f"💾 Imagen de entrada (ID {track_id}) guardada: {entrada_relative_path}")

                    # Guardar imagen segmentada (ROI con máscara aplicada)
                    segmented_roi = roi.copy()
                    mask_roi_3channel = cv2.cvtColor(mask_roi.astype(np.uint8) * 50, cv2.COLOR_GRAY2BGR)
                    segmented_roi = cv2.addWeighted(roi, 0.7, mask_roi_3channel, 0.3, 0)

                    segmented_filename = "segmentada.jpg"
                    segmented_path = person_dir / segmented_filename
                    cv2.imwrite(str(segmented_path), segmented_roi)
                    segmented_relative_path = str(segmented_path).replace("\\", "/")
                    logger.info(f"💾 Imagen segmentada guardada: {segmented_relative_path}")

                    # Guardar prendas en disco y construir dict de rutas
                    garments_paths = {}
                    colors_dict = {}

                    for garment_name, crop in garments_crops.items():
                        if crop is not None:
                            # Guardar archivo PNG (SIN timestamp para sobrescribir)
                            garment_filename = f"{garment_name}.png"
                            garment_path = person_dir / garment_filename
                            cv2.imwrite(str(garment_path), crop)
                            garment_relative_path = str(garment_path).replace("\\", "/")
                            garments_paths[garment_name] = garment_relative_path

                            # Calcular color dominante
                            color_hex = segmentation_service.get_dominant_color(crop)
                            colors_dict[garment_name] = color_hex

                            logger.info(f"💾 {garment_name} guardado: {garment_relative_path} | Color: {color_hex}")
                        else:
                            garments_paths[garment_name] = None
                            colors_dict[garment_name] = None

                    # Guardar en MongoDB con rutas (actualiza si ya existe el track_id)
                    await save_garment_extraction(
                        track_id=track_id,
                        image_input_path=entrada_relative_path,
                        image_segmented_path=segmented_relative_path,
                        garments_data=garments_paths,
                        colors_dict=colors_dict
                    )
                except Exception as e:
                    logger.error(f"⚠️ Error guardando extracción ID {track_id}: {e}")
                    # No detenemos el flujo si hay error

        return JSONResponse(
            content={
                "success": True,
                "persons_count": int(len(persons_list)),
                "persons": persons_list
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error extrayendo prendas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get(
    "/health",
    summary="Health check",
    description="Verifica que el servicio esté funcionando correctamente"
)
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "service": "segmentation-api",
        "version": settings.VERSION
    }

@router.get(
    "/stats",
    summary="Estadísticas del sistema",
    description="Retorna información sobre los modelos cargados"
)
async def get_stats():
    """Retorna estadísticas del sistema"""
    from services.model_manager import model_manager

    return {
        "device": str(model_manager.device),
        "models_loaded": {
            "segmentation": model_manager._seg_model is not None,
            "yolo": model_manager._yolo_model is not None
        },
        "config": {
            "input_size": settings.INPUT_SIZE,
            "num_classes": settings.NUM_CLASSES,
            "encoder": settings.ENCODER_NAME
        }
    }

@router.post(
    "/segmentar_imagen",
    summary="Segmenta la imagen completa y extrae prendas",
    description="Aplica segmentación en toda la imagen (sin ROI) y retorna prendas recortadas por clase. Útil para comparar con el notebook."
)
async def segmentar_imagen(file: UploadFile = File(...)):
    try:
        segmentation_service = get_segmentation_service()

        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Imagen inválida")

        # Segmentar la imagen completa
        mask_full = segmentation_service.segment_roi(image)

        # Extraer prendas por clase de toda la imagen
        crops = segmentation_service.extract_garments(image, mask_full)

        # Codificar a base64
        garments_b64 = {}
        for garment_name, crop in crops.items():
            if crop is not None:
                ok, buf = cv2.imencode('.png', crop, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
                garments_b64[garment_name] = base64.b64encode(buf.tobytes()).decode('utf-8') if ok else None
            else:
                garments_b64[garment_name] = None

        # Para debug: clases presentes en máscara
        debug_classes = np.unique(mask_full).tolist()

        return JSONResponse(content={
            "success": True,
            "debug_mask_classes": debug_classes,
            "prendas": garments_b64
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error segmentando imagen completa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/historial",
    summary="Obtiene historial de extracciones",
    description="Retorna el historial de extracciones guardadas en MongoDB"
)
async def obtener_historial(
    limit: int = 50,
    payload: dict = Depends(get_current_user)
):
    """
    Obtiene el historial de extracciones de prendas

    - **limit**: Número máximo de registros (default 50)

    Retorna: Lista de extracciones con información de prendas
    """
    try:
        logger.info(f"📋 [historial] Usuario: {payload.get('username', 'unknown')} - Limit: {limit}")

        history = await get_extraction_history(limit)

        return JSONResponse(content={
            "success": True,
            "count": len(history),
            "data": history
        })
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get(
    "/imagen-guardada",
    summary="Obtiene una imagen guardada en base64",
    description="Retorna una imagen guardada como base64 dado un archivo"
)
async def obtener_imagen_guardada(
    archivo: str,
    payload: dict = Depends(get_current_user)
):
    """
    Obtiene una imagen guardada y la retorna en base64

    - **archivo**: Ruta relativa del archivo (ej: extracted_garments/persona_1/segmentada.jpg)

    Retorna: JSON con imagen en base64
    """
    try:
        logger.info(f"📸 [imagen-guardada] Usuario: {payload.get('username', 'unknown')} - Archivo: {archivo}")

        # Validación de seguridad: evitar path traversal
        if ".." in archivo or archivo.startswith("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ruta de archivo inválida"
            )

        # Construir ruta segura
        file_path = Path(archivo)

        if not file_path.exists():
            logger.warning(f"⚠️ Archivo no encontrado: {archivo}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )

        # Leer imagen y convertir a base64
        with open(file_path, 'rb') as f:
            image_data = f.read()

        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Detectar tipo de archivo
        suffix = file_path.suffix.lower()
        media_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"

        logger.debug(f"✅ Imagen cargada: {len(image_data)} bytes")

        return JSONResponse(content={
            "success": True,
            "image": f"data:{media_type};base64,{image_base64}",
            "file": archivo
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo imagen: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get(
    "/estadisticas",
    summary="Obtiene estadísticas de extracciones",
    description="Retorna estadísticas agregadas de las extracciones realizadas"
)
async def obtener_estadisticas(payload: dict = Depends(get_current_user)):
    """
    Obtiene estadísticas de extracciones

    Retorna:
    - Total de extracciones
    - Personas únicas procesadas
    - Prendas más detectadas
    - Colores más frecuentes
    - Distribución por categoría
    """
    try:
        logger.info(f"📊 [estadisticas] Usuario: {payload.get('username', 'unknown')}")

        stats = await get_extraction_analytics()

        return JSONResponse(content={
            "success": True,
            "data": stats
        })
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get(
    "/descargar_prendas",
    summary="Descarga prendas extraídas en ZIP",
    description="Retorna un archivo ZIP con todas las prendas extraídas"
)
async def descargar_prendas(
    persona_id: int = None,
    payload: dict = Depends(get_current_user)
):
    """
    Descarga las prendas extraídas en formato ZIP

    - **persona_id**: ID de persona específica (opcional, descarga todas si no se especifica)

    Retorna: Archivo ZIP con las prendas
    """
    try:
        logger.info(f"📥 [descargar_prendas] Usuario: {payload.get('username', 'unknown')} - Persona ID: {persona_id}")

        # Crear ZIP en memoria
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            extracted_dir = Path("extracted_garments")

            if not extracted_dir.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No hay prendas extraídas para descargar"
                )

            # Iterar sobre carpetas de personas
            for person_folder in extracted_dir.iterdir():
                if not person_folder.is_dir():
                    continue

                # Extraer ID de persona de nombre como "persona_1"
                try:
                    folder_persona_id = int(person_folder.name.split('_')[1])
                except (IndexError, ValueError):
                    continue

                # Si se especificó persona_id, filtrar
                if persona_id is not None and folder_persona_id != persona_id:
                    continue

                # Agregar archivos de esta persona al ZIP
                for file_path in person_folder.iterdir():
                    if file_path.is_file():
                        # Crear estructura dentro del ZIP
                        arcname = f"{person_folder.name}/{file_path.name}"
                        zip_file.write(file_path, arcname=arcname)
                        logger.debug(f"📦 Agregado al ZIP: {arcname}")

            # Verificar que se agregaron archivos
            if len(zip_file.namelist()) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No hay archivos para descargar"
                )

        zip_buffer.seek(0)

        # Nombre del archivo
        filename = f"prendas_extraidas_{persona_id}.zip" if persona_id else "prendas_extraidas.zip"

        logger.info(f"✅ ZIP generado: {filename} - {len(zip_buffer.getvalue())} bytes")

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error descargando prendas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
