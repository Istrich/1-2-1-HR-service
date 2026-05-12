import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_FILE_PATH)

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
USERS_RAW = os.getenv("USERS", "admin:admin")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

USERS: dict[str, str] = {}
for pair in USERS_RAW.split(","):
    pair = pair.strip()
    if ":" in pair:
        u, p = pair.split(":", 1)
        USERS[u.strip()] = p.strip()

CHUNK_DURATION_SECONDS = 15 * 60
TARGET_SAMPLE_RATE = 16000
TARGET_BITRATE = "64k"
MAX_UPLOAD_MB = 500

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)
