# 导入 logging 标准库，提供日志能力。
import logging
# 导入 Logger 类型，便于类型注解。
from logging import Logger

# 导入日志目录配置。
from config import LOG_DIR

# 定义统一 logger 名称，避免多模块重复创建不同 logger。
LOGGER_NAME = "secure_cloud_client"


def setup_logger() -> Logger:
    """初始化并返回项目日志实例。"""
    # 获取（或创建）同名 logger。
    logger = logging.getLogger(LOGGER_NAME)
    # 如果已存在处理器，直接复用，避免重复添加 handler 导致日志重复输出。
    if logger.handlers:
        return logger

    # 设置日志级别为 INFO，记录常规信息与错误信息。
    logger.setLevel(logging.INFO)
    # 定义日志文件路径。
    log_file = LOG_DIR / "system.log"

    # 设置日志格式：时间 | 级别 | 文本。
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    # 创建文件处理器，使用 UTF-8 保证中文可读。
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    # 为处理器绑定格式化器。
    file_handler.setFormatter(formatter)

    # 将文件处理器挂载到 logger。
    logger.addHandler(file_handler)
    # 禁止向根 logger 传播，避免控制台重复打印。
    logger.propagate = False
    # 返回初始化完成的 logger。
    return logger


def _build_message(action: str, filename: str = "", message: str = "") -> str:
    """构造统一日志消息体。"""
    # 使用竖线分隔操作类型、文件名和消息内容。
    return f"{action} | {filename} | {message}"


def log_info(action: str, filename: str = "", message: str = "") -> None:
    """记录普通信息日志。"""
    # 获取 logger 实例（首次调用时会自动初始化）。
    logger = setup_logger()
    # 写入 INFO 级别日志。
    logger.info(_build_message(action, filename, message))


def log_error(action: str, filename: str = "", message: str = "") -> None:
    """记录错误信息日志。"""
    # 获取 logger 实例（首次调用时会自动初始化）。
    logger = setup_logger()
    # 写入 ERROR 级别日志。
    logger.error(_build_message(action, filename, message))
