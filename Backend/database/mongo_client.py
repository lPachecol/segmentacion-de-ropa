"""
Cliente de MongoDB con gestión de conexiones
Ubicación: /database/mongo_client.py
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from typing import Optional
import datetime
from bson import ObjectId

from config import get_settings
from utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)

class MongoDBClient:
    """Singleton para gestionar la conexión a MongoDB"""

    _instance: Optional['MongoDBClient'] = None
    _client: Optional[AsyncIOMotorClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self):
        """Establece conexión con MongoDB"""
        try:
            self._client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
            # Verificar conexión
            await self._client.admin.command('ping')
            logger.info("💾 Conectado a MongoDB")
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            raise

    def close(self):
        """Cierra la conexión"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB: Conexión cerrada")

    def get_collection(self) -> AsyncIOMotorCollection:
        """Retorna la colección de historial de personas"""
        if not self._client:
            raise RuntimeError("MongoDB no conectado. Llama a connect() primero.")

        db = self._client[settings.DB_NAME]
        return db[settings.COLLECTION_NAME]

    def get_users_collection(self) -> AsyncIOMotorCollection:
        """Retorna la colección de usuarios"""
        if not self._client:
            raise RuntimeError("MongoDB no conectado. Llama a connect() primero.")

        db = self._client[settings.DB_NAME]
        return db[settings.USERS_COLLECTION]

# Instancia global
mongodb = MongoDBClient()

async def save_person_garments(track_id: int, garments: list[str]):
    """
    Guarda o actualiza información de prendas de una persona

    Args:
        track_id: ID de tracking de la persona
        garments: Lista de prendas detectadas
    """
    if not garments:
        return

    collection = mongodb.get_collection()

    filter_query = {"persona_id": int(track_id)}

    update_query = {
        "$set": {
            "ultima_actualizacion": datetime.datetime.now()
        },
        "$setOnInsert": {
            "fecha_creacion": datetime.datetime.now()
        },
        "$addToSet": {
            "prendas": {"$each": garments}
        }
    }

    try:
        await collection.update_one(filter_query, update_query, upsert=True)
        logger.debug(f"💾 ID {track_id} actualizado con prendas: {garments}")
    except Exception as e:
        logger.error(f"⚠️ Error guardando en MongoDB: {e}")
        raise


async def save_garment_extraction(
    track_id: int,
    image_input_path: str,
    image_segmented_path: str,
    garments_data: dict,
    colors_dict: dict
):
    """
    Guarda o ACTUALIZA un registro de extracción de prendas con rutas a archivos

    Usa upsert: si la persona ya existe, actualiza su información
    Si es nueva, crea un nuevo documento

    Args:
        track_id: ID de tracking de la persona
        image_input_path: Ruta relativa a imagen de entrada
        image_segmented_path: Ruta relativa a imagen segmentada (corporal)
        garments_data: Dict con rutas de prendas
        colors_dict: Dict con colores dominantes
    """
    collection = mongodb.get_collection()

    # Construir documento de prendas con rutas y colores
    prendas_completas = {}
    for garment_name, img_path in garments_data.items():
        color_hex = colors_dict.get(garment_name, "#CCCCCC")

        prendas_completas[garment_name] = {
            "imagen_path": img_path,
            "color_hex": color_hex if img_path else None
        }

    # Crear documento con upsert
    extraction_record = {
        "$set": {
            "persona_id": int(track_id),
            "timestamp": datetime.datetime.now(),
            "imagen_entrada_path": image_input_path,
            "imagen_corporal": image_segmented_path,
            "prendas": prendas_completas
        }
    }

    try:
        # upsert=True: actualiza si existe, crea si no
        result = await collection.update_one(
            {"persona_id": int(track_id)},
            extraction_record,
            upsert=True
        )

        if result.upserted_id:
            logger.info(f"💾 Extracción ID {track_id} creada en MongoDB: {result.upserted_id}")
        else:
            logger.info(f"♻️ Extracción ID {track_id} actualizada en MongoDB (archivos sobrescritos)")

        return result.upserted_id or result.matched_count
    except Exception as e:
        logger.error(f"⚠️ Error guardando extracción en MongoDB: {e}")
        raise


