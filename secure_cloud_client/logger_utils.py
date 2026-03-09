import logging
from logging import Logger

from config import LOG_DIR

LOGGER_NAME = "secure_cloud_client"


def setup_logger() -> Logger:
    """初始化并返回项目日志实例。"""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_file = LOG_DIR / "system.log"

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def _build_message(action: str, filename: str = "", message: str = "") -> str:
    return f"{action} | {filename} | {message}"


def log_info(action: str, filename: str = "", message: str = "") -> None:
    """记录普通信息日志。"""
    logger = setup_logger()
    logger.info(_build_message(action, filename, message))


def log_error(action: str, filename: str = "", message: str = "") -> None:
    """记录错误信息日志。"""
    logger = setup_logger()
    logger.error(_build_message(action, filename, message))
