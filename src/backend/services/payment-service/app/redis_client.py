import secrets
import hashlib
import redis.asyncio as aioredis
from typing import Optional, Tuple
from app.config import settings

# Kết nối Async Redis
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=5.0,
    socket_connect_timeout=5.0
)

def hash_otp(code: str) -> str:
    """Băm mã OTP bằng SHA-256 trước khi lưu trữ (OWASP Security standard)."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

async def generate_unique_otp(transaction_id: str, length: int = 6, expire_seconds: int = 300) -> str:
    """
    Sinh mã OTP ngẫu nhiên bằng CSPRNG (secrets.randbelow) đáp ứng khuyến nghị OWASP:
    1. Gắn với một giao dịch cụ thể (Key: otp:{transaction_id}).
    2. Chỉ lưu chuỗi băm SHA-256 trong Redis, không lưu plaintext.
    3. Hết hạn tối đa 5 phút (TTL 300s).
    4. Chỉ được sử dụng thành công 1 lần (Single-use).
    5. Đếm số lần thử (tối đa 5 lần) chống brute-force.
    """
    # CSPRNG - Cryptographically Secure Pseudo-Random Number Generator
    otp_code = f"{secrets.randbelow(10 ** length):0{length}d}"
    otp_hashed = hash_otp(otp_code)

    # Lưu mã OTP băm theo transaction_id có TTL 300s
    await redis_client.set(f"otp:{transaction_id}", otp_hashed, ex=expire_seconds)
    # Khởi tạo bộ đếm số lần nhập sai
    await redis_client.set(f"otp_attempts:{transaction_id}", "0", ex=expire_seconds)

    # Chỉ trả về mã gốc cho luồng gửi email tới người dùng, không lưu plaintext ở bất kỳ đâu
    return otp_code


async def verify_otp(transaction_id: str, input_otp: str, max_attempts: int = 5) -> Tuple[bool, str, bool]:
    """
    Kiểm tra mã OTP có hợp lệ và còn hạn hay không:
    - Trả về tuple: (is_valid: bool, message: str, is_expired_or_locked: bool)
    - Tự động đếm và chặn brute-force sau max_attempts lần sai.
    - Không xóa ngay để bảo vệ nếu bước chiếm Distributed Lock bận.
    """
    stored_hash = await redis_client.get(f"otp:{transaction_id}")
    if not stored_hash:
        return False, "Mã OTP đã hết hạn (quá 5 phút) hoặc không tồn tại.", True

    # Tăng số lần thử
    attempts = await redis_client.incr(f"otp_attempts:{transaction_id}")
    if attempts > max_attempts:
        # Vượt quá số lần thử -> Hủy ngay OTP
        await consume_otp(transaction_id)
        return False, f"Bạn đã nhập sai mã OTP quá {max_attempts} lần. Giao dịch đã bị hủy để bảo vệ tài khoản.", True

    # So sánh mã băm
    input_hashed = hash_otp(input_otp)
    if input_hashed == stored_hash:
        return True, "Mã OTP hợp lệ.", False
    else:
        remaining = max(0, max_attempts - attempts)
        return False, f"Mã OTP không chính xác. Bạn còn {remaining} lần thử.", (remaining == 0)


async def consume_otp(transaction_id: str):
    """
    Tiêu thụ và XÓA VĨNH VIỄN mã OTP sau khi xác thực thành công.
    Đảm bảo tính chất Single-use (chỉ dùng thành công 1 lần duy nhất).
    """
    await redis_client.delete(f"otp:{transaction_id}")
    await redis_client.delete(f"otp_attempts:{transaction_id}")


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
