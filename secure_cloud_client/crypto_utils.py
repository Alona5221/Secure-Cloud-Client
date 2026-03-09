# 开启未来注解，提升类型注解书写体验。
from __future__ import annotations

# 导入 struct，用于二进制打包/解包 filename_len。
import struct
# 导入 datetime，用于冲突重命名时间戳。
from datetime import datetime
# 导入 Path 用于文件路径处理。
from pathlib import Path
# 导入安全随机字节生成函数。
from secrets import token_bytes

# 导入哈希算法组件（PBKDF2 使用 SHA256）。
from cryptography.hazmat.primitives import hashes
# 导入 AES-GCM 对称加密实现。
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# 导入 PBKDF2 密钥派生实现。
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 导入项目配置常量。
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
# 导入日志工具。
from logger_utils import log_error, log_info


def validate_password(password: str) -> tuple[bool, str]:
    """校验口令合法性。"""
    # 处理空对象场景（保险性检查）。
    if password is None:
        return False, "口令不能为空"
    # 去除首尾空白，避免用户误输入空格导致不一致。
    cleaned = password.strip()
    # 去除空白后若为空，提示口令不能为空。
    if not cleaned:
        return False, "口令不能为空"
    # 口令长度不小于 6。
    if len(cleaned) < 6:
        return False, "口令长度不能少于 6 位"
    # 校验通过。
    return True, ""


def derive_key(password: str, salt: bytes) -> bytes:
    """使用 PBKDF2HMAC 派生 AES 密钥。"""
    # 创建 PBKDF2 派生器。
    kdf = PBKDF2HMAC(
        # 指定哈希算法 SHA256。
        algorithm=hashes.SHA256(),
        # 指定输出长度 32 字节（AES-256）。
        length=AES_KEY_SIZE,
        # 指定盐值。
        salt=salt,
        # 指定迭代次数。
        iterations=PBKDF2_ITERATIONS,
    )
    # 使用清洗后的口令字节派生密钥。
    return kdf.derive(password.strip().encode("utf-8"))


