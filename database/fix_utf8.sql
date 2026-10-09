SET NAMES utf8mb4;

USE ibanking_user_db;
UPDATE users SET full_name = 'Nguyễn Văn A' WHERE id = 1;
UPDATE users SET full_name = 'Trần Thị B' WHERE id = 2;
UPDATE users SET full_name = 'Lê Thành C' WHERE id = 3;

USE tdtu_tuition_db;
UPDATE students SET full_name = 'Nguyễn Văn An', major = 'Kỹ thuật phần mềm' WHERE student_code = '524H0001';
UPDATE students SET full_name = 'Trần Thị Mai', major = 'Khoa học máy tính' WHERE student_code = '524H0002';
UPDATE students SET full_name = 'Lê Hoàng Nam', major = 'Mạng máy tính & TTTT' WHERE student_code = '524H0003';
UPDATE students SET full_name = 'Phạm Minh Đức', major = 'Hệ thống thông tin' WHERE student_code = '524H0004';
