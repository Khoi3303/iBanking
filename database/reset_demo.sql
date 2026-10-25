-- ========================================================
-- KHOI PHUC DU LIEU BAN DAU (RESET DEMO)
-- ========================================================
SET NAMES utf8mb4;

-- 1. Dat lai trang thai hoa don ve UNPAID
USE tdtu_tuition_db;
UPDATE tuition_invoices 
SET status = 'UNPAID', paid_at = NULL, paid_by_user = NULL, transaction_ref = NULL 
WHERE student_code IN (
    '524H0001', '524H0005', '524H0006', '524H0007', '524H0008', '524H0009', 
    '524H0010', '524H0011', '524H0012', '524H0013', '524H0014', '524H0015',
    '524H0016', '524H0017', '524H0018', '524H0019', '524H0020'
);

-- 2. Dat lai so du nguoi dung va dong bo so cai (Ledger Consistency)
USE ibanking_user_db;
UPDATE users SET balance = 20000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'nguyenvana@ibanking.tdtu.edu.vn' WHERE id = 1 OR username = 'nguyenvana';
UPDATE users SET balance = 15000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'tranthib@ibanking.tdtu.edu.vn' WHERE id = 2 OR username = 'tranthib';
UPDATE users SET balance = 5000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'lethanhc@ibanking.tdtu.edu.vn' WHERE id = 3 OR username = 'lethanhc';

-- Tai khoan lekhoi3303
INSERT INTO users (username, password_hash, full_name, phone_number, email, balance)
VALUES ('lekhoi3303', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Lê Khôi', '0903303303', 'lekhoi@ibanking.tdtu.edu.vn', 20000000.00)
ON DUPLICATE KEY UPDATE balance = 20000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'lekhoi@ibanking.tdtu.edu.vn';

-- Tai khoan tienmobile2006
INSERT INTO users (username, password_hash, full_name, phone_number, email, balance)
VALUES ('tienmobile2006', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Nguyễn Thanh Tiền', '0907123456', 'tienmobile@ibanking.tdtu.edu.vn', 20000000.00)
ON DUPLICATE KEY UPDATE full_name = 'Nguyễn Thanh Tiền', balance = 20000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'tienmobile@ibanking.tdtu.edu.vn';

-- Tai khoan mensieu123
INSERT INTO users (username, password_hash, full_name, phone_number, email, balance)
VALUES ('mensieu123', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Nguyễn Minh Đăng', '0908123456', 'mensieu@ibanking.tdtu.edu.vn', 20000000.00)
ON DUPLICATE KEY UPDATE full_name = 'Nguyễn Minh Đăng', balance = 20000000.00, password_hash = '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', email = 'mensieu@ibanking.tdtu.edu.vn';

-- Reset so cai bien dong so du (Account Ledger) khop chinh xac voi so du thuc te
DELETE FROM account_transactions;
INSERT INTO account_transactions (user_id, amount, transaction_type, balance_after, reference_id, description) VALUES
(1, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_001', 'Số dư khởi tạo ban đầu'),
(2, 15000000.00, 'CREDIT', 15000000.00, 'INIT_BALANCE_002', 'Số dư khởi tạo ban đầu'),
(3, 5000000.00, 'CREDIT', 5000000.00, 'INIT_BALANCE_003', 'Số dư khởi tạo ban đầu'),
(4, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_004', 'Số dư khởi tạo ban đầu'),
(5, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_005', 'Số dư khởi tạo ban đầu'),
(6, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_006', 'Số dư khởi tạo ban đầu');

-- 3. Xoa sach giao dich thanh toan cu va cap nhat cau truc
USE ibanking_payment_db;
ALTER TABLE otp_tokens MODIFY COLUMN otp_code VARCHAR(64) NOT NULL;
ALTER TABLE transactions MODIFY COLUMN status ENUM('PENDING_OTP', 'PROCESSING', 'SUCCESS', 'FAILED', 'EXPIRED', 'CANCELLED', 'COMPENSATION_PENDING') NOT NULL DEFAULT 'PENDING_OTP';
DELETE FROM otp_tokens;
DELETE FROM transactions;

-- 4. Dong bo thong tin sinh vien day du tieng Viet (khong che thong tin)
USE tdtu_tuition_db;
INSERT INTO students (student_code, full_name, class_name, major, email) VALUES
('524H0001', 'Nguyễn Văn An', '24050301', 'Kỹ thuật phần mềm', '524H0001@student.tdtu.edu.vn'),
('524H0002', 'Trần Thị Mai', '24050201', 'Khoa học máy tính', '524H0002@student.tdtu.edu.vn'),
('524H0003', 'Lê Hoàng Nam', '24050401', 'Mạng máy tính & TTTT', '524H0003@student.tdtu.edu.vn'),
('524H0004', 'Phạm Minh Đức', '24050101', 'Hệ thống thông tin', '524H0004@student.tdtu.edu.vn'),
('524H0005', 'Đỗ Gia Bảo', '24050301', 'Kỹ thuật phần mềm', '524H0005@student.tdtu.edu.vn'),
('524H0006', 'Hoàng Thị Lan', '24050201', 'Khoa học máy tính', '524H0006@student.tdtu.edu.vn'),
('524H0007', 'Vũ Đình Trọng', '24050501', 'An toàn thông tin', '524H0007@student.tdtu.edu.vn'),
('524H0008', 'Bùi Ngọc Ánh', '24050601', 'Kỹ thuật dữ liệu', '524H0008@student.tdtu.edu.vn'),
('524H0009', 'Phan Quốc Huy', '24050701', 'Trí tuệ nhân tạo', '524H0009@student.tdtu.edu.vn'),
('524H0010', 'Nguyễn Thùy Trang', '24050801', 'Thiết kế đồ họa', '524H0010@student.tdtu.edu.vn'),
('524H0011', 'Đặng Minh Khang', '24050901', 'Thương mại điện tử', '524H0011@student.tdtu.edu.vn'),
('524H0012', 'Trịnh Mỹ Duyên', '24051001', 'Quản trị kinh doanh', '524H0012@student.tdtu.edu.vn'),
('524H0013', 'Huỳnh Nhật Minh', '24050602', 'Khoa học dữ liệu', '524H0013@student.tdtu.edu.vn'),
('524H0014', 'Mai Phương Thảo', '24051101', 'Ngôn ngữ Anh', '524H0014@student.tdtu.edu.vn'),
('524H0015', 'Lương Thế Vinh', '24050401', 'Mạng máy tính', '524H0015@student.tdtu.edu.vn'),
('524H0016', 'Cao Thu Hà', '24051201', 'Tài chính ngân hàng', '524H0016@student.tdtu.edu.vn'),
('524H0017', 'Tạ Quang Khải', '24051301', 'Kỹ thuật điện tử', '524H0017@student.tdtu.edu.vn'),
('524H0018', 'Đoàn Yến Nhi', '24051401', 'Kế toán kiểm toán', '524H0018@student.tdtu.edu.vn'),
('524H0019', 'Ngô Gia Khiêm', '24051501', 'Luật kinh tế', '524H0019@student.tdtu.edu.vn'),
('524H0020', 'Chu Bảo Trâm', '24051601', 'Marketing số', '524H0020@student.tdtu.edu.vn')
ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    class_name = VALUES(class_name),
    major = VALUES(major),
    email = VALUES(email);
