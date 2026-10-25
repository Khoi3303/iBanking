-- ========================================================
-- KHỞI TẠO CƠ SỞ DỮ LIỆU CHO HỆ THỐNG iBanking MICROSERVICES
-- Môn: Kiến Trúc Hướng Dịch Vụ (SOA) - TDTU
-- ========================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

CREATE DATABASE IF NOT EXISTS ibanking_user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS tdtu_tuition_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ibanking_payment_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Ghi chú: Việc cấp quyền tài khoản Microservices (Service Accounts)
-- được thực hiện động qua script /docker-entrypoint-initdb.d/02-create-users.sh
-- nhằm bảo đảm mật khẩu luôn đồng bộ 100% với file .env (Least Privilege).
-- --------------------------------------------------------

-- --------------------------------------------------------
-- 1. DATABASE CHO USER & ACCOUNT SERVICE
-- --------------------------------------------------------
USE ibanking_user_db;

DROP TABLE IF EXISTS account_transactions;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_positive_balance CHECK (balance >= 0)
) ENGINE=InnoDB;

CREATE TABLE account_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type ENUM('DEBIT', 'CREDIT') NOT NULL,
    balance_after DECIMAL(15, 2) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_ref_type (user_id, reference_id, transaction_type),
    INDEX idx_user_tx (user_id, created_at)
) ENGINE=InnoDB;

