# 开启未来注解特性，减少前向引用类型提示负担。
from __future__ import annotations

# 导入 shutil 用于文件复制。
import shutil
# 导入 datetime 以生成时间戳重命名与格式化时间。
from datetime import datetime
# 导入 Path 进行路径处理。
from pathlib import Path

# 导入路径与扩展名配置。
from config import CLIENT_CACHE_DIR, ENC_EXTENSION, SERVER_STORAGE_DIR
# 导入统一日志函数。
from logger_utils import log_error, log_info


def generate_unique_filename(directory: Path, filename: str) -> str:
    """如存在同名文件，使用时间戳生成唯一文件名。"""
    # 计算目标路径。
    target = directory / filename
    # 若不存在冲突，直接返回原文件名。
    if not target.exists():
        return filename

    # 将文件名解析为 Path 对象，便于处理多后缀（如 .txt.enc）。
    path = Path(filename)
    # 拼接所有后缀字符串。
    suffixes = "".join(path.suffixes)
    # 获取不含后缀的基础名。
    base_name = path.name[: -len(suffixes)] if suffixes else path.name
    # 生成时间戳，满足课程要求的重命名方案。
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 初始新文件名：基础名_时间戳+原后缀。
    new_name = f"{base_name}_{timestamp}{suffixes}"
    # 计数器用于极端情况下同秒多次冲突。
    counter = 1
    # 若新文件名仍冲突，追加计数器继续尝试。
    while (directory / new_name).exists():
        new_name = f"{base_name}_{timestamp}_{counter}{suffixes}"
        counter += 1
    # 返回最终唯一文件名。
    return new_name


def upload_encrypted_file(local_enc_path: str) -> tuple[bool, str, str]:
    """上传密文到服务器模拟目录。"""
    # 构造源文件路径对象。
    source_path = Path(local_enc_path)
    # 校验源文件存在且为普通文件。
    if not source_path.exists() or not source_path.is_file():
        # 面向用户的友好错误信息。
        msg = "待上传密文文件不存在"
        # 记录错误日志。
        log_error("UPLOAD", source_path.name, msg)
        # 返回失败结果。
        return False, msg, ""

    try:
        # 生成服务器端唯一文件名，避免覆盖已有密文。
        server_filename = generate_unique_filename(SERVER_STORAGE_DIR, source_path.name)
        # 计算目标路径。
        target_path = SERVER_STORAGE_DIR / server_filename
        # 执行复制，并保留时间等元数据。
        shutil.copy2(source_path, target_path)
        # 记录上传成功日志。
        log_info("UPLOAD", server_filename, "success")
        # 返回成功和服务器实际文件名。
        return True, "文件上传成功", server_filename
    except Exception as exc:
        # 记录底层异常到日志，便于排查。
        log_error("UPLOAD", source_path.name, str(exc))
        # 向 GUI 返回友好消息。
        return False, "文件上传失败，请稍后重试", ""


def list_server_files() -> list[dict]:
    """获取服务器端 .enc 文件信息，按修改时间倒序。"""
    # 用于承载最终结果。
    items: list[dict] = []
    try:
        # 遍历服务器模拟目录下所有条目。
        for path in SERVER_STORAGE_DIR.iterdir():
            # 仅收集普通文件且后缀为 .enc 的项目。
            if path.is_file() and path.suffix == ENC_EXTENSION:
                # 读取文件状态信息。
                stat = path.stat()
                # 组装列表项字典。
                items.append(
                    {
                        "name": path.name,
                        "size": stat.st_size,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "_mtime": stat.st_mtime,
                    }
                )
        # 按修改时间戳倒序，最新文件在前。
        items.sort(key=lambda x: x["_mtime"], reverse=True)
        # 删除内部排序字段，保留对外约定字段。
        for item in items:
            item.pop("_mtime", None)
        # 记录列表读取成功日志。
        log_info("LIST_FILES", "", f"count={len(items)}")
    except Exception as exc:
        # 出错时写日志。
        log_error("LIST_FILES", "", str(exc))
        # 出错时返回空列表，保证 UI 不崩溃。
        return []
    # 返回最终文件信息列表。
    return items


def download_encrypted_file(server_filename: str) -> tuple[bool, str, str]:
    """从服务器目录下载密文到客户端缓存目录。"""
    # 计算服务器端源路径。
    source_path = SERVER_STORAGE_DIR / server_filename
    # 校验服务器文件存在且为普通文件。
    if not source_path.exists() or not source_path.is_file():
        # 设置友好提示。
        msg = "服务器文件不存在"
        # 记录错误日志。
        log_error("DOWNLOAD", server_filename, msg)
        # 返回失败。
        return False, msg, ""

    try:
        # 在 client_cache 中生成唯一文件名。
        local_name = generate_unique_filename(CLIENT_CACHE_DIR, server_filename)
        # 构造目标路径。
        target_path = CLIENT_CACHE_DIR / local_name
        # 执行复制。
        shutil.copy2(source_path, target_path)
        # 写入成功日志。
        log_info("DOWNLOAD", server_filename, "success")
        # 返回成功结果及本地缓存路径。
        return True, "文件下载成功", str(target_path)
    except Exception as exc:
        # 记录详细异常。
        log_error("DOWNLOAD", server_filename, str(exc))
        # 返回友好错误。
        return False, "文件下载失败，请稍后重试", ""
