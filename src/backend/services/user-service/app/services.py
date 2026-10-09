from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status
from app.models import User, AccountTransaction
from app.security import verify_password

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Xác thực người dùng bằng username và password."""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Tìm thông tin người dùng theo ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Tìm thông tin người dùng theo username."""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def deduct_user_balance(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    transaction_id: str,
    description: Optional[str] = None
) -> Tuple[Decimal, Decimal]:
    """
    Trừ tiền khỏi tài khoản người dùng:
    1. Kiểm tra tính bất biến (Idempotency): Nếu transaction_id này đã trừ tiền (DEBIT), trả kết quả cũ.
    2. Sử dụng PESSIMISTIC LOCKING (with_for_update) chống Double Spending khi có request đồng thời.
    3. Ghi vết lịch sử biến động số dư (AccountTransaction).
    """
    # 1. Kiểm tra Idempotency
    existing_tx_stmt = select(AccountTransaction).where(
        AccountTransaction.user_id == user_id,
        AccountTransaction.reference_id == transaction_id,
        AccountTransaction.transaction_type == "DEBIT"
    )
    existing_tx_res = await db.execute(existing_tx_stmt)
    existing_tx = existing_tx_res.scalar_one_or_none()

    if existing_tx:
        # Request này đã được xử lý thành công trước đó (do network retry từ Payment Service)
        previous_balance = existing_tx.balance_after + existing_tx.amount
        return previous_balance, existing_tx.balance_after

    # 2. Khóa dòng với with_for_update()
    user_stmt = select(User).where(User.id == user_id).with_for_update()
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại trong hệ thống."
        )

    previous_balance = user.balance

    # Kiểm tra số dư có đủ thanh toán không
    if user.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số dư khả dụng ({user.balance:,.0f} VNĐ) không đủ để thanh toán ({amount:,.0f} VNĐ)."
        )

    # Trừ số dư
    user.balance = user.balance - amount

    # 3. Ghi lịch sử giao dịch (Lưu vết biến động tài khoản)
    tx_record = AccountTransaction(
        user_id=user.id,
        amount=amount,
        transaction_type="DEBIT",
        balance_after=user.balance,
        reference_id=transaction_id,
        description=description or f"Thanh toán học phí (GD: {transaction_id})"
    )
    db.add(tx_record)

    await db.commit()
    await db.refresh(user)

    return previous_balance, user.balance

async def refund_user_balance(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    transaction_id: str,
    reason: Optional[str] = None
) -> Decimal:
    """
    Hoàn tiền lại vào tài khoản người dùng (Saga Compensating Action):
    1. Kiểm tra Idempotency: Không hoàn tiền 2 lần cho cùng 1 giao dịch.
    2. Khóa dòng với with_for_update() đảm bảo tính nhất quán.
    3. Ghi vết lịch sử biến động số dư (CREDIT).
    """
    # 1. Kiểm tra Idempotency
    existing_tx_stmt = select(AccountTransaction).where(
        AccountTransaction.user_id == user_id,
        AccountTransaction.reference_id == transaction_id,
        AccountTransaction.transaction_type == "CREDIT"
    )
    existing_tx_res = await db.execute(existing_tx_stmt)
    existing_tx = existing_tx_res.scalar_one_or_none()

    if existing_tx:
        return existing_tx.balance_after

    # 2. Khóa dòng
    user_stmt = select(User).where(User.id == user_id).with_for_update()
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại."
        )

    user.balance = user.balance + amount

    # 3. Ghi lịch sử hoàn tiền
    tx_record = AccountTransaction(
        user_id=user.id,
        amount=amount,
        transaction_type="CREDIT",
        balance_after=user.balance,
        reference_id=transaction_id,
        description=reason or f"Hoàn tiền giao dịch {transaction_id}"
    )
    db.add(tx_record)

    await db.commit()
    await db.refresh(user)

    return user.balance

async def get_user_transactions(
    db: AsyncSession,
    user_id: int,
    limit: int = 50
) -> List[AccountTransaction]:
    """Lấy danh sách lịch sử giao dịch và biến động số dư của người dùng."""
    stmt = (
        select(AccountTransaction)
        .where(AccountTransaction.user_id == user_id)
        .order_by(desc(AccountTransaction.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