-- Dữ liệu mẫu tài khoản người dùng thử nghiệm
INSERT INTO users (id, username, password_hash, full_name, phone_number, email, balance) VALUES
(1, 'nguyenvana', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Nguyễn Văn A', '0901234567', 'nguyenvana@ibanking.tdtu.edu.vn', 20000000.00),
(2, 'tranthib', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Trần Thị B', '0912345678', 'tranthib@ibanking.tdtu.edu.vn', 15000000.00),
(3, 'lethanhc', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Lê Thành C', '0987654321', 'lethanhc@ibanking.tdtu.edu.vn', 5000000.00),
(4, 'lekhoi3303', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Lê Khôi', '0903303303', 'lekhoi@ibanking.tdtu.edu.vn', 20000000.00),
(5, 'tienmobile2006', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Nguyễn Thanh Tiền', '0907123456', 'tienmobile@ibanking.tdtu.edu.vn', 20000000.00),
(6, 'mensieu123', '$2b$12$eRypkj2XTlMZIZjOEFGrbufe748Gt5BZyLK5LCwtLN6KzpMChZFyO', 'Nguyễn Minh Đăng', '0908123456', 'mensieu@ibanking.tdtu.edu.vn', 20000000.00);

-- Dữ liệu mẫu lịch sử số dư ban đầu
INSERT INTO account_transactions (user_id, amount, transaction_type, balance_after, reference_id, description) VALUES
(1, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_001', 'Số dư khởi tạo ban đầu'),
(2, 15000000.00, 'CREDIT', 15000000.00, 'INIT_BALANCE_002', 'Số dư khởi tạo ban đầu'),
(3, 5000000.00, 'CREDIT', 5000000.00, 'INIT_BALANCE_003', 'Số dư khởi tạo ban đầu'),
(4, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_004', 'Số dư khởi tạo ban đầu'),
(5, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_005', 'Số dư khởi tạo ban đầu'),
(6, 20000000.00, 'CREDIT', 20000000.00, 'INIT_BALANCE_006', 'Số dư khởi tạo ban đầu');


-- --------------------------------------------------------
-- 2. DATABASE CHO TDTU TUITION SERVICE
-- --------------------------------------------------------
USE tdtu_tuition_db;

DROP TABLE IF EXISTS tuition_invoices;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    student_code VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    class_name VARCHAR(50) NOT NULL,
    major VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE tuition_invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_code VARCHAR(20) NOT NULL,
    semester VARCHAR(50) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    status ENUM('UNPAID', 'PAID') NOT NULL DEFAULT 'UNPAID',
    paid_at DATETIME NULL,
    paid_by_user VARCHAR(50) NULL,
    transaction_ref VARCHAR(100) NULL,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_code) REFERENCES students(student_code) ON DELETE CASCADE,
    UNIQUE KEY uq_student_semester (student_code, semester)
) ENGINE=InnoDB;

-- Dữ liệu mẫu sinh viên và khoản học phí TDTU (Phục vụ đầy đủ kịch bản demo chấm điểm)
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
('524H0020', 'Chu Bảo Trâm', '24051601', 'Marketing số', '524H0020@student.tdtu.edu.vn');

-- Du lieu hoa don hoc phi
INSERT INTO tuition_invoices (id, student_code, semester, amount, status, paid_at, paid_by_user, transaction_ref) VALUES
-- Sinh vien 524H0001: chua thanh toan
(1, '524H0001', 'HK1/2026-2027', 15000000.00, 'UNPAID', NULL, NULL, NULL),

-- Sinh vien 524H0002: da thanh toan
(2, '524H0002', 'HK1/2026-2027', 12000000.00, 'PAID', '2026-10-01 09:30:00', 'nguyenvana', 'INIT_TX_PAID_002'),

-- Sinh vien 524H0003: hoc phi vuot han muc so du
(3, '524H0003', 'HK1/2026-2027', 50000000.00, 'UNPAID', NULL, NULL, NULL),

-- Danh sach hoa don sinh vien bo sung
(4, '524H0005', 'HK1/2026-2027', 14000000.00, 'UNPAID', NULL, NULL, NULL),
(5, '524H0006', 'HK1/2026-2027', 11500000.00, 'UNPAID', NULL, NULL, NULL),
(6, '524H0007', 'HK1/2026-2027', 16000000.00, 'UNPAID', NULL, NULL, NULL),
(7, '524H0008', 'HK1/2026-2027', 13200000.00, 'UNPAID', NULL, NULL, NULL),
(8, '524H0009', 'HK1/2026-2027', 15500000.00, 'UNPAID', NULL, NULL, NULL),
(9, '524H0010', 'HK1/2026-2027', 9800000.00, 'UNPAID', NULL, NULL, NULL),
(10, '524H0011', 'HK1/2026-2027', 8500000.00, 'UNPAID', NULL, NULL, NULL),
(11, '524H0012', 'HK1/2026-2027', 12500000.00, 'UNPAID', NULL, NULL, NULL),
(12, '524H0013', 'HK1/2026-2027', 7500000.00, 'UNPAID', NULL, NULL, NULL),
(13, '524H0014', 'HK1/2026-2027', 10200000.00, 'UNPAID', NULL, NULL, NULL),
(14, '524H0015', 'HK1/2026-2027', 6800000.00, 'UNPAID', NULL, NULL, NULL),
(15, '524H0016', 'HK1/2026-2027', 13000000.00, 'UNPAID', NULL, NULL, NULL),
(16, '524H0017', 'HK1/2026-2027', 5500000.00, 'UNPAID', NULL, NULL, NULL),
(17, '524H0018', 'HK1/2026-2027', 11000000.00, 'UNPAID', NULL, NULL, NULL),
(18, '524H0019', 'HK1/2026-2027', 8900000.00, 'UNPAID', NULL, NULL, NULL),
(19, '524H0020', 'HK1/2026-2027', 14500000.00, 'UNPAID', NULL, NULL, NULL);

-- --------------------------------------------------------
-- 3. DATABASE CHO PAYMENT & TRANSACTION SERVICE
-- --------------------------------------------------------
USE ibanking_payment_db;

DROP TABLE IF EXISTS otp_tokens;
DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    id VARCHAR(36) PRIMARY KEY, -- UUID
    user_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    student_code VARCHAR(20) NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    invoice_id INT NULL,
    semester VARCHAR(50) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    idempotency_key VARCHAR(64) NULL,
    status ENUM('PENDING_OTP', 'PROCESSING', 'SUCCESS', 'FAILED', 'EXPIRED', 'CANCELLED', 'COMPENSATION_PENDING') NOT NULL DEFAULT 'PENDING_OTP',
    failure_reason VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_student_code (student_code),
    INDEX idx_status (status),
    UNIQUE KEY uq_user_idempotency (user_id, idempotency_key)
) ENGINE=InnoDB;

CREATE TABLE otp_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(36) NOT NULL UNIQUE,
    otp_code VARCHAR(64) NOT NULL, -- SHA-256 Hash bảo mật của mã OTP (OWASP Standard)
    expires_at DATETIME NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    INDEX idx_otp_lookup (transaction_id, otp_code, is_used)
) ENGINE=InnoDB;
