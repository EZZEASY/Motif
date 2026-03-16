import os
from dotenv import load_dotenv

load_dotenv(override=True)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_GENAI_API_KEY = os.getenv("GOOGLE_GENAI_API_KEY", "")
GCS_BUCKET = os.getenv("GCS_BUCKET", "motif-animations")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")
LOCAL_ANIMATIONS_DIR = os.getenv("LOCAL_ANIMATIONS_DIR", os.path.join(os.path.dirname(__file__), "data", "animations"))
LOCAL_CHARACTERS_DIR = os.getenv("LOCAL_CHARACTERS_DIR", os.path.join(os.path.dirname(__file__), "data", "characters"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
