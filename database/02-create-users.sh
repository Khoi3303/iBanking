#!/bin/bash
# ==============================================================================
# Script khởi tạo tài khoản cơ sở dữ liệu riêng biệt cho từng Microservice
# Đọc trực tiếp biến môi trường do Docker Compose cung cấp (Least Privilege)
# ==============================================================================
set -e

echo "========================================================================"
echo ">> [MySQL Init] Khởi tạo Database Service Accounts với biến môi trường..."
echo "========================================================================"

# Kiểm tra các biến môi trường bắt buộc
if [ -z "${USER_DB_PASSWORD}" ] || [ -z "${TUITION_DB_PASSWORD}" ] || [ -z "${PAYMENT_DB_PASSWORD}" ]; then
    echo "[ERROR] Thiếu biến môi trường mật khẩu database (USER_DB_PASSWORD, TUITION_DB_PASSWORD, PAYMENT_DB_PASSWORD)."
    exit 1
fi

USER_NAME="${USER_DB_USER:-ibanking_user_app}"
TUITION_NAME="${TUITION_DB_USER:-ibanking_tuition_app}"
PAYMENT_NAME="${PAYMENT_DB_USER:-ibanking_payment_app}"

# Hàm chạy câu lệnh SQL thông qua socket cục bộ trong quá trình khởi tạo container
run_sql() {
    local sql_query="$1"
    if type docker_process_sql > /dev/null 2>&1; then
        docker_process_sql <<< "$sql_query"
    else
        mysql --protocol=socket -u root -p"${MYSQL_ROOT_PASSWORD}" <<< "$sql_query"
    fi
}

run_sql "
-- 1. User & Account Service Account
CREATE USER IF NOT EXISTS '${USER_NAME}'@'%' IDENTIFIED BY '${USER_DB_PASSWORD}';
ALTER USER '${USER_NAME}'@'%' IDENTIFIED BY '${USER_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ibanking_user_db.* TO '${USER_NAME}'@'%';

-- 2. Tuition Service Account
CREATE USER IF NOT EXISTS '${TUITION_NAME}'@'%' IDENTIFIED BY '${TUITION_DB_PASSWORD}';
ALTER USER '${TUITION_NAME}'@'%' IDENTIFIED BY '${TUITION_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON tdtu_tuition_db.* TO '${TUITION_NAME}'@'%';

-- 3. Payment Service Account
CREATE USER IF NOT EXISTS '${PAYMENT_NAME}'@'%' IDENTIFIED BY '${PAYMENT_DB_PASSWORD}';
ALTER USER '${PAYMENT_NAME}'@'%' IDENTIFIED BY '${PAYMENT_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ibanking_payment_db.* TO '${PAYMENT_NAME}'@'%';

FLUSH PRIVILEGES;
"

echo ">> [MySQL Init] Hoàn tất thiết lập Service Accounts độc lập:"
echo "   - ${USER_NAME} -> ibanking_user_db"
echo "   - ${TUITION_NAME} -> tdtu_tuition_db"
echo "   - ${PAYMENT_NAME} -> ibanking_payment_db"
echo "========================================================================"
