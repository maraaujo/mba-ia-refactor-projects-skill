import os
import secrets


class Config:
    """Configuração da aplicação, lida a partir de variáveis de ambiente."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    PORT = int(os.environ.get("PORT", "5000"))

    SECRET_KEY_IS_GENERATED = "SECRET_KEY" not in os.environ
