"""Crea un administrador local con una contraseña ingresada de forma interactiva."""
import asyncio
from getpass import getpass

from database.mongo_client import create_user, mongodb
from services.auth_service import hash_password


async def create_admin(username: str, password: str) -> None:
    try:
        await mongodb.connect()
        user_id = await create_user(username, hash_password(password), role="admin")
        if user_id is None:
            raise SystemExit("No se pudo crear el usuario. Comprueba si ya existe.")
        print(f"Administrador creado: {username}")
    finally:
        mongodb.close()


if __name__ == "__main__":
    username = input("Usuario administrador: ").strip()
    password = getpass("Contraseña: ")
    if not username or len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Ingresa un usuario y una contraseña de 8 a 72 bytes UTF-8 (mínimo 8 caracteres).")
    if password != getpass("Repite la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    asyncio.run(create_admin(username, password))
