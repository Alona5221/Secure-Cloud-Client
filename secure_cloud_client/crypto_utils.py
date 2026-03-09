from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path
from secrets import token_bytes

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import (
    AES_KEY_SIZE,
    CLIENT_CACHE_DIR,
    DOWNLOADS_DIR,
    ENC_EXTENSION,
    MAGIC_HEADER,
    NONCE_SIZE,
    PBKDF2_ITERATIONS,
    SALT_SIZE,
)
from logger_utils import log_error, log_info


def validate_password(password: str) -> tuple[bool, str]:
    """校验口令合法性。"""
    if password is None:
        return False, "口令不能为空"
    cleaned = password.strip()
    if not cleaned:
        return False, "口令不能为空"
    if len(cleaned) < 6:
        return False, "口令长度不能少于 6 位"
    return True, ""


def derive_key(password: str, salt: bytes) -> bytes:
    """使用 PBKDF2HMAC 派生 AES 密钥。"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.strip().encode("utf-8"))


def build_encrypted_blob(original_filename: str, salt: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """按协议封装密文二进制数据。"""
    filename_bytes = original_filename.encode("utf-8")
    if len(filename_bytes) > 65535:
        raise ValueError("文件名过长，无法封装")

    return b"".join(
        [
            MAGIC_HEADER,
            struct.pack(">H", len(filename_bytes)),
            filename_bytes,
            salt,
            nonce,
            ciphertext,
        ]
    )


def parse_encrypted_blob(blob: bytes) -> dict:
    """解析封装后的密文文件。"""
    min_length = 4 + 2 + SALT_SIZE + NONCE_SIZE + 1
    if len(blob) < min_length:
        raise ValueError("密文格式非法：长度不足")

    if blob[:4] != MAGIC_HEADER:
        raise ValueError("密文格式非法：文件头无效")

    filename_len = struct.unpack(">H", blob[4:6])[0]
    cursor = 6
    end_filename = cursor + filename_len
    if end_filename > len(blob):
        raise ValueError("密文格式非法：文件名长度异常")

    filename_bytes = blob[cursor:end_filename]
    cursor = end_filename

    end_salt = cursor + SALT_SIZE
    end_nonce = end_salt + NONCE_SIZE
    if end_nonce >= len(blob):
        raise ValueError("密文格式非法：盐值或随机数异常")

    salt = blob[cursor:end_salt]
    nonce = blob[end_salt:end_nonce]
    ciphertext = blob[end_nonce:]

    if not ciphertext:
        raise ValueError("密文格式非法：密文数据为空")

    try:
        filename = filename_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("密文格式非法：文件名编码错误") from exc

    return {
        "filename": filename,
        "salt": salt,
        "nonce": nonce,
        "ciphertext": ciphertext,
    }


def _generate_unique_filename(directory: Path, filename: str) -> str:
    target = directory / filename
    if not target.exists():
        return filename

    path = Path(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffixes = "".join(path.suffixes)
    base_name = path.name[: -len(suffixes)] if suffixes else path.name
    new_name = f"{base_name}_{timestamp}{suffixes}"
    counter = 1
    while (directory / new_name).exists():
        new_name = f"{base_name}_{timestamp}_{counter}{suffixes}"
        counter += 1
    return new_name


def encrypt_file(file_path: str, password: str) -> tuple[bool, str, str]:
    """加密本地文件并输出到 client_cache。"""
    valid, reason = validate_password(password)
    if not valid:
        return False, reason, ""

    source_path = Path(file_path)
    if not source_path.exists() or not source_path.is_file():
        msg = "本地文件不存在或不可用"
        log_error("ENCRYPT", source_path.name, msg)
        return False, msg, ""

    try:
        plaintext = source_path.read_bytes()
        salt = token_bytes(SALT_SIZE)
        nonce = token_bytes(NONCE_SIZE)
        key = derive_key(password, salt)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        blob = build_encrypted_blob(source_path.name, salt, nonce, ciphertext)

        output_filename = _generate_unique_filename(CLIENT_CACHE_DIR, f"{source_path.name}{ENC_EXTENSION}")
        output_path = CLIENT_CACHE_DIR / output_filename
        output_path.write_bytes(blob)

        log_info("ENCRYPT", source_path.name, "success")
        return True, "文件加密成功", str(output_path)
    except Exception as exc:
        log_error("ENCRYPT", source_path.name, str(exc))
        return False, "文件加密失败，请稍后重试", ""


def decrypt_file(enc_file_path: str, password: str) -> tuple[bool, str, str]:
    """解密密文文件并输出到 downloads。"""
    valid, reason = validate_password(password)
    if not valid:
        return False, reason, ""

    source_path = Path(enc_file_path)
    if not source_path.exists() or not source_path.is_file():
        msg = "密文文件不存在或不可用"
        log_error("DECRYPT", source_path.name, msg)
        return False, msg, ""

    try:
        blob = source_path.read_bytes()
        parsed = parse_encrypted_blob(blob)
        key = derive_key(password, parsed["salt"])
        plaintext = AESGCM(key).decrypt(parsed["nonce"], parsed["ciphertext"], None)

        output_filename = _generate_unique_filename(DOWNLOADS_DIR, parsed["filename"])
        output_path = DOWNLOADS_DIR / output_filename
        output_path.write_bytes(plaintext)

        log_info("DECRYPT", source_path.name, "success")
        return True, "文件解密成功", str(output_path)
    except Exception as exc:
        log_error("DECRYPT", source_path.name, str(exc))
        return False, "口令错误或文件已损坏，解密失败", ""
