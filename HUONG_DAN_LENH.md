# BẢNG TỔNG HỢP CÂU LỆNH THƯỜNG DÙNG - iBanking TDTU (SOA)

Tài liệu này tổng hợp các câu lệnh thông dụng trong quá trình phát triển, kiểm thử và demo đồ án **iBanking Microservices**.

---

## 1. CÁC FILE SCRIPT CHẠY NHANH

Trong thư mục gốc của dự án có sẵn các file script hỗ trợ thao tác nhanh:

| File Script | Mục đích sử dụng | Khi nào dùng? |
| :--- | :--- | :--- |
| **`setup.bat`** | Khởi tạo cấu hình môi trường `.env` tự động với các secret ngẫu nhiên bảo mật và tùy chọn chạy hệ thống. | Khi vừa `git clone` về máy lần đầu tiên. |
| **`start.bat`** | Khởi động toàn bộ hệ thống (Build + MySQL + Redis + Microservices). | Khi mới mở máy tính, hoặc muốn khởi động toàn bộ hệ thống từ đầu. |
| **`rebuild.bat`** | Rebuild và cập nhật nhanh các service đã sửa code. | Sau khi vừa sửa code Frontend, Gateway hoặc các service. |
| **`reset_demo.bat`** | Đặt lại trạng thái dữ liệu demo ban đầu và số dư tài khoản về 20.000.000đ. | Dùng sau khi vừa thanh toán xong để kiểm thử lại từ đầu. |

---

## 2. CÂU LỆNH RESET DỮ LIỆU VÀ TRẠNG THÁI

### Cách 1: Reset dữ liệu qua script SQL (Khuyên dùng)
Chạy file script `reset_demo.bat` hoặc dùng lệnh PowerShell:
```powershell
.\reset_demo.bat
```
*(Lệnh này đặt lại trạng thái các hóa đơn học phí về `UNPAID`, xóa lịch sử giao dịch cũ và đặt lại số dư 20.000.000 VNĐ cho các tài khoản kiểm thử).*

> **Lưu ý:** Hệ thống đã được bổ sung sẵn danh sách hơn 15 mã sinh viên (MSSV) còn nợ học phí (< 20 triệu) để kiểm thử thanh toán liên tục mà không bắt buộc phải reset:
> - `524H0001` (15.000.000đ - Nguyễn Văn An)
> - `524H0005` (14.000.000đ - Đỗ Gia Bảo)
> - `524H0006` (11.500.000đ - Hoàng Thị Lan)
> - `524H0007` (16.000.000đ - Vũ Đình Trọng)
> - `524H0008` (13.200.000đ - Bùi Ngọc Ánh)
> - `524H0009` (15.500.000đ - Phan Quốc Huy)
> - `524H0010` (9.800.000đ - Nguyễn Thùy Trang)
> - `524H0011` (8.500.000đ - Đặng Minh Khang)
> - `524H0012` (12.500.000đ - Trịnh Mỹ Duyên)
> - `524H0013` (7.500.000đ - Huỳnh Nhật Minh)
> - `524H0014` (10.200.000đ - Mai Phương Thảo)
> - `524H0015` (6.800.000đ - Lương Thế Vinh)
> - `524H0016` (13.000.000đ - Cao Thu Hà)
> - `524H0017` (5.500.000đ - Tạ Quang Khải)
> - `524H0018` (11.000.000đ - Đoàn Yến Nhi)
> - `524H0019` (8.900.000đ - Ngô Gia Khiêm)
> - `524H0020` (14.500.000đ - Chu Bảo Trâm)
> - *Các trường hợp đặc biệt:* `524H0002` (Đã đóng), `524H0003` (50 triệu - Kiểm tra thiếu số dư), `524H0004` (Không có nợ học phí).

---

### Cách 2: Khởi tạo lại Database từ đầu
```powershell
docker compose down -v
docker compose up -d
```
*(Tham số `-v` xóa các volume dữ liệu cũ và nạp lại toàn bộ file `database/init.sql`).*

---

## 3. CÂU LỆNH KHI CHỈNH SỬA CODE (REBUILD TỪNG SERVICE)

Khi chỉnh sửa code của một service cụ thể, chỉ cần rebuild đúng service đó:

### Khi sửa giao diện Frontend (HTML / CSS / JS):
```powershell
docker compose up -d --build frontend
```
*(Sau đó mở trình duyệt bấm Ctrl + F5 để xem thay đổi).*

### Khi sửa User & Account Service:
```powershell
docker compose up -d --build user-service
```

### Khi sửa API Gateway:
```powershell
docker compose up -d --build api-gateway
```

### Khi sửa Payment Service:
```powershell
docker compose up -d --build payment-service
```

### Khi sửa Tuition Service:
```powershell
docker compose up -d --build tuition-service
```

### Khi sửa Notification Service:
```powershell
docker compose up -d --build notification-service
```