# ========================
# === GESTIÓN DE USUARIOS ===
# ========================

async def create_user(username: str, password_hash: str, role: str = "user") -> Optional[str]:
    """
    Crea un nuevo usuario

    Args:
        username: Nombre de usuario único
        password_hash: Contraseña hasheada
        role: Rol del usuario ("user" o "admin")

    Returns:
        ID del usuario creado o None si ya existe
    """
    users_collection = mongodb.get_users_collection()

    # Verificar si el usuario ya existe
    existing = await users_collection.find_one({"username": username})
    if existing:
        logger.warning(f"⚠️ Usuario '{username}' ya existe")
        return None

    user_doc = {
        "username": username,
        "password": password_hash,
        "role": role,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "active": True
    }

    try:
        result = await users_collection.insert_one(user_doc)
        logger.info(f"✅ Usuario '{username}' creado con rol '{role}'")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"❌ Error creando usuario: {e}")
        raise


async def get_user(username: str) -> Optional[dict]:
    """
    Obtiene un usuario por nombre

    Args:
        username: Nombre de usuario

    Returns:
        Documento del usuario o None si no existe
    """
    users_collection = mongodb.get_users_collection()

    try:
        user = await users_collection.find_one({"username": username})
        return user
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuario: {e}")
        return None


async def get_all_users(skip_password: bool = True) -> list[dict]:
    """
    Obtiene todos los usuarios (sin contraseñas)

    Args:
        skip_password: Si True, no incluye el campo password

    Returns:
        Lista de usuarios
    """
    users_collection = mongodb.get_users_collection()

    try:
        projection = {"password": 0} if skip_password else {}
        users = await users_collection.find({}, projection).to_list(None)
        return users
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuarios: {e}")
        return []


async def update_user(username: str, updates: dict) -> bool:
    """
    Actualiza un usuario

    Args:
        username: Nombre de usuario
        updates: Dict con campos a actualizar

    Returns:
        True si se actualizó, False si no existe
    """
    users_collection = mongodb.get_users_collection()

    updates["updated_at"] = datetime.datetime.utcnow()

    try:
        result = await users_collection.update_one(
            {"username": username},
            {"$set": updates}
        )

        if result.matched_count > 0:
            logger.info(f"♻️ Usuario '{username}' actualizado")
            return True
        else:
            logger.warning(f"⚠️ Usuario '{username}' no encontrado")
            return False
    except Exception as e:
        logger.error(f"❌ Error actualizando usuario: {e}")
        return False


async def delete_user(username: str) -> bool:
    """
    Elimina un usuario

    Args:
        username: Nombre de usuario

    Returns:
        True si se eliminó, False si no existe
    """
    users_collection = mongodb.get_users_collection()

    try:
        result = await users_collection.delete_one({"username": username})

        if result.deleted_count > 0:
            logger.info(f"🗑️ Usuario '{username}' eliminado")
            return True
        else:
            logger.warning(f"⚠️ Usuario '{username}' no encontrado")
            return False
    except Exception as e:
        logger.error(f"❌ Error eliminando usuario: {e}")
        return False


# ========================
# === HISTORIAL ===
# ========================

