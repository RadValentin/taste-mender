import os
from pathlib import Path
from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parent
DOTENV_CONFIG = dotenv_values(BASE_DIR / ".env")


def get_config(key: str, default: str | None = None) -> str:
    """Return config values preferring process env over backend/.env."""
    value = os.getenv(key) or DOTENV_CONFIG.get(key) or default
    if not value:
        raise ValueError(f"Missing value for config key: {key}")
    return value
