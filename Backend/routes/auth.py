"""
Rutas de autenticación
Ubicación: /routes/auth.py
"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
import jwt

from database.mongo_client import (
    create_user, get_user, get_all_users, update_user, delete_user
)
from services.auth_service import (
    hash_password, verify_password, create_access_token, verify_token
)
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/api", tags=["auth"])


# ========================
# === MODELOS ===
# ========================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: str


# ========================
# === DEPENDENCIAS ===
# ========================

async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Extrae el usuario actual del token JWT

    Args:
        authorization: Header Authorization (Bearer <token>)

    Returns:
        Payload del token (contiene username, role, etc)

    Raises:
        HTTPException si el token es inválido
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado"
        )

    try:
        parts = authorization.split()
        if len(parts) != 2:
            raise ValueError("Formato inválido")

        scheme, token = parts
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Esquema de autenticación inválido"
            )

        payload = verify_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Formato de Authorization inválido: {str(e)}"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )


async def require_admin(payload: dict = Depends(get_current_user)) -> dict:
    """
    Verifica que el usuario sea administrador

    Args:
        payload: Payload del token

    Returns:
        Payload del token

    Raises:
        HTTPException si no es admin
    """
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere rol de administrador"
        )
    return payload


# ========================
# === ENDPOINTS ===
# ========================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Endpoint de login

    Args:
        request: Credenciales (username, password)

    Returns:
        Token JWT, tipo, username y rol
    """
    # Obtener usuario de la BD
    user = await get_user(request.username)

    if not user:
        logger.warning(f"❌ Intento de login fallido: usuario '{request.username}' no existe")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    # Verificar contraseña
    if not verify_password(request.password, user["password"]):
        logger.warning(f"❌ Intento de login fallido: contraseña incorrecta para '{request.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    # Verificar que el usuario esté activo
    if not user.get("active", True):
        logger.warning(f"❌ Usuario '{request.username}' está inactivo")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    # Crear token
    token = create_access_token(
        user_id=str(user["_id"]),
        username=user["username"],
        role=user["role"]
    )

    logger.info(f"✅ Login exitoso: {request.username} (rol: {user['role']})")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        role=user["role"]
    )


@router.post("/register")
async def register(request: RegisterRequest, payload: dict = Depends(require_admin)):
    """
    Endpoint para registrar nuevos usuarios (solo admin)

    Args:
        request: Datos del nuevo usuario
        payload: Payload del token (requiere admin)

    Returns:
        Mensaje de éxito
    """
    # Validaciones
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    if len(request.username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario debe tener al menos 3 caracteres"
        )

    # Hashear contraseña
    password_hash = hash_password(request.password)

    # Crear usuario
    user_id = await create_user(request.username, password_hash, role="user")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe"
        )

    logger.info(f"👤 Usuario '{request.username}' registrado por admin '{payload['username']}'")

    return {
        "message": f"Usuario '{request.username}' creado exitosamente",
        "user_id": user_id
    }


@router.get("/me", response_model=UserInfo)
async def get_me(payload: dict = Depends(get_current_user)):
    """
    Obtiene información del usuario actual

    Args:
        payload: Payload del token

    Returns:
        Información del usuario (username, role)
    """
    return UserInfo(
        username=payload["username"],
        role=payload["role"]
    )


@router.get("/users", response_model=list[dict])
async def list_users(payload: dict = Depends(require_admin)):
    """
    Lista todos los usuarios (solo admin)

    Args:
        payload: Payload del token (requiere admin)

    Returns:
        Lista de usuarios sin contraseñas
    """
    users = await get_all_users(skip_password=True)

    # Convertir ObjectId a string
    for user in users:
        if "_id" in user:
            user["_id"] = str(user["_id"])

    return users


@router.delete("/users/{username}")
async def delete_user_endpoint(username: str, payload: dict = Depends(require_admin)):
    """
    Elimina un usuario (solo admin)

    Args:
        username: Nombre de usuario a eliminar
        payload: Payload del token (requiere admin)

    Returns:
        Mensaje de éxito
    """
    if username == payload["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo"
        )

    success = await delete_user(username)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario '{username}' no encontrado"
        )

    logger.info(f"🗑️ Usuario '{username}' eliminado por admin '{payload['username']}'")

    return {"message": f"Usuario '{username}' eliminado"}