async def get_extraction_history(limit: int = 50) -> list[dict]:
    """
    Obtiene el historial de extracciones de prendas

    Args:
        limit: Número máximo de registros a retornar

    Returns:
        Lista de documentos de historial ordenados por timestamp descendente
    """
    collection = mongodb.get_collection()

    try:
        cursor = collection.find().sort("timestamp", -1).limit(limit)
        documents = await cursor.to_list(length=limit)

        # Convertir ObjectId y datetime a string para serialización JSON
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

            # Convertir timestamp a ISO format string
            if "timestamp" in doc and doc["timestamp"]:
                doc["timestamp"] = doc["timestamp"].isoformat()

            # Convertir fecha_creacion si existe
            if "fecha_creacion" in doc and doc["fecha_creacion"]:
                doc["fecha_creacion"] = doc["fecha_creacion"].isoformat()

            # Convertir ultima_actualizacion si existe
            if "ultima_actualizacion" in doc and doc["ultima_actualizacion"]:
                doc["ultima_actualizacion"] = doc["ultima_actualizacion"].isoformat()

        logger.info(f"📋 Obtenidos {len(documents)} registros de historial")
        return documents
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        return []


async def get_extraction_analytics() -> dict:
    """
    Calcula estadísticas de extracciones

    Returns:
        Dict con estadísticas: total, prendas frecuentes, colores, personas únicas, horas de uso
    """
    collection = mongodb.get_collection()

    try:
        all_docs = await collection.find().to_list(None)

        if not all_docs:
            return {
                "total_extracciones": 0,
                "personas_unicas": 0,
                "prendas_frecuentes": [],
                "colores_frecuentes": [],
                "horas_uso": {}
            }

        # Contadores
        total = len(all_docs)
        personas_unicas = len(set(doc.get("persona_id") for doc in all_docs if "persona_id" in doc))

        # Contar prendas (SOLO las que no son None/null)
        prendas_contador = {}
        colores_contador = {}
        horas_contador = {}

        for doc in all_docs:
            prendas = doc.get("prendas", {})
            for garment_name, garment_data in prendas.items():
                # ⭐ SOLO contar si garment_data no es None y tiene contenido válido
                if garment_data is not None:
                    # Si es diccionario, verificar que tenga al menos imagen_path válida
                    if isinstance(garment_data, dict):
                        if garment_data.get("imagen_path") is not None:  # Solo contar si hay imagen
                            prendas_contador[garment_name] = prendas_contador.get(garment_name, 0) + 1

                            # Contar color si existe
                            if garment_data.get("color_hex"):
                                color = garment_data["color_hex"]
                                colores_contador[color] = colores_contador.get(color, 0) + 1
                    # Si es string (base64), contar directamente
                    elif isinstance(garment_data, str) and garment_data.strip():
                        prendas_contador[garment_name] = prendas_contador.get(garment_name, 0) + 1

            # Extraer hora de timestamp
            if "timestamp" in doc and doc["timestamp"]:
                hora = doc["timestamp"].hour
                hora_label = f"{hora:02d}:00"
                horas_contador[hora_label] = horas_contador.get(hora_label, 0) + 1

        # Ordenar por frecuencia
        prendas_frecuentes = sorted(prendas_contador.items(), key=lambda x: x[1], reverse=True)[:5]
        colores_frecuentes = sorted(colores_contador.items(), key=lambda x: x[1], reverse=True)[:5]

        # Ordenar horas de uso
        horas_uso_sorted = sorted(horas_contador.items())

        result = {
            "total_extracciones": total,
            "personas_unicas": personas_unicas,
            "prendas_frecuentes": [{"name": p[0], "count": p[1]} for p in prendas_frecuentes],
            "colores_frecuentes": [{"color": c[0], "count": c[1]} for c in colores_frecuentes],
            "horas_uso": [{"hora": h[0], "count": h[1]} for h in horas_uso_sorted]
        }

        logger.info(f"📊 Estadísticas calculadas: {total} extracciones, {personas_unicas} personas únicas")
        return result

    except Exception as e:
        logger.error(f"❌ Error calculando estadísticas: {e}")
        return {
            "total_extracciones": 0,
            "personas_unicas": 0,
            "prendas_frecuentes": [],
            "colores_frecuentes": [],
            "horas_uso": {}
        }
