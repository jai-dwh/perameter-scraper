import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

API_KEY = os.getenv("API_KEY")
BROWSER_HEADLESS = _env_bool("BROWSER_HEADLESS", default=True)
CATEGORY_NAME = os.getenv("CATEGORY_NAME")
MODEL_BASE_URL=os.getenv("MODEL_BASE_URL")
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL_NAME=os.getenv("OPENROUTER_MODEL_NAME")
