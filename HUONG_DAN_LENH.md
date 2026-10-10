# BẢNG TỔNG HỢP CÂU LỆNH THƯỜNG DÙNG - iBanking TDTU (SOA)

Tài liệu này tổng hợp đầy đủ các câu lệnh thông dụng nhất trong quá trình phát triển, kiểm thử, sửa lỗi và demo đồ án **iBanking Microservices**.

---

## ⚡ 1. CÁC FILE SCRIPT CHẠY NHANH BẰNG 1-CLICK (Khuyên dùng)

Trong thư mục gốc của dự án đã tạo sẵn 3 file script tiện lợi, bạn chỉ cần **nhấp đúp chuột** để chạy:

| File Script | Mục đích sử dụng | Khi nào dùng? |
| :--- | :--- | :--- |
| **`start.bat`** | Khởi động toàn bộ hệ thống từ đầu (Build + MySQL + Redis + Mailpit + 5 Services). | Khi mới mở máy tính, hoặc muốn reset toàn bộ hệ thống về mới tinh. |
| **`rebuild.bat`** | Rebuild và cập nhật nhanh các service đã sửa code (**giữ nguyên dữ liệu DB**). | Sau khi bạn vừa sửa code Frontend, Gateway, hoặc User Service. |
| **`reset_demo.bat`** | **Đặt lại trạng thái demo:** Sinh viên `524H0001` về `UNPAID` và tài khoản `nguyenvana` về `20.000.000đ`. | **Dùng ngay sau khi vừa thanh toán xong**, muốn test thanh toán lại nhiều lần. |

---

## 🔄 2. CÂU LỆNH RESET DỮ LIỆU & TRẠNG THÁI THANH TOÁN

### Cách 1: Reset nhanh hóa đơn 524H0001 và số dư tài khoản 1 (Khuyên dùng)
Chạy lệnh này trong Terminal PowerShell hoặc Command Prompt:
```powershell
type database\reset_demo.sql | docker compose exec -T mysql mysql -u root -prootpassword
```
*(Lệnh này đặt lại hóa đơn `524H0001` thành `UNPAID`, xóa lịch sử giao dịch của MSSV này trong `payment_db`, và trả số dư `nguyenvana` về 20.000.000 VNĐ).*

---

### Cách 2: Reset toàn bộ Database về trạng thái gốc ban đầu của đồ án
Nếu muốn xóa sạch các tài khoản tự đăng ký mới và đưa toàn bộ database về lúc mới nộp bài:
```powershell
docker compose down -v
docker compose up -d
```
*(Tham số `-v` sẽ xóa sạch các volume dữ liệu cũ và nạp lại toàn bộ file `database/init.sql`).*

---

## 🛠️ 3. CÂU LỆNH KHI CHỈNH SỬA CODE (REBUILD TỪNG SERVICE)

Khi bạn chỉnh sửa code của một service cụ thể, bạn **không cần restart toàn bộ hệ thống**. Chỉ cần rebuild đúng service đó (thời gian build chỉ mất 2-3 giây):

### ① Khi sửa giao diện Frontend (HTML / CSS / JS):
```powershell
docker compose up -d --build frontend
```
*(Sau đó mở trình duyệt bấm **Ctrl + F5** để xem thay đổi ngay lập tức).*

### ② Khi sửa User & Account Service:
```powershell
docker compose up -d --build user-service
```

### ③ Khi sửa API Gateway:
```powershell
docker compose up -d --build api-gateway
```

### ④ Khi sửa Payment & Saga Service:
```powershell
docker compose up -d --build payment-service
```

### ⑤ Khi sửa Tuition Service (Dữ liệu học phí TDTU):
```powershell
docker compose up -d --build tuition-service
```

### ⑥ Khi sửa Notification Service (Cấu hình gửi Email Gmail / Mailpit):
```powershell
docker compose up -d --build notification-service
```

### ⑦ Rebuild cùng lúc nhiều service đã sửa:
```powershell
docker compose up -d --build user-service api-gateway frontend
```

