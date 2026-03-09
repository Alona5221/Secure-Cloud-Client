# 导入 pathlib.Path，用于跨平台路径管理。
from pathlib import Path

# PBKDF2 迭代次数，值越大抗暴力破解能力越强，但计算更慢。
PBKDF2_ITERATIONS = 100000
# 盐值长度（字节）。
SALT_SIZE = 16
# AES 密钥长度（字节），32 对应 AES-256。
AES_KEY_SIZE = 32
# AES-GCM 推荐随机数长度（字节）。
NONCE_SIZE = 12
# 密文封装魔术头，用于识别文件格式。
MAGIC_HEADER = b"SCF1"
# 统一的密文扩展名。
ENC_EXTENSION = ".enc"

# 当前文件所在目录，作为项目运行时的基础目录。
BASE_DIR = Path(__file__).resolve().parent
# 客户端缓存目录：保存本地加密产物和从服务器下载的密文副本。
CLIENT_CACHE_DIR = BASE_DIR / "client_cache"
# 下载目录：保存解密后的明文文件。
DOWNLOADS_DIR = BASE_DIR / "downloads"
# 服务器模拟目录：保存上传后的密文文件。
SERVER_STORAGE_DIR = BASE_DIR / "server_storage"
# 日志目录：保存运行日志文件。
LOG_DIR = BASE_DIR / "logs"


def init_directories() -> None:
    """初始化项目运行所需目录。"""
    # 遍历所有运行期必需目录。
    for directory in (CLIENT_CACHE_DIR, DOWNLOADS_DIR, SERVER_STORAGE_DIR, LOG_DIR):
        # 若目录不存在则创建，parents=True 支持递归创建父级目录。
        directory.mkdir(parents=True, exist_ok=True)
