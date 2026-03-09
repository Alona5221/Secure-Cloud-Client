from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from config import CLIENT_CACHE_DIR, ENC_EXTENSION, SERVER_STORAGE_DIR
from logger_utils import log_error, log_info


def generate_unique_filename(directory: Path, filename: str) -> str:
    """如存在同名文件，使用时间戳生成唯一文件名。"""
    target = directory / filename
    if not target.exists():
        return filename

    path = Path(filename)
    suffixes = "".join(path.suffixes)
    base_name = path.name[: -len(suffixes)] if suffixes else path.name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    new_name = f"{base_name}_{timestamp}{suffixes}"
    counter = 1
    while (directory / new_name).exists():
        new_name = f"{base_name}_{timestamp}_{counter}{suffixes}"
        counter += 1
    return new_name


def upload_encrypted_file(local_enc_path: str) -> tuple[bool, str, str]:
    """上传密文到服务器模拟目录。"""
    source_path = Path(local_enc_path)
    if not source_path.exists() or not source_path.is_file():
        msg = "待上传密文文件不存在"
        log_error("UPLOAD", source_path.name, msg)
        return False, msg, ""

    try:
        server_filename = generate_unique_filename(SERVER_STORAGE_DIR, source_path.name)
        target_path = SERVER_STORAGE_DIR / server_filename
        shutil.copy2(source_path, target_path)
        log_info("UPLOAD", server_filename, "success")
        return True, "文件上传成功", server_filename
    except Exception as exc:
        log_error("UPLOAD", source_path.name, str(exc))
        return False, "文件上传失败，请稍后重试", ""


def list_server_files() -> list[dict]:
    """获取服务器端 .enc 文件信息，按修改时间倒序。"""
    items: list[dict] = []
    try:
        for path in SERVER_STORAGE_DIR.iterdir():
            if path.is_file() and path.suffix == ENC_EXTENSION:
                stat = path.stat()
                items.append(
                    {
                        "name": path.name,
                        "size": stat.st_size,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "_mtime": stat.st_mtime,
                    }
                )
        items.sort(key=lambda x: x["_mtime"], reverse=True)
        for item in items:
            item.pop("_mtime", None)
        log_info("LIST_FILES", "", f"count={len(items)}")
    except Exception as exc:
        log_error("LIST_FILES", "", str(exc))
        return []
    return items


def download_encrypted_file(server_filename: str) -> tuple[bool, str, str]:
    """从服务器目录下载密文到客户端缓存目录。"""
    source_path = SERVER_STORAGE_DIR / server_filename
    if not source_path.exists() or not source_path.is_file():
        msg = "服务器文件不存在"
        log_error("DOWNLOAD", server_filename, msg)
        return False, msg, ""

    try:
        local_name = generate_unique_filename(CLIENT_CACHE_DIR, server_filename)
        target_path = CLIENT_CACHE_DIR / local_name
        shutil.copy2(source_path, target_path)
        log_info("DOWNLOAD", server_filename, "success")
        return True, "文件下载成功", str(target_path)
    except Exception as exc:
        log_error("DOWNLOAD", server_filename, str(exc))
        return False, "文件下载失败，请稍后重试", ""
