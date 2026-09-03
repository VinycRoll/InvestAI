"""Centralized application configuration.

All environment variables are read here once, so the rest of the codebase
references named constants instead of scattering ``os.getenv`` calls and magic
values around. ``load_dotenv`` is invoked a single time at import.
"""
import os

from dotenv import load_dotenv

load_dotenv()


# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./investia.db")


# --- JWT / Auth ---
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
)
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "90"))
GEMINI_RETRIES = int(os.getenv("GEMINI_RETRIES", "2"))
GEMINI_RETRY_DELAY = float(os.getenv("GEMINI_RETRY_DELAY", "1.0"))
GEMINI_MAX_CONTEXT_LENGTH = int(os.getenv("GEMINI_MAX_CONTEXT_LENGTH", "60000"))


# --- Upload ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1024 * 1024  # stream upload in 1MB chunks


# --- CORS ---
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:8501,http://localhost:3000"
).split(",")
CORS_ALLOW_METHODS = ["GET", "POST", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]


# --- App metadata ---
APP_NAME = "InvestIA"
APP_VERSION = "2.0.0"
