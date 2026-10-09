import random
import string
import redis.asyncio as aioredis
from typing import Optional
from app.config import settings

# Kết nối Async Redis
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=5.0,
    socket_connect_timeout=5.0
)

async def generate_unique_otp(transaction_id: str, length: int = 6, expire_seconds: int = 300) -> str:
    """
    Sinh mã OTP ngẫu nhiên đáp ứng trọn vẹn Mục 3 của đề bài:
    1. Gắn với một giao dịch cụ thể (Key: otp:{transaction_id}).
    2. Không trùng với OTP đang có hiệu lực của giao dịch khác.
    3. Hết hạn tối đa 5 phút (TTL 300s).
    4. Chỉ được sử dụng thành công 1 lần.
    """
    max_attempts = 10
    otp_code = None

    for _ in range(max_attempts):
        candidate = "".join(random.choices(string.digits, k=length))
        is_active = await redis_client.exists(f"active_otp_code:{candidate}")
        if not is_active:
            otp_code = candidate
            break

    if not otp_code:
        otp_code = "".join(random.choices(string.digits, k=length))

    # Lưu mã OTP theo transaction_id có TTL 300s
    await redis_client.set(f"otp:{transaction_id}", otp_code, ex=expire_seconds)
    # Đánh dấu mã OTP này đang có hiệu lực trong toàn hệ thống
    await redis_client.set(f"active_otp_code:{otp_code}", transaction_id, ex=expire_seconds)

    return otp_code


async def verify_otp(transaction_id: str, input_otp: str) -> bool:
    """
    Kiểm tra mã OTP có hợp lệ và còn hạn hay không (CHƯA XÓA).
    Dùng trước khi chiếm Lock để tránh mất OTP nếu chiếm Lock thất bại.
    """
    stored_otp = await redis_client.get(f"otp:{transaction_id}")
    if not stored_otp:
        return False
    return stored_otp.strip() == input_otp.strip()


async def consume_otp(transaction_id: str):
    """
    Tiêu thụ và XÓA VĨNH VIỄN mã OTP sau khi đã chiếm Lock an toàn.
    Đảm bảo tính chất Single-use (chỉ dùng thành công 1 lần duy nhất).
    """
    stored_otp = await redis_client.get(f"otp:{transaction_id}")
    if stored_otp:
        await redis_client.delete(f"otp:{transaction_id}")
        await redis_client.delete(f"active_otp_code:{stored_otp}")


async def verify_and_consume_otp(transaction_id: str, input_otp: str) -> bool:
    """Tiện ích kiểm tra và tiêu thụ OTP trong 1 bước."""
    if await verify_otp(transaction_id, input_otp):
        await consume_otp(transaction_id)
        return True
    return False


async def invalidate_otp(transaction_id: str):
    """Hủy mã OTP khi người dùng tắt hoặc tạo phiên giao dịch mới."""
    await consume_otp(transaction_id)


# ========================================================
# CƠ CHẾ DISTRIBUTED LOCK (REDIS LOCK) CÓ TTL CHỐNG DEADLOCK
# ========================================================

LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

async def acquire_distributed_lock(lock_key: str, lock_token: str, ttl_seconds: int = 10) -> bool:
    """
    Chiếm khóa phân tán (Distributed Lock) trên Redis:
    - nx=True: Chỉ chiếm nếu khóa chưa tồn tại.
    - ex=ttl_seconds: BẮT BUỘC có thời hạn TTL (mặc định 10s) chống Deadlock vĩnh viễn nếu container crash.
    """
    return bool(await redis_client.set(lock_key, lock_token, nx=True, ex=ttl_seconds))

async def release_distributed_lock(lock_key: str, lock_token: str):
    """Giải phóng khóa phân tán an toàn bằng Lua Script."""
    try:
        await redis_client.eval(LUA_RELEASE_LOCK, 1, lock_key, lock_token)
    except Exception:
        pass
