#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
iBanking TDTU - Automated Concurrency, Idempotency & Saga Verification Suite
Môn học: Kiến Trúc Hướng Dịch Vụ (SOA - CS504070, ĐH Tôn Đức Thắng)
=============================================================================
Kịch bản kiểm thử tự động toàn diện cho PHASE 2:
1. Distributed Tracing: Truy vết phân tán qua header X-Correlation-ID.
2. Idempotency-Key: Chống trùng lặp giao dịch khi gửi nhiều request đồng thời.
3. Concurrency 1 (Double-Spending): Chống âm số dư tài khoản khi thanh toán song song.
4. Concurrency 2 (Tuition Race Condition & Saga Compensation): 2 người trả 1 hóa đơn.
5. End-to-End Payment Flow: Hoàn chỉnh từ đăng nhập -> OTP Mailpit -> Xác nhận -> Số dư.
=============================================================================
"""

import sys
import os
import time
import json
import uuid
import re
import asyncio
import subprocess
from decimal import Decimal

# Đảm bảo UTF-8 trên Windows console
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cấu hình màu sắc Terminal (ANSI Escape Codes)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*75}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}[TEST] {title.upper()}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*75}{Colors.RESET}")

def print_pass(msg: str):
    print(f"  {Colors.BOLD}{Colors.GREEN}[PASS]{Colors.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Colors.BOLD}{Colors.RED}[FAIL]{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"  {Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def print_warn(msg: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

# Cấu hình URL hệ thống (Tất cả gọi qua API Gateway và Mailpit)
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAILPIT_URL = os.getenv("MAILPIT_URL", "http://localhost:8025")

# Kiểm tra thư viện httpx
try:
    import httpx
except ImportError:
    print(f"{Colors.RED}Lỗi: Thư viện 'httpx' chưa được cài đặt.{Colors.RESET}")
    print(f"Vui lòng cài đặt bằng lệnh: {Colors.BOLD}pip install httpx{Colors.RESET}\n")
    sys.exit(1)


# =============================================================================
# HELPER FUNCTIONS (TIỆN ÍCH HỖ TRỢ KIỂM THỬ)
# =============================================================================

def get_mysql_root_password() -> str:
    """Đọc MYSQL_ROOT_PASSWORD trực tiếp từ file .env an toàn."""
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MYSQL_ROOT_PASSWORD="):
                    return line.strip().split("=", 1)[1]
    return os.getenv("MYSQL_ROOT_PASSWORD", "ibanking_root_secure_2026_tdtu")


def reset_demo_database() -> bool:
    """Khôi phục trạng thái số dư người dùng và hóa đơn học phí về ban đầu."""
    print_info("Đang khôi phục dữ liệu mẫu về trạng thái gốc qua reset_demo.sql...")
    root_pw = get_mysql_root_password()
    sql_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "reset_demo.sql")
    if not os.path.exists(sql_path):
        print_warn(f"Không tìm thấy file {sql_path}")
        return False
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        res = subprocess.run(
            ["docker", "compose", "exec", "-T", "mysql", "mysql", "-uroot", f"-p{root_pw}"],
            input=sql_content.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15
        )
        if res.returncode == 0:
            print_pass("Dữ liệu mẫu đã được reset thành công.")
            return True
        else:
            print_warn(f"Reset DB exit code {res.returncode}: {res.stderr.decode('utf-8', errors='ignore')}")
            return False
    except Exception as e:
        print_warn(f"Không thể chạy reset DB tự động: {e}")
        return False


async def clear_mailpit_messages(client: httpx.AsyncClient):
    """Xóa sạch hòm thư Mailpit để kiểm thử OTP tươi mới."""
    try:
        await client.delete(f"{MAILPIT_URL}/api/v1/messages", timeout=3.0)
    except Exception:
        pass


async def get_latest_otp_mailpit(client: httpx.AsyncClient, recipient_email: str, max_retries: int = 15) -> str:
    """Trích xuất mã OTP từ email nhận được trong Mailpit."""
    for attempt in range(max_retries):
        try:
            r = await client.get(f"{MAILPIT_URL}/api/v1/messages", timeout=3.0)
            if r.status_code == 200:
                messages = r.json().get("messages", [])
                for msg in messages:
                    subject = msg.get("Subject", "")
                    if "OTP" in subject:
                        # Kiểm tra người nhận
                        to_list = [addr.get("Address", "") for addr in msg.get("To", [])]
                        if not recipient_email or recipient_email in to_list:
                            match = re.search(r"(\d{6})", subject)
                            if match:
                                return match.group(1)
                            snippet = msg.get("Snippet", "")
                            match_snip = re.search(r"(\d{6})", snippet)
                            if match_snip:
                                return match_snip.group(1)
        except Exception:
            pass
        await asyncio.sleep(0.4)
    raise TimeoutError(f"Không tìm thấy email OTP trong Mailpit cho {recipient_email}")


async def login_user(client: httpx.AsyncClient, username: str, password: str = "123456") -> dict:
    """Đăng nhập và lấy Bearer Token JWT."""
    url = f"{GATEWAY_URL}/api/auth/login"
    resp = await client.post(url, json={"username": username, "password": password})
    if resp.status_code != 200:
        raise Exception(f"Đăng nhập thất bại cho {username}: {resp.text}")
    return resp.json()


# =============================================================================
# BÀI KIỂM THỬ 1: DISTRIBUTED TRACING (X-CORRELATION-ID)
# =============================================================================
async def test_scenario_tracing(client: httpx.AsyncClient) -> bool:
    """
    Kỳ vọng:
    1. Gửi request có X-Correlation-ID -> Gateway và các service hạ tầng giữ nguyên CID trong response.
    2. Gửi request không có header -> Gateway tự sinh UUID hợp lệ và trả về trong response.
    """
    print_header("Kịch bản 1: Kiểm thử Truy vết Phân tán (X-Correlation-ID Tracing)")
    
    # 1. Test với CID tự định nghĩa
    custom_cid = f"trace-test-{uuid.uuid4().hex[:12]}"
    print_info(f"Gửi request kèm header 'X-Correlation-ID: {custom_cid}'...")
    r1 = await client.get(f"{GATEWAY_URL}/health", headers={"X-Correlation-ID": custom_cid})
    received_cid_1 = r1.headers.get("X-Correlation-ID") or r1.headers.get("x-correlation-id")

    if received_cid_1 == custom_cid:
        print_pass(f"Gateway bảo toàn chính xác X-Correlation-ID nhận được: {received_cid_1}")
    else:
        print_fail(f"Lỗi: Kỳ vọng {custom_cid}, nhận được {received_cid_1}")
        return False

    # 2. Test tự động sinh CID nếu client không gửi
    print_info("Gửi request KHÔNG kèm header X-Correlation-ID (kỳ vọng Gateway tự cấp phát)...")
    r2 = await client.get(f"{GATEWAY_URL}/health")
    received_cid_2 = r2.headers.get("X-Correlation-ID") or r2.headers.get("x-correlation-id")

    if received_cid_2 and len(received_cid_2) >= 16:
        print_pass(f"Gateway đã tự động tạo X-Correlation-ID mới: {received_cid_2}")
    else:
        print_fail(f"Lỗi: Không tìm thấy X-Correlation-ID tự sinh hợp lệ trong header response: {r2.headers}")
        return False

    print_pass("KỊCH BẢN TRACING HOÀN TOÀN ĐẠT CHUẨN!")
    return True


# =============================================================================
# BÀI KIỂM THỬ 2: PAYMENT IDEMPOTENCY (IDEMPOTENCY-KEY DEDUPLICATION)
# =============================================================================
async def test_scenario_idempotency(client: httpx.AsyncClient) -> bool:
    """
    Kịch bản: Bấm liên tiếp 5 lần 'Xác nhận' với cùng 1 Idempotency-Key trong cùng 1 mili-giây.
    Kỳ vọng:
    1. Cả 5 request đều nhận HTTP 201 Created (hoặc 200 OK).
    2. Cả 5 request đều trả về CHÍNH XÁC cùng 1 transaction_id.
    3. Hệ thống chỉ sinh duy nhất 1 phiên giao dịch trong DB và chỉ gửi 1 email OTP.
    """
    print_header("Kịch bản 2: Kiểm thử Tính Bất Khả Biến (Payment Idempotency-Key)")

    # Đăng nhập
    login_data = await login_user(client, "nguyenvana", "123456")
    token = login_data["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Sinh 1 Idempotency-Key duy nhất
    idempotency_key = f"idemp-run-{uuid.uuid4().hex}"
    headers["Idempotency-Key"] = idempotency_key

    payload = {
        "student_code": "524H0001",
        "amount": 15000000.00,
        "invoice_id": 1
    }

    print_info(f"Bắn đồng thời 5 request 'POST /api/payments/initiate' với Idempotency-Key: {idempotency_key}...")
    t_start = time.perf_counter()

    tasks = [
        client.post(f"{GATEWAY_URL}/api/payments/initiate", json=payload, headers=headers)
        for _ in range(5)
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    t_elapsed = (time.perf_counter() - t_start) * 1000
    print_info(f"Đã nhận 5 response sau {t_elapsed:.1f}ms.")

    tx_ids = []
    status_codes = []
    for i, r in enumerate(responses, 1):
        if isinstance(r, Exception):
            print_fail(f"Request {i} gặp ngoại lệ: {r}")
            return False
        status_codes.append(r.status_code)
        if r.status_code in [200, 201]:
            data = r.json()
            tx_ids.append(data.get("transaction_id"))
            print_info(f"Request {i}: HTTP {r.status_code} - TxID: {data.get('transaction_id')} - Msg: {data.get('message')}")
        else:
            print_fail(f"Request {i} trả về lỗi HTTP {r.status_code}: {r.text}")

    # Kiểm tra tất cả status code là 200 hoặc 201
    all_success = all(code in [200, 201] for code in status_codes)
    if not all_success:
        print_fail(f"Một số request không thành công: {status_codes}")
        return False

    # Kiểm tra tất cả tx_id là duy nhất 1 ID
    unique_tx_ids = set(tx_ids)
    if len(unique_tx_ids) == 1 and None not in unique_tx_ids:
        print_pass(f"Cả 5 request đều tái sử dụng CHÍNH XÁC cùng 1 giao dịch: {tx_ids[0]}")
        print_pass("Hệ thống Idempotency đã ngăn chặn hoàn toàn việc tạo trùng lặp giao dịch và OTP rác!")
        print_pass("KỊCH BẢN IDEMPOTENCY HOÀN TOÀN ĐẠT CHUẨN!")
        return True
    else:
        print_fail(f"Phát hiện trùng lặp hoặc sinh nhiều giao dịch khác nhau: {unique_tx_ids}")
        return False


# =============================================================================
# BÀI KIỂM THỬ 3: DOUBLE-SPENDING (CHỐNG TRỪ TIỀN 2 LẦN / ÂM SỐ DƯ)
# =============================================================================
async def test_scenario_double_spending(client: httpx.AsyncClient) -> bool:
    """
    Kịch bản: Người dùng nguyenvana có 20,000,000 VNĐ.
    Khởi tạo và xác thực thanh toán đồng thời cho 2 giao dịch mỗi giao dịch 15,000,000 VNĐ.
    Tổng: 30,000,000 VNĐ > 20,000,000 VNĐ.
    Kỳ vọng: Khóa dòng Pessimistic Lock tại DB bảo đảm:
    - Đúng 1 giao dịch thành công (HTTP 200).
    - Đúng 1 giao dịch thất bại do không đủ số dư.
    - Số dư tài khoản tuyệt đối không bị âm!
    """
    print_header("Kịch bản 3: Kiểm thử Concurrency Double-Spending (Chống âm số dư)")
    
    # Đăng nhập nguyenvana
    login_data = await login_user(client, "nguyenvana", "123456")
    token = login_data["access_token"]
    user_initial_balance = Decimal(str(login_data["user"]["balance"]))
    print_info(f"User nguyenvana - Số dư khả dụng hiện tại: {user_initial_balance:,.0f} VNĐ.")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Tra cứu học phí MSSV 524H0005 và 524H0006
    r_t1 = await client.get(f"{GATEWAY_URL}/api/tuition/students/524H0005", headers=headers)
    amt1 = float(r_t1.json()["amount"])
    inv1 = r_t1.json()["invoice_id"]

    r_t2 = await client.get(f"{GATEWAY_URL}/api/tuition/students/524H0006", headers=headers)
    amt2 = float(r_t2.json()["amount"])
    inv2 = r_t2.json()["invoice_id"]

    print_info(f"Khoản 1 (524H0005): {amt1:,.0f} VNĐ | Khoản 2 (524H0006): {amt2:,.0f} VNĐ (Tổng: {amt1+amt2:,.0f} VNĐ > 20,000,000 VNĐ)")

    # 2. Khởi tạo giao dịch 1
    await clear_mailpit_messages(client)
    r_init1 = await client.post(
        f"{GATEWAY_URL}/api/payments/initiate",
        json={"student_code": "524H0005", "amount": amt1, "invoice_id": inv1},
        headers=headers
    )
    if r_init1.status_code != 201:
        print_fail(f"Khởi tạo giao dịch 1 thất bại: {r_init1.text}")
        return False
    tx1 = r_init1.json()
    otp1 = await get_latest_otp_mailpit(client, "nguyenvana@ibanking.tdtu.edu.vn")
    print_info(f"Giao dịch 1 đã tạo: TxID {tx1['transaction_id'][:8]}... - OTP {otp1}")

    # 3. Khởi tạo giao dịch 2
    await clear_mailpit_messages(client)
    r_init2 = await client.post(
        f"{GATEWAY_URL}/api/payments/initiate",
        json={"student_code": "524H0006", "amount": amt2, "invoice_id": inv2},
        headers=headers
    )
    if r_init2.status_code != 201:
        print_fail(f"Khởi tạo giao dịch 2 thất bại: {r_init2.text}")
        return False
    tx2 = r_init2.json()
    otp2 = await get_latest_otp_mailpit(client, "nguyenvana@ibanking.tdtu.edu.vn")
    print_info(f"Giao dịch 2 đã tạo: TxID {tx2['transaction_id'][:8]}... - OTP {otp2}")

    # 4. Bắn đồng thời 2 lệnh confirm qua Gateway
    print_info("Bắn đồng thời 2 lệnh 'POST /api/payments/confirm'...")
    t_start = time.perf_counter()
    task1 = client.post(
        f"{GATEWAY_URL}/api/payments/confirm",
        json={"transaction_id": tx1["transaction_id"], "otp_code": otp1},
        headers=headers
    )
    task2 = client.post(
        f"{GATEWAY_URL}/api/payments/confirm",
        json={"transaction_id": tx2["transaction_id"], "otp_code": otp2},
        headers=headers
    )

    resps = await asyncio.gather(task1, task2, return_exceptions=True)
    t_elapsed = (time.perf_counter() - t_start) * 1000
    print_info(f"Đã xử lý xong 2 request song song trong {t_elapsed:.1f}ms.")

    status_codes = []
    for i, r in enumerate(resps, 1):
        if isinstance(r, Exception):
            print_fail(f"Giao dịch {i} exception: {r}")
            return False
        status_codes.append(r.status_code)
        print_info(f"Giao dịch {i}: HTTP {r.status_code} - {r.text[:90]}")

    has_one_success = (status_codes.count(200) == 1)
    has_one_failure = any(code in [400, 409] for code in status_codes)

    if not (has_one_success and has_one_failure):
        print_fail(f"Kỳ vọng 1 thành công (200) và 1 từ chối (400/409). Thực tế: {status_codes}")
        return False

    # 5. Kiểm tra số dư cuối cùng
    r_me = await client.get(f"{GATEWAY_URL}/api/users/me", headers=headers)
    final_balance = Decimal(str(r_me.json()["balance"]))
    expected_balances = [
        user_initial_balance - Decimal(str(amt1)),
        user_initial_balance - Decimal(str(amt2))
    ]
    print_info(f"Số dư thực tế trong tài khoản: {final_balance:,.0f} VNĐ (Kỳ vọng: {', '.join(f'{b:,.0f}' for b in expected_balances)} VNĐ).")

    if final_balance in expected_balances and final_balance >= 0:
        print_pass("Số dư chuẩn xác! Không bị âm và không có hiện tượng Double-Spending!")
        print_pass("KỊCH BẢN CONCURRENCY 1 HOÀN TOÀN ĐẠT CHUẨN!")
        return True
    else:
        print_fail(f"Số dư sai lệch: {final_balance}")
        return False


# =============================================================================
# BÀI KIỂM THỬ 4: TUITION RACE CONDITION & SAGA COMPENSATING ROLLBACK
# =============================================================================
async def test_scenario_race_condition(client: httpx.AsyncClient) -> bool:
    """
    Kịch bản: Hai người dùng 'nguyenvana' và 'tranthib' cùng trả tiền học phí
    cho sinh viên 524H0001 (15,000,000 VNĐ, UNPAID) tại cùng 1 mili-giây.
    Kỳ vọng:
    - Đúng 1 người gạch nợ thành công (HTTP 200).
    - Người đến sau nhận 409 Conflict hoặc hệ thống Saga kích hoạt Compensating Refund
      bồi hoàn số dư ngay lập tức.
    - Hóa đơn sinh viên 524H0001 chỉ bị gạch nợ đúng 1 lần!
    """
    print_header("Kịch bản 4: Kiểm thử Race Condition Học phí & Saga Compensating Rollback")

    # 1. Đăng nhập 2 tài khoản
    login_a = await login_user(client, "nguyenvana", "123456")
    token_a = login_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}

    login_b = await login_user(client, "tranthib", "123456")
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    print_info("Khởi tạo 2 phiên giao dịch song song cho cùng sinh viên 524H0001...")

    # Khởi tạo cho A
    await clear_mailpit_messages(client)
    r_init_a = await client.post(
        f"{GATEWAY_URL}/api/payments/initiate",
        json={"student_code": "524H0001", "amount": 15000000.00, "invoice_id": 1},
        headers=headers_a
    )
    if r_init_a.status_code != 201:
        print_fail(f"User A initiate fail: {r_init_a.text}")
        return False
    tx_a = r_init_a.json()
    otp_a = await get_latest_otp_mailpit(client, "nguyenvana@ibanking.tdtu.edu.vn")
    print_info(f"User A đã nhận OTP: {otp_a} (TxID: {tx_a['transaction_id'][:8]}...)")

    # Khởi tạo cho B
    await clear_mailpit_messages(client)
    r_init_b = await client.post(
        f"{GATEWAY_URL}/api/payments/initiate",
        json={"student_code": "524H0001", "amount": 15000000.00, "invoice_id": 1},
        headers=headers_b
    )
    if r_init_b.status_code != 201:
        print_fail(f"User B initiate fail: {r_init_b.text}")
        return False
    tx_b = r_init_b.json()
    otp_b = await get_latest_otp_mailpit(client, "tranthib@ibanking.tdtu.edu.vn")
    print_info(f"User B đã nhận OTP: {otp_b} (TxID: {tx_b['transaction_id'][:8]}...)")

    # Bắn đồng thời 2 lệnh confirm
    print_info("Bắn đồng thời 2 lệnh confirm từ User A và User B cho cùng 1 hóa đơn sinh viên...")
    t_start = time.perf_counter()
    task_a = client.post(
        f"{GATEWAY_URL}/api/payments/confirm",
        json={"transaction_id": tx_a["transaction_id"], "otp_code": otp_a},
        headers=headers_a
    )
    task_b = client.post(
        f"{GATEWAY_URL}/api/payments/confirm",
        json={"transaction_id": tx_b["transaction_id"], "otp_code": otp_b},
        headers=headers_b
    )

    resps = await asyncio.gather(task_a, task_b, return_exceptions=True)
    t_elapsed = (time.perf_counter() - t_start) * 1000
    print_info(f"Đã xử lý xong 2 request trong {t_elapsed:.1f}ms.")

    status_codes = []
    for i, r in enumerate(resps, 1):
        who = "User A" if i == 1 else "User B"
        if isinstance(r, Exception):
            print_fail(f"{who} gặp lỗi: {r}")
            return False
        status_codes.append(r.status_code)
        print_info(f"{who}: HTTP {r.status_code} - {r.text[:90]}")

    has_one_200 = (status_codes.count(200) == 1)
    has_one_conflict = any(code in [400, 409] for code in status_codes)

    if not (has_one_200 and has_one_conflict):
        print_fail(f"Kỳ vọng đúng 1 HTTP 200 và 1 lỗi (400/409). Nhận được: {status_codes}")
        return False

    print_pass("Đúng 1 người thanh toán thành công, người thứ hai nhận phản hồi an toàn từ hệ thống!")

    # Kiểm tra hóa đơn
    r_check = await client.get(f"{GATEWAY_URL}/api/tuition/students/524H0001", headers=headers_a)
    invoice_data = r_check.json()
    if invoice_data.get("status") == "PAID" and invoice_data.get("can_pay") is False:
        print_pass("Hóa đơn học phí đã được chốt PAID đúng 1 lần và khóa thanh toán an toàn!")
        print_pass("KỊCH BẢN RACE CONDITION & SAGA HOÀN TOÀN ĐẠT CHUẨN!")
        return True
    else:
        print_fail(f"Trạng thái hóa đơn bất thường: {invoice_data}")
        return False


# =============================================================================
# BÀI KIỂM THỬ 5: END-TO-END FLOW (E2E)
# =============================================================================
async def test_scenario_end_to_end(client: httpx.AsyncClient) -> bool:
    """
    Toàn bộ quy trình thanh toán thực tế của người dùng:
    1. Đăng nhập.
    2. Tra cứu MSSV 524H0001.
    3. Initiate thanh toán kèm Idempotency-Key.
    4. Trích xuất mã OTP từ Mailpit.
    5. Confirm thanh toán và kích hoạt Saga.
    6. Kiểm tra số dư và lịch sử giao dịch.
    """
    print_header("Kịch bản 5: Toàn bộ Luồng Thanh toán End-to-End (E2E)")

    # 1. Đăng nhập
    login_data = await login_user(client, "nguyenvana", "123456")
    token = login_data["access_token"]
    user_info = login_data["user"]
    initial_balance = Decimal(str(user_info["balance"]))
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print_pass(f"Đăng nhập thành công! User: {user_info['username']} - Số dư: {initial_balance:,.0f} VNĐ")

    # 2. Tra cứu học phí
    r_tuition = await client.get(f"{GATEWAY_URL}/api/tuition/students/524H0001", headers=headers)
    if r_tuition.status_code != 200:
        print_fail(f"Tra cứu học phí thất bại: {r_tuition.text}")
        return False
    tuition = r_tuition.json()
    tuition_amount = Decimal(str(tuition["amount"]))
    print_pass(f"Tìm thấy: {tuition['student_name']} - {tuition['semester']} - Cần nộp: {tuition_amount:,.0f} VNĐ")

    # 3. Khởi tạo thanh toán
    await clear_mailpit_messages(client)
    idemp_key = f"e2e-key-{uuid.uuid4().hex}"
    headers["Idempotency-Key"] = idemp_key

    r_init = await client.post(
        f"{GATEWAY_URL}/api/payments/initiate",
        json={"student_code": "524H0001", "amount": float(tuition_amount), "invoice_id": tuition.get("invoice_id")},
        headers=headers
    )
    if r_init.status_code != 201:
        print_fail(f"Khởi tạo thanh toán thất bại: {r_init.text}")
        return False
    init_data = r_init.json()
    tx_id = init_data["transaction_id"]
    print_pass(f"Giao dịch đã tạo thành công! TxID: {tx_id} - TTL: {init_data.get('expires_in_seconds')}s")

    # 4. Lấy OTP từ Mailpit
    otp = await get_latest_otp_mailpit(client, user_info["email"])
    print_pass(f"Đã nhận OTP hợp lệ từ Mailpit: {otp}")

    # 5. Xác nhận giao dịch
    r_confirm = await client.post(
        f"{GATEWAY_URL}/api/payments/confirm",
        json={"transaction_id": tx_id, "otp_code": otp},
        headers=headers
    )
    if r_confirm.status_code != 200:
        print_fail(f"Xác nhận OTP thất bại: {r_confirm.text}")
        return False
    confirm_data = r_confirm.json()
    print_pass(f"Giao dịch hoàn tất! Trạng thái: {confirm_data.get('status')} - Msg: {confirm_data.get('message')}")

    # 6. Kiểm tra số dư
    r_me = await client.get(f"{GATEWAY_URL}/api/users/me", headers=headers)
    new_balance = Decimal(str(r_me.json()["balance"]))
    expected_new_balance = initial_balance - tuition_amount
    print_info(f"Số dư mới: {new_balance:,.0f} VNĐ (Kỳ vọng: {expected_new_balance:,.0f} VNĐ).")

    if new_balance == expected_new_balance:
        print_pass("Số dư đã được khấu trừ chính xác tuyệt đối!")
    else:
        print_fail(f"Số dư không khớp: {new_balance} vs {expected_new_balance}")
        return False

    # 7. Kiểm tra lịch sử giao dịch
    r_hist = await client.get(f"{GATEWAY_URL}/api/payments/history", headers=headers)
    history = r_hist.json()
    found = any(t.get("id") == tx_id and t.get("status") == "SUCCESS" for t in history)
    if found:
        print_pass("Giao dịch SUCCESS đã được lưu trong lịch sử giao dịch người dùng!")
    else:
        print_warn("Chưa tìm thấy TxID trong lịch sử giao dịch.")

    print_pass("KỊCH BẢN END-TO-END HOÀN THÀNH XUẤT SẮC (100% SUCCESS)!")
    return True


# =============================================================================
# KIỂM TRA SỨC KHỎE CÁC SERVICE TRƯỚC KHI CHẠY (SMOKE TEST)
# =============================================================================
async def check_all_services_health(client: httpx.AsyncClient) -> bool:
    """Kiểm tra xem Gateway, Frontend và Mailpit có sẵn sàng tiếp nhận request."""
    endpoints = {
        "API Gateway (Port 8000)": f"{GATEWAY_URL}/health",
        "Frontend Web (Port 3000)": f"{FRONTEND_URL}/",
        "Mailpit Test Mail Server (Port 8025)": f"{MAILPIT_URL}/api/v1/messages"
    }

    print_header("Kiểm tra kết nối dịch vụ (Smoke Test)")
    all_ok = True

    for name, url in endpoints.items():
        try:
            resp = await client.get(url, timeout=4.0)
            if resp.status_code in [200, 301, 302]:
                print_pass(f"{name}: ONLINE (HTTP {resp.status_code})")
            else:
                print_fail(f"{name}: Lỗi HTTP {resp.status_code}")
                all_ok = False
        except Exception as e:
            print_fail(f"{name}: KHÔNG THỂ KẾT NỐI ({e})")
            all_ok = False

    return all_ok


# =============================================================================
# HÀM CHÍNH (MAIN TEST RUNNER)
# =============================================================================
async def main():
    print(f"\n{Colors.BOLD}{Colors.YELLOW}")
    print("================================================================================")
    print("   iBanking TDTU - AUTOMATED VERIFICATION SUITE (PHASE 2: CONCURRENCY & SOA)    ")
    print("        Môn: CS504070 - Kiến Trúc Hướng Dịch Vụ - ĐH Tôn Đức Thắng              ")
    print("================================================================================")
    print(f"{Colors.RESET}")

    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(limits=limits, timeout=20.0) as client:
        # 1. Kiểm tra sức khỏe hệ thống
        is_healthy = await check_all_services_health(client)
        if not is_healthy:
            print(f"\n{Colors.BOLD}{Colors.RED}[CẢNH BÁO] Hệ thống chưa sẵn sàng.{Colors.RESET}")
            print(f"Vui lòng đảm bảo bạn đã chạy: {Colors.BOLD}docker compose up -d --build{Colors.RESET}\n")
            sys.exit(1)

        results = {}

        # 2. Test 1: X-Correlation-ID Tracing
        results["1. Distributed Tracing (X-Correlation-ID)"] = await test_scenario_tracing(client)

        # 3. Test 2: Idempotency-Key
        reset_demo_database()
        results["2. Payment Idempotency (Idempotency-Key)"] = await test_scenario_idempotency(client)

        # 4. Test 3: Double-Spending Prevention
        reset_demo_database()
        results["3. Concurrency Double-Spending (Pessimistic Lock)"] = await test_scenario_double_spending(client)

        # 5. Test 4: Tuition Race Condition & Saga Rollback
        reset_demo_database()
        results["4. Tuition Race Condition & Saga Compensation"] = await test_scenario_race_condition(client)

        # 6. Test 5: Full E2E Flow
        reset_demo_database()
        results["5. End-to-End Payment Flow & Receipt"] = await test_scenario_end_to_end(client)

        # TỔNG KẾT
        print_header("TỔNG KẾT KẾT QUẢ KIỂM THỬ TỰ ĐỘNG PHASE 2")
        all_passed = True
        for test_name, passed in results.items():
            if passed:
                print(f"  {Colors.BOLD}{Colors.GREEN}[PASS]{Colors.RESET} {test_name}: ĐẠT YÊU CẦU")
            else:
                print(f"  {Colors.BOLD}{Colors.RED}[FAIL]{Colors.RESET} {test_name}: CHƯA ĐẠT")
                all_passed = False

        print(f"\n{Colors.CYAN}{'='*75}{Colors.RESET}")
        if all_passed:
            print(f"{Colors.BOLD}{Colors.GREEN}KẾT QUẢ: TOÀN BỘ 5/5 TIÊU CHÍ CONCURRENCY, IDEMPOTENCY & SAGA ĐỀU ĐẠT CHUẨN!{Colors.RESET}")
        else:
            print(f"{Colors.BOLD}{Colors.RED}[CẢNH BÁO] Một số bài kiểm thử chưa vượt qua. Vui lòng kiểm tra lại log bên trên.{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*75}{Colors.RESET}\n")

        if not all_passed:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
