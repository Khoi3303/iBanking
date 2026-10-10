-- ========================================================
-- KHÔI PHỤC DỮ LIỆU DEMO CHO TÀI KHOẢN VÀ HỌC PHÍ TDTU
-- ========================================================
SET NAMES utf8mb4;

-- 1. Reset hóa đơn sinh viên 524H0001 về trạng thái chưa đóng tiền (UNPAID)
USE tdtu_tuition_db;
UPDATE tuition_invoices 
SET status = 'UNPAID', paid_at = NULL, paid_by_user = NULL, transaction_ref = NULL 
WHERE student_code = '524H0001';

-- 2. Reset số dư các tài khoản demo chuẩn về mức ban đầu
USE ibanking_user_db;
UPDATE users SET balance = 20000000.00 WHERE id = 1; -- nguyenvana: 20 triệu
UPDATE users SET balance = 15000000.00 WHERE id = 2; -- tranthib: 15 triệu
UPDATE users SET balance = 5000000.00 WHERE id = 3;  -- lethanhc: 5 triệu

-- 3. Xóa các giao dịch demo cũ của sinh viên 524H0001 trong payment_db để làm sạch lịch sử
USE ibanking_payment_db;
DELETE FROM otp_tokens WHERE transaction_id IN (SELECT id FROM transactions WHERE student_code = '524H0001');
DELETE FROM transactions WHERE student_code = '524H0001';