### Rebuild các service chính và nạp lại dữ liệu:
```powershell
docker compose up -d --build user-service tuition-service payment-service notification-service api-gateway frontend
.\reset_demo.bat
```

---

## 4. CÂU LỆNH XEM LOGS THEO THỜI GIAN THỰC

* **Xem log gửi Email (Notification Service):**
  ```powershell
  docker compose logs -f notification-service
  ```
* **Xem log điều phối giao dịch (Payment Service):**
  ```powershell
  docker compose logs -f payment-service
  ```
* **Xem log tài khoản và số dư (User Service):**
  ```powershell
  docker compose logs -f user-service
  ```
* **Xem log của tất cả các container cùng lúc:**
  ```powershell
  docker compose logs -f
  ```
*(Nhấn `Ctrl + C` để thoát khỏi màn hình xem log).*

---

## 5. CÂU LỆNH QUẢN LÝ DOCKER CONTAINER

* **Kiểm tra trạng thái các container đang chạy:**
  ```powershell
  docker compose ps
  ```
* **Khởi động các container:**
  ```powershell
  docker compose up -d
  ```
* **Tạm dừng hệ thống:**
  ```powershell
  docker compose stop
  ```
* **Khởi động lại sau khi tạm dừng:**
  ```powershell
  docker compose start
  ```
* **Tắt và xóa các container:**
  ```powershell
  docker compose down
  ```

---

## 6. CÂU LỆNH CHẠY KIỂM THỬ TỰ ĐỘNG (CONCURRENCY & SAGA)

1. Kích hoạt chạy test:
   ```powershell
   python scripts\test_concurrency.py
   ```
   *(Hoặc nhấp đúp vào `scripts\run_tests.bat`).*

2. Các kịch bản kiểm thử:
   - Scenario 1: Double-Spending Test (Khóa `SELECT ... FOR UPDATE` chống âm tiền).
   - Scenario 2: Race Condition Test (Hai người cùng thanh toán 1 hóa đơn).
   - Scenario 3: E2E Payment Flow & Saga Compensation.

---

## 7. CÂU LỆNH GIT LÀM VIỆC NHÓM

* **Gỡ bỏ theo dõi file .env (Bảo vệ mật khẩu/SMTP không bị lộ):**
  ```powershell
  git rm --cached .env
  ```
  *(Hoặc chạy nhanh file `untrack_secrets.bat`).*
* **Xem các file đã thay đổi:**
  ```powershell
  git status
  ```
* **Lưu và đẩy code lên GitHub:**
  ```powershell
  git add .
  git commit -m "Cap nhat he thong iBanking"
  git push origin main
  ```
* **Kéo code mới về máy:**
  ```powershell
  git pull origin main
  ```

---

## 8. DANH SÁCH TÀI KHOẢN TEST (SỐ DƯ 20.000.000 VNĐ)

Mật khẩu chung cho tất cả tài khoản: `123456`

| Tên đăng nhập | Mật khẩu | Họ và tên | Email nhận mã OTP | Số dư khả dụng |
| :--- | :--- | :--- | :--- | :--- |
| **`nguyenvana`** | `123456` | Nguyễn Văn A | `nguyenvana@ibanking.tdtu.edu.vn` | `20.000.000 VNĐ` |
| **`lekhoi3303`** | `123456` | Lê Khôi | `lekhoi3303@ibanking.tdtu.edu.vn` | `20.000.000 VNĐ` |
| **`tienmobile2006`** | `123456` | Nguyễn Thanh Tiền | `tienmobile@ibanking.tdtu.edu.vn` | `20.000.000 VNĐ` |
| **`mensieu123`** | `123456` | Nguyễn Minh Đăng | `mensieu@ibanking.tdtu.edu.vn` | `20.000.000 VNĐ` |
| **`tranthib`** | `123456` | Trần Thị B | `tranthib@ibanking.tdtu.edu.vn` | `15.000.000 VNĐ` |
| **`lethanhc`** | `123456` | Lê Thành C | `lethanhc@ibanking.tdtu.edu.vn` | `5.000.000 VNĐ` |

---

## 9. DANH SÁCH ĐỊA CHỈ TRUY CẬP HỆ THỐNG

| Dịch vụ | Địa chỉ URL | Mô tả |
| :--- | :--- | :--- |
| **Giao diện Web iBanking** | `http://localhost:3000` | Trang giao diện chính của người dùng |
| **API Gateway Swagger Docs** | `http://localhost:8000/docs` | Tài liệu API tập trung |
| **User Service Docs** | `http://localhost:8001/docs` | API tài khoản & số dư |
| **Tuition Service Docs** | `http://localhost:8002/docs` | API học phí TDTU |
| **Payment Service Docs** | `http://localhost:8003/docs` | API thanh toán & OTP |
| **Notification Service Docs** | `http://localhost:8004/docs` | API gửi email thông báo qua SMTP |