---

## 📋 4. CÂU LỆNH XEM LOGS & DEBUG THEO THỜI GIAN THỰC

Xem log là cách nhanh nhất để kiểm tra xem hệ thống có gửi mail chưa, có bị lỗi gì không:

* **Xem log gửi Email (xem Gmail gửi OTP & Biên lai):**
  ```powershell
  docker compose logs -f notification-service
  ```
* **Xem log điều phối giao dịch Saga & OTP:**
  ```powershell
  docker compose logs -f payment-service
  ```
* **Xem log trừ tiền & khóa dữ liệu Pessimistic Lock (User Service):**
  ```powershell
  docker compose logs -f user-service
  ```
* **Xem log của tất cả các container cùng lúc:**
  ```powershell
  docker compose logs -f
  ```
*(Nhấn `Ctrl + C` để thoát khỏi màn hình xem log).*

---

## 🚦 5. CÂU LỆNH QUẢN LÝ DOCKER CONTAINER

* **Kiểm tra trạng thái các container đang chạy:**
  ```powershell
  docker compose ps
  ```
* **Khởi động các container (chạy nền):**
  ```powershell
  docker compose up -d
  ```
* **Tạm dừng hệ thống (vẫn giữ dữ liệu trong DB):**
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

## 🧪 6. CÂU LỆNH CHẠY KIỂM THỬ TỰ ĐỘNG (CONCURRENCY & SAGA)

Đây là kịch bản kiểm thử tự động để lấy trọn vẹn điểm phần Concurrency (1.5đ) và Saga Transaction (1.5đ) theo Rubric của thầy:

1. Kích hoạt chạy test:
   ```powershell
   python scripts\test_concurrency.py
   ```
   *(Hoặc nhấp đúp vào `scripts\run_tests.bat`).*

2. Kết quả kiểm thử sẽ in ra trực tiếp:
   - ✓ `Scenario 1: Double-Spending Test` (Khóa `SELECT ... FOR UPDATE` chống âm tiền).
   - ✓ `Scenario 2: Race Condition Test` (Hai người cùng thanh toán 1 hóa đơn).
   - ✓ `Scenario 3: E2E Payment Flow & Saga Compensation`.

---

## 🐙 7. CÂU LỆNH GIT LÀM VIỆC NHÓM & ĐẨY LÊN GITHUB

Khi bạn hoặc bạn bè trong nhóm muốn đồng bộ code:

* **Xem các file đã thay đổi:**
  ```powershell
  git status
  ```
* **Lưu và đẩy code lên GitHub:**
  ```powershell
  git add .
  git commit -m "Cap nhat chuc nang nap tien va mac dinh so du 0d"
  git push origin main
  ```
* **Bạn trong nhóm kéo code mới về máy:**
  ```powershell
  git pull origin main
  ```
  *(Sau khi pull về, chỉ cần chạy file `start.bat` là hệ thống của bạn bè tự động chạy hoàn chỉnh).*

---

## 🌐 8. DANH SÁCH ĐỊA CHỈ TRUY CẬP HỆ THỐNG

| Dịch vụ | Địa chỉ URL | Mô tả |
| :--- | :--- | :--- |
| **Giao diện Web iBanking** | `http://localhost:3000` | Trang giao diện chính của người dùng |
| **Hộp thư xem OTP (Mailpit)** | `http://localhost:8025` | Xem mã OTP gửi giả lập cục bộ |
| **API Gateway Swagger Docs** | `http://localhost:8000/docs` | Tài liệu API tập trung |
| **User Service Docs** | `http://localhost:8001/docs` | API tài khoản & số dư |
| **Tuition Service Docs** | `http://localhost:8002/docs` | API học phí TDTU |
| **Payment Service Docs** | `http://localhost:8003/docs` | API thanh toán & OTP |
| **Notification Service Docs** | `http://localhost:8004/docs` | API gửi email thông báo |
