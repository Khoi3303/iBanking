# iBanking Microservices - Hệ thống Thanh toán Học phí TDTU (SOA Architecture)

Hệ thống ngân hàng số và cổng thanh toán học phí đại học theo kiến trúc **Service-Oriented Architecture (SOA) / Microservices**, được thiết kế theo tiêu chuẩn công nghiệp với cơ chế bảo mật nghiêm ngặt, quản trị dữ liệu độc lập và điều phối giao dịch phân tán Saga.

---

## 1. Kiến trúc Tổng quan & Phân quyền Cơ sở Dữ liệu

```text
               [ Trình duyệt / Web Client ] (Port 3000)
                               │
                               ▼
               [ API Gateway (FastAPI) ] (Port 8000)
                               │
     ┌─────────────────────────┼─────────────────────────┐
     ▼ (Docker Network)        ▼                         ▼
[ User Service ]       [ Tuition Service ]       [ Payment Service ]
     │ (Port 8001)             │ (Port 8002)             │ (Port 8003)
     │                         │                         │
     ▼ (User DB User)          ▼ (Tuition DB User)       ▼ (Payment DB User)
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ ibanking_user_db│       │ tdtu_tuition_db │       │ibanking_payment │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                                                             ▼
                                                    [ Redis 7 (OTP & Lock) ]
```

### Nguyên tắc Database Ownership (Least Privilege):
- **Không service nào chạy bằng tài khoản `root`**.
- `User Service` sử dụng tài khoản `ibanking_user_app` chỉ có quyền trên `ibanking_user_db`.
- `Tuition Service` sử dụng tài khoản `ibanking_tuition_app` chỉ có quyền trên `tdtu_tuition_db`.
- `Payment Service` sử dụng tài khoản `ibanking_payment_app` chỉ có quyền trên `ibanking_payment_db`.
- Cổng kết nối của Database, Redis và các microservices nội bộ được cô lập hoàn toàn trong mạng Docker ảo, chỉ mở cổng công khai cho **Frontend (3000)** và **API Gateway (8000)**.

---

## 2. Hướng dẫn Khởi chạy Nhanh (1-Click Setup)

### Bước 1: Clone kho mã nguồn
```bash
git clone https://github.com/Khoi3303/iBanking.git
cd iBanking
```

### Bước 2: Chạy script khởi tạo môi trường tự động
Chạy file script:
```powershell
.\setup.bat
```
*(hoặc `powershell -ExecutionPolicy Bypass -File .\setup.ps1`)*

> Script sẽ tự động:
> 1. Copy file mẫu `.env.example` thành `.env`.
> 2. Tự động sinh ngẫu nhiên các khóa bảo mật mạnh (CSPRNG 32/64 bytes) cho `JWT_SECRET_KEY`, `INTERNAL_API_KEY` và mật khẩu cho từng tài khoản cơ sở dữ liệu.
> 3. Hỗ trợ kích hoạt `docker compose up -d --build` để khởi chạy toàn bộ dịch vụ.

### Bước 3: Truy cập hệ thống
- **Giao diện Web iBanking:** [http://localhost:3000](http://localhost:3000)
- **API Gateway Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Danh sách Tài khoản Kiểm thử (Demo Credentials)

> **Ghi chú:** Các tài khoản bên dưới được cấu hình sẵn trong dữ liệu khởi tạo (`database/init.sql`) phục vụ kiểm thử và chấm đồ án. Mật khẩu được mã hóa an toàn bằng thuật toán **Bcrypt** trong cơ sở dữ liệu.

| Tên đăng nhập (Username) | Mật khẩu Demo | Họ và tên | Số dư kiểm thử | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **`nguyenvana`** | `123456` | Nguyễn Văn A | 20.000.000 VNĐ | Hoạt động |
| **`tranthib`** | `123456` | Trần Thị B | 15.000.000 VNĐ | Hoạt động |
| **`lethanhc`** | `123456` | Lê Thành C | 5.000.000 VNĐ | Hoạt động |
| **`lekhoi3303`** | `123456` | Lê Khôi | 20.000.000 VNĐ | Hoạt động |
| **`tienmobile2006`** | `123456` | Nguyễn Thanh Tiền | 20.000.000 VNĐ | Hoạt động |
| **`mensieu123`** | `123456` | Nguyễn Minh Đăng | 20.000.000 VNĐ | Hoạt động |

### Danh sách Mã Sinh Viên (MSSV) kiểm tra học phí:
- `524H0001` (Nguyễn Văn An - Khoa CNTT - Học phí: 15.000.000 VNĐ - `UNPAID`)
- `524H0005` (Đỗ Gia Bảo - Khoa CNTT - Học phí: 14.000.000 VNĐ - `UNPAID`)
- `524H0006` (Hoàng Thị Lan - Khoa QTKD - Học phí: 11.500.000 VNĐ - `UNPAID`)
- `524H0003` (Trần Văn Cường - Học phí: 50.000.000 VNĐ - Kiểm tra xử lý thiếu số dư)
- `524H0002` (Trần Thị Bình - Đã thanh toán trước đó - `PAID`)

---

## 4. Đặc tả Tiêu chuẩn Bảo mật (Security Highlights)

1. **Fail-Fast Configuration (Không dùng Hardcoded Secret Fallback):**
   - Tất cả các biến môi trường nhạy cảm (`JWT_SECRET_KEY`, `INTERNAL_API_KEY`, mật khẩu database của từng dịch vụ) được khai báo bắt buộc bằng Pydantic BaseSettings.
   - Ứng dụng sẽ từ chối khởi động ngay lập tức nếu thiếu các khóa cấu hình trong `.env`, ngăn ngừa việc chạy ứng dụng với khóa mặc định không an toàn.

2. **Cơ chế OTP CSPRNG & SHA-256:**
   - Mã OTP 6 chữ số được tạo bằng bộ sinh số ngẫu nhiên mật mã học (`secrets.randbelow`).
   - Mã OTP được lưu dưới dạng chuỗi băm **SHA-256** cả trong Redis và bảng giao dịch của MySQL, không lưu trữ OTP dạng thô.
   - Giới hạn tối đa 5 lần thử sai trước khi tự động hủy mã.
   - Hủy OTP ngay sau khi sử dụng thành công (Single-use OTP).

3. **Phân quyền và Cô lập Cơ sở Dữ liệu:**
   - Mỗi microservice sở hữu một schema độc lập và một database user riêng biệt.
   - Nếu một dịch vụ bị tấn công, kẻ tấn công không thể đọc hoặc ghi đè dữ liệu của các dịch vụ khác trên MySQL.

4. **Kiểm tra Mật khẩu Bcrypt:**
   - Xác thực danh tính hoàn toàn qua `passlib.context.CryptContext(schemes=["bcrypt"])`.
   - Không tồn tại mã backdoor hay bypass điều kiện kiểm tra mật khẩu.

---

## 5. Hướng dẫn Reset Dữ liệu Demo

Để đưa toàn bộ học phí về `UNPAID` và số dư về trạng thái ban đầu để kiểm thử lại nhiều lần:
```powershell
.\reset_demo.bat
```
hoặc chạy bằng lệnh (sử dụng mật khẩu quản trị trong file .env):
```bash
docker compose exec -T -e MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysql mysql --default-character-set=utf8mb4 -u root < database/reset_demo.sql
```
