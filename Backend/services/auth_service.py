"""
Servicio de autenticación
Ubicación: /services/auth_service.py
"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


def hash_password(password: str) -> str:
    """Encripta una contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(user_id: str, username: str, role: str) -> str:
    """
    Crea un JWT token

    Args:
        user_id: ID del usuario en MongoDB
        username: Nombre de usuario
        role: Rol del usuario ("user" o "admin")

    Returns:
        Token JWT
    """
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return token


def verify_token(token: str) -> dict:
    """
    Verifica y decodifica un JWT token

    Args:
        token: JWT token

    Returns:
        Payload del token si es válido

    Raises:
        jwt.InvalidTokenError si el token es inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("⏰ Token expirado")
        raise jwt.InvalidTokenError("Token expirado")
    except jwt.InvalidTokenError as e:
        logger.warning(f"❌ Token inválido: {e}")
        raise