def build_encrypted_blob(original_filename: str, salt: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """按协议封装密文二进制数据。"""
    # 将原始文件名编码为 UTF-8 字节。
    filename_bytes = original_filename.encode("utf-8")
    # filename_len 为 2 字节无符号整数，最大 65535。
    if len(filename_bytes) > 65535:
        raise ValueError("文件名过长，无法封装")

    # 按规范拼接：magic + filename_len + filename + salt + nonce + ciphertext。
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
    # 最小长度：4(magic)+2(filename_len)+16(salt)+12(nonce)+1(ciphertext 至少 1 字节)。
    min_length = 4 + 2 + SALT_SIZE + NONCE_SIZE + 1
    # 校验最小长度。
    if len(blob) < min_length:
        raise ValueError("密文格式非法：长度不足")

    # 校验魔术头。
    if blob[:4] != MAGIC_HEADER:
        raise ValueError("密文格式非法：文件头无效")

    # 读取 2 字节文件名长度。
    filename_len = struct.unpack(">H", blob[4:6])[0]
    # 初始游标位置（跳过 magic 与 filename_len）。
    cursor = 6
    # 文件名字节结束下标。
    end_filename = cursor + filename_len
    # 校验文件名区间不越界。
    if end_filename > len(blob):
        raise ValueError("密文格式非法：文件名长度异常")

    # 切片出文件名字节。
    filename_bytes = blob[cursor:end_filename]
    # 游标移动到文件名之后。
    cursor = end_filename

    # 盐值结束位置。
    end_salt = cursor + SALT_SIZE
    # nonce 结束位置。
    end_nonce = end_salt + NONCE_SIZE
    # 校验 salt/nonce 及后续密文区域至少有 1 字节密文。
    if end_nonce >= len(blob):
        raise ValueError("密文格式非法：盐值或随机数异常")

    # 提取 salt。
    salt = blob[cursor:end_salt]
    # 提取 nonce。
    nonce = blob[end_salt:end_nonce]
    # 提取 ciphertext。
    ciphertext = blob[end_nonce:]

    # 密文为空时视为损坏。
    if not ciphertext:
        raise ValueError("密文格式非法：密文数据为空")

    try:
        # 解码原始文件名。
        filename = filename_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        # 文件名解码失败时抛出格式错误。
        raise ValueError("密文格式非法：文件名编码错误") from exc

    # 返回解析结果字典。
    return {
        "filename": filename,
        "salt": salt,
        "nonce": nonce,
        "ciphertext": ciphertext,
    }


def _generate_unique_filename(directory: Path, filename: str) -> str:
    """在指定目录为目标文件生成唯一名称。"""
    # 计算候选路径。
    target = directory / filename
    # 无冲突直接返回。
    if not target.exists():
        return filename

    # 解析文件名。
    path = Path(filename)
    # 生成时间戳。
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 保留全部后缀。
    suffixes = "".join(path.suffixes)
    # 基础文件名（去后缀）。
    base_name = path.name[: -len(suffixes)] if suffixes else path.name
    # 第一版冲突替代名。
    new_name = f"{base_name}_{timestamp}{suffixes}"
    # 次级冲突计数器。
    counter = 1
    # 处理同秒多次冲突。
    while (directory / new_name).exists():
        new_name = f"{base_name}_{timestamp}_{counter}{suffixes}"
        counter += 1
    # 返回唯一文件名。
    return new_name


def encrypt_file(file_path: str, password: str) -> tuple[bool, str, str]:
    """加密本地文件并输出到 client_cache。"""
    # 先校验口令。
    valid, reason = validate_password(password)
    # 口令非法直接返回。
    if not valid:
        return False, reason, ""

    # 构造源文件路径对象。
    source_path = Path(file_path)
    # 检查文件可用性。
    if not source_path.exists() or not source_path.is_file():
        # 友好错误消息。
        msg = "本地文件不存在或不可用"
        # 写错误日志。
        log_error("ENCRYPT", source_path.name, msg)
        # 返回失败。
        return False, msg, ""

    try:
        # 读取明文二进制数据。
        plaintext = source_path.read_bytes()
        # 生成随机 salt。
        salt = token_bytes(SALT_SIZE)
        # 生成随机 nonce。
        nonce = token_bytes(NONCE_SIZE)
        # 从口令派生密钥。
        key = derive_key(password, salt)
        # 执行 AES-GCM 加密。
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        # 按规范封装密文 blob。
        blob = build_encrypted_blob(source_path.name, salt, nonce, ciphertext)

        # 默认输出文件名 = 原文件名 + .enc。
        output_filename = _generate_unique_filename(CLIENT_CACHE_DIR, f"{source_path.name}{ENC_EXTENSION}")
        # 计算输出路径。
        output_path = CLIENT_CACHE_DIR / output_filename
        # 写入密文文件。
        output_path.write_bytes(blob)

        # 记录加密成功。
        log_info("ENCRYPT", source_path.name, "success")
        # 返回成功结果。
        return True, "文件加密成功", str(output_path)
    except Exception as exc:
        # 记录底层异常以供排查。
        log_error("ENCRYPT", source_path.name, str(exc))
        # 对用户返回友好错误。
        return False, "文件加密失败，请稍后重试", ""


def decrypt_file(enc_file_path: str, password: str) -> tuple[bool, str, str]:
    """解密密文文件并输出到 downloads。"""
    # 校验口令。
    valid, reason = validate_password(password)
    # 口令非法时直接返回。
    if not valid:
        return False, reason, ""

    # 构造输入密文路径对象。
    source_path = Path(enc_file_path)
    # 检查密文文件可用性。
    if not source_path.exists() or not source_path.is_file():
        # 友好错误提示。
        msg = "密文文件不存在或不可用"
        # 记录错误日志。
        log_error("DECRYPT", source_path.name, msg)
        # 返回失败。
        return False, msg, ""

    try:
        # 读取密文 blob。
        blob = source_path.read_bytes()
        # 解析 blob 得到文件名、salt、nonce、ciphertext。
        parsed = parse_encrypted_blob(blob)
        # 用解析出的 salt 重新派生密钥。
        key = derive_key(password, parsed["salt"])
        # 执行 AES-GCM 解密。
        plaintext = AESGCM(key).decrypt(parsed["nonce"], parsed["ciphertext"], None)

        # 按原始文件名写回 downloads（若冲突自动改名）。
        output_filename = _generate_unique_filename(DOWNLOADS_DIR, parsed["filename"])
        # 计算输出路径。
        output_path = DOWNLOADS_DIR / output_filename
        # 写入解密后的明文。
        output_path.write_bytes(plaintext)

        # 记录解密成功日志。
        log_info("DECRYPT", source_path.name, "success")
        # 返回成功。
        return True, "文件解密成功", str(output_path)
    except Exception as exc:
        # 记录详细异常（包括口令错误、GCM 校验失败、格式错误等）。
        log_error("DECRYPT", source_path.name, str(exc))
        # 对外统一错误口径，避免暴露底层细节。
        return False, "口令错误或文件已损坏，解密失败", ""
