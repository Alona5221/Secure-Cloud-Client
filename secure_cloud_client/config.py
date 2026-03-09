from pathlib import Path

PBKDF2_ITERATIONS = 100000
SALT_SIZE = 16
AES_KEY_SIZE = 32
NONCE_SIZE = 12
MAGIC_HEADER = b"SCF1"
ENC_EXTENSION = ".enc"

BASE_DIR = Path(__file__).resolve().parent
CLIENT_CACHE_DIR = BASE_DIR / "client_cache"
DOWNLOADS_DIR = BASE_DIR / "downloads"
SERVER_STORAGE_DIR = BASE_DIR / "server_storage"
LOG_DIR = BASE_DIR / "logs"


def init_directories() -> None:
    """初始化项目运行所需目录。"""
    for directory in (CLIENT_CACHE_DIR, DOWNLOADS_DIR, SERVER_STORAGE_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
