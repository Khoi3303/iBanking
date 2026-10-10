/**
 * iBanking Frontend Application Logic
 * Môn: Kiến Trúc Hướng Dịch Vụ (CS504070 - SOA, TDTU)
 */

// Tự động nhận diện API endpoint linh hoạt:
// - Khi chạy qua Docker Nginx container: gọi relative "/api" (Nginx reverse proxy sang api-gateway:8000)
// - Khi chạy mở file tĩnh local: fallback sang "http://localhost:8000/api"
const API_BASE_URL = (window.location.protocol.startsWith("http") && window.location.port !== "8000")
    ? "/api"
    : "http://localhost:8000/api";

// State quản trị ứng dụng
const state = {
    token: localStorage.getItem("ibanking_token") || null,
    currentUser: null,
    currentTuition: null,
    currentTransactionId: null,
    otpTimerInterval: null,
    otpSecondsRemaining: 300,
    isSubmittingOtp: false // Flag chống double click
};

// ========================================================
// HÀM TIỆN ÍCH
// ========================================================
function formatVND(amount) {
    if (isNaN(amount) || amount === null || amount === undefined) return "0 VND";
    return Number(amount).toLocaleString('vi-VN') + " VND";
}

function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}

function getAuthHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
    };
}

// ========================================================
// KHỞI ĐỘNG ỨNG DỤNG
// ========================================================
document.addEventListener("DOMContentLoaded", () => {
    initEventListeners();
    checkExistingSession();
});

function initEventListeners() {
    // Form Login
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLoginSubmit);
    }

    // Form Register
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegisterSubmit);
    }

    // Nút đăng xuất
    const btnLogout = document.getElementById("btnLogout");
    if (btnLogout) {
        btnLogout.addEventListener("click", logout);
    }

    // Checkbox Điều khoản
    const termsCheckbox = document.getElementById("agreeTermsCheckbox");
    if (termsCheckbox) {
        termsCheckbox.addEventListener("change", validatePaymentConditions);
    }

    // Phím Enter ở ô tra cứu MSSV
    const studentInput = document.getElementById("studentCodeInput");
    if (studentInput) {
        studentInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                searchStudentTuition();
            }
        });
    }

    // Phím Enter ở ô nhập OTP
    const otpInput = document.getElementById("otpCodeInput");
    if (otpInput) {
        otpInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                submitOtpConfirm();
            }
        });
    }
}

async function checkExistingSession() {
    if (state.token) {
        try {
            await loadUserProfile();
            showMainScreen();
        } catch (e) {
            logout();
        }
    } else {
        showLoginScreen();
    }
}

function showLoginScreen() {
    document.getElementById("loginScreen").classList.remove("hidden");
    document.getElementById("mainScreen").classList.add("hidden");
}

function showMainScreen() {
    document.getElementById("loginScreen").classList.add("hidden");
    document.getElementById("mainScreen").classList.remove("hidden");
    switchTab('tuition');
}

// ========================================================
// 1. NGHIỆP VỤ XÁC THỰC (AUTHENTICATION)
// ========================================================
async function handleLoginSubmit(e) {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;
    const btnLogin = document.getElementById("btnLogin");

    btnLogin.disabled = true;
    btnLogin.querySelector(".spinner").classList.remove("hidden");

    try {
        const resp = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.detail || "Đăng nhập không thành công.");
        }

        state.token = data.access_token;
        state.currentUser = data.user;
        localStorage.setItem("ibanking_token", state.token);

        renderUserInfo(state.currentUser);
        showMainScreen();
        showToast(`Đăng nhập thành công! Xin chào ${data.user.full_name}`, "success");

        // Tự động tìm kiếm MSSV mẫu đầu tiên
        searchStudentTuition();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btnLogin.disabled = false;
        btnLogin.querySelector(".spinner").classList.add("hidden");
    }
}

function switchAuthTab(tab) {
    const tabLogin = document.getElementById("tabLogin");
    const tabRegister = document.getElementById("tabRegister");
    const loginSection = document.getElementById("loginSection");
    const registerSection = document.getElementById("registerSection");

    if (tab === "register") {
        tabLogin.classList.remove("active");
        tabRegister.classList.add("active");
        loginSection.classList.add("hidden");
        registerSection.classList.remove("hidden");
    } else {
        tabRegister.classList.remove("active");
        tabLogin.classList.add("active");
        registerSection.classList.add("hidden");
        loginSection.classList.remove("hidden");
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const full_name = document.getElementById("regFullName").value.trim();
    const email = document.getElementById("regEmail").value.trim();
    const username = document.getElementById("regUsername").value.trim();
    const phone_number = document.getElementById("regPhone").value.trim();
    const password = document.getElementById("regPassword").value;
    const balance = 0; // Mặc định 0 VNĐ khi đăng ký mới

    const btnRegister = document.getElementById("btnRegister");
    btnRegister.disabled = true;
    btnRegister.querySelector(".spinner").classList.remove("hidden");

    try {
        const resp = await fetch(`${API_BASE_URL}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username,
                password,
                full_name,
                phone_number,
                email,
                balance
            })
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.detail || "Đăng ký không thành công.");
        }

        state.token = data.access_token;
        state.currentUser = data.user;
        localStorage.setItem("ibanking_token", state.token);

        renderUserInfo(state.currentUser);
        showMainScreen();
        showToast(`Đăng ký thành công! Chào mừng ${data.user.full_name}`, "success");

        // Tự động tìm kiếm MSSV mẫu đầu tiên
        searchStudentTuition();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btnRegister.disabled = false;
        btnRegister.querySelector(".spinner").classList.add("hidden");
    }
}

function logout() {
    state.token = null;
    state.currentUser = null;
    state.currentTuition = null;
    state.currentTransactionId = null;
    clearInterval(state.otpTimerInterval);
    localStorage.removeItem("ibanking_token");
    showLoginScreen();
    showToast("Đã đăng xuất khỏi iBanking.", "info");
}

async function loadUserProfile() {
    const resp = await fetch(`${API_BASE_URL}/users/me`, {
        headers: getAuthHeaders()
    });

    if (!resp.ok) {
        throw new Error("Không thể tải thông tin người dùng.");
    }

    const user = await resp.json();
    state.currentUser = user;
    renderUserInfo(user);
    return user;
}

function renderUserInfo(user) {
    if (!user) return;
    // Navbar Header
    document.getElementById("navUserName").textContent = user.full_name;
    document.getElementById("navUserBalance").textContent = `Số dư: ${formatVND(user.balance)}`;
    document.getElementById("userAvatar").textContent = user.full_name.charAt(0);

    // Form Thông tin người nộp tiền (Read-only)
    document.getElementById("payerName").value = user.full_name;
    document.getElementById("payerPhone").value = user.phone_number;
    document.getElementById("payerEmail").value = user.email;

    // Box số dư cột C
    document.getElementById("boxUserBalance").textContent = formatVND(user.balance);

    // Cập nhật lại số dư còn lại nếu đang có khoản nợ
    validatePaymentConditions();
}

function quickFillUser(username, note) {
    document.getElementById("loginUsername").value = username;
    document.getElementById("loginPassword").value = "123456";
    showToast(`Đã chọn tài khoản: ${username} (${note})`, "info");
}

// ========================================================
// 2. TRA CỨU HỌC PHÍ (TUITION INQUIRY)
// ========================================================
async function searchStudentTuition() {
    const mssv = document.getElementById("studentCodeInput").value.trim();
    if (!mssv) {
        showToast("Vui lòng nhập MSSV cần tra cứu.", "error");
        return;
    }

    const btnSearch = document.getElementById("btnSearchStudent");
    btnSearch.disabled = true;
    btnSearch.textContent = "Đang tra cứu...";

    try {
        const resp = await fetch(`${API_BASE_URL}/tuition/students/${encodeURIComponent(mssv)}`, {
            headers: getAuthHeaders()
        });

        const data = await resp.json();

        if (!resp.ok) {
            document.getElementById("tuitionResultArea").classList.add("hidden");
            state.currentTuition = null;
            validatePaymentConditions();
            throw new Error(data.detail || "Không tìm thấy thông tin sinh viên.");
        }

        state.currentTuition = data;
        renderTuitionResult(data);
        validatePaymentConditions();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btnSearch.disabled = false;
        btnSearch.textContent = "Tra cứu học phí";
    }
}

function renderTuitionResult(tuition) {
    const resultArea = document.getElementById("tuitionResultArea");
    resultArea.classList.remove("hidden");

    document.getElementById("resStudentCode").textContent = tuition.student_code;
    document.getElementById("resStudentName").textContent = tuition.student_name;
    document.getElementById("resStudentClass").textContent = `${tuition.major} (${tuition.class_name})`;
    document.getElementById("resSemester").textContent = tuition.semester || "N/A";
    document.getElementById("resAmount").textContent = formatVND(tuition.amount);

    // Cập nhật Banner trạng thái
    const banner = document.getElementById("tuitionStatusBanner");
    if (tuition.status === "UNPAID") {
        banner.className = "status-banner unpaid";
        banner.textContent = `⚠️ Khoản nợ còn phải thanh toán cho học kỳ ${tuition.semester}.`;
    } else if (tuition.status === "PAID") {
        banner.className = "status-banner paid";
        banner.textContent = `✓ ${tuition.message}`;
    } else {
        banner.className = "status-banner nodebt";
        banner.textContent = `ℹ️ ${tuition.message}`;
    }

    // Box số tiền cột C
    document.getElementById("boxTuitionAmount").textContent = formatVND(tuition.amount);
}

function quickFillStudent(mssv) {
    document.getElementById("studentCodeInput").value = mssv;
    searchStudentTuition();
}

// ========================================================
// 3. KIỂM TRA ĐIỀU KIỆN THANH TOÁN (Mục 2.c đề bài)
// ========================================================
function validatePaymentConditions() {
    const btnConfirm = document.getElementById("btnConfirmInitiate");
    const alertInsufficient = document.getElementById("insufficientBalanceAlert");
    const termsCheckbox = document.getElementById("agreeTermsCheckbox");
    const boxRemaining = document.getElementById("boxRemainingBalance");

    if (!state.currentUser || !state.currentTuition) {
        btnConfirm.disabled = true;
        btnConfirm.classList.remove("btn-ready");
        alertInsufficient.classList.add("hidden");
        boxRemaining.textContent = "0 VND";
        return;
    }

    const userBalance = Number(state.currentUser.balance);
    const tuitionAmount = Number(state.currentTuition.amount);
    const remainingBalance = userBalance - tuitionAmount;

    // Tính toán số dư còn lại và style màu sắc
    if (state.currentTuition.status === "UNPAID") {
        boxRemaining.textContent = formatVND(remainingBalance);
        boxRemaining.className = remainingBalance >= 0 ? "val text-success font-bold" : "val text-danger font-bold";
    } else {
        boxRemaining.textContent = formatVND(userBalance);
        boxRemaining.className = "val text-success font-bold";
    }

    // RÀNG BUỘC THEO ĐỀ BÀI (Mục 2c):
    // 1. Khoản học phí tồn tại và chưa được thanh toán (status == UNPAID & can_pay == true)
    // 2. Số dư khả dụng của người nộp >= số tiền cần thanh toán
    // 3. Đã đồng ý điều khoản
    const isUnpaid = state.currentTuition.status === "UNPAID" && (state.currentTuition.can_pay !== false);
    const isBalanceEnough = userBalance >= tuitionAmount;

    if (isUnpaid && !isBalanceEnough) {
        alertInsufficient.classList.remove("hidden");
    } else {
        alertInsufficient.classList.add("hidden");
    }

    // Nếu đã đủ số dư để đóng học phí còn nợ, tự động tích chọn điều khoản nếu chưa tích
    if (isUnpaid && isBalanceEnough && termsCheckbox && !termsCheckbox.checked) {
        termsCheckbox.checked = true;
    }

    const termsAgreed = termsCheckbox ? termsCheckbox.checked : false;

    if (isUnpaid && isBalanceEnough && termsAgreed) {
        btnConfirm.disabled = false;
        btnConfirm.textContent = "Xác nhận giao dịch";
        btnConfirm.classList.add("btn-ready");
    } else {
        btnConfirm.disabled = true;
        btnConfirm.classList.remove("btn-ready");
    }
}

// ========================================================
// 4. KHỞI TẠO THANH TOÁN & GỬI OTP (INITIATE PAYMENT)
// ========================================================
async function initiatePayment() {
    if (!state.currentTuition) return;

    const btnConfirm = document.getElementById("btnConfirmInitiate");
    btnConfirm.disabled = true;
    btnConfirm.textContent = "Đang khởi tạo giao dịch...";

    try {
        const payload = {
            student_code: state.currentTuition.student_code,
            amount: state.currentTuition.amount,
            invoice_id: state.currentTuition.invoice_id
        };

        const resp = await fetch(`${API_BASE_URL}/payments/initiate`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.detail || "Không thể khởi tạo giao dịch.");
        }

        state.currentTransactionId = data.transaction_id;

        // Mở Modal OTP và khởi động đồng hồ đếm ngược 5 phút
        openOtpModal(data.user_email, data.expires_in_seconds || 300);
        showToast("Mã OTP đã được gửi đến email của bạn!", "success");
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btnConfirm.textContent = "Xác nhận giao dịch";
        validatePaymentConditions();
    }
}

function openOtpModal(emailMasked, seconds) {
    document.getElementById("otpEmailMasked").textContent = emailMasked;
    document.getElementById("otpCodeInput").value = "";
    document.getElementById("otpErrorAlert").classList.add("hidden");
    document.getElementById("otpModal").classList.remove("hidden");
    document.getElementById("otpCodeInput").focus();

    startOtpCountdown(seconds);
}

function startOtpCountdown(seconds) {
    clearInterval(state.otpTimerInterval);
    state.otpSecondsRemaining = seconds;

    updateTimerDisplay();

    state.otpTimerInterval = setInterval(() => {
        state.otpSecondsRemaining--;
        if (state.otpSecondsRemaining <= 0) {
            clearInterval(state.otpTimerInterval);
            document.getElementById("otpTimer").textContent = "00:00 (Hết hạn)";
            showOtpError("Mã OTP đã hết hiệu lực (quá 5 phút). Vui lòng tạo lại giao dịch mới.");
            document.getElementById("btnSubmitOtp").disabled = true;
        } else {
            updateTimerDisplay();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const mins = Math.floor(state.otpSecondsRemaining / 60);
    const secs = state.otpSecondsRemaining % 60;
    const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    document.getElementById("otpTimer").textContent = formatted;
}

// XỬ LÝ HỦY GIAO DỊCH TẠI MODAL OTP
async function cancelOtpModal() {
    // 1. Dừng đồng hồ đếm ngược ngầm ngay lập tức (tránh chạy ngầm tự động khóa modal lần sau)
    if (state.otpTimerInterval) {
        clearInterval(state.otpTimerInterval);
        state.otpTimerInterval = null;
    }

    const txIdToCancel = state.currentTransactionId;

    // 2. Ẩn modal và xóa vết transaction_id
    document.getElementById("otpModal").classList.add("hidden");
    document.getElementById("otpCodeInput").value = "";
    document.getElementById("otpErrorAlert").classList.add("hidden");
    state.currentTransactionId = null;
    state.isSubmittingOtp = false;

    // 3. Thông báo cho người dùng
    showToast("Đã hủy phiên giao dịch.", "info");

    // 4. Báo cho Backend hủy phiên và vô hiệu hóa mã OTP trong Redis ngay lập tức
    if (txIdToCancel) {
        try {
            await fetch(`${API_BASE_URL}/payments/cancel`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ transaction_id: txIdToCancel })
            });
        } catch (err) {
            console.warn("Lỗi khi hủy phiên OTP phía server:", err);
        }
    }
}

function showOtpError(message) {
    const errorBox = document.getElementById("otpErrorAlert");
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

// ========================================================
// 5. XÁC NHẬN OTP & HOÀN TẤT THANH TOÁN (CHỐNG DOUBLE-CLICK)
// ========================================================
async function submitOtpConfirm() {
    // Ngăn chặn bấm liên tiếp nhiều lần (Debounce / Double-click guard)
    if (state.isSubmittingOtp) return;

    const otpCode = document.getElementById("otpCodeInput").value.trim();
    if (!otpCode || otpCode.length !== 6) {
        showOtpError("Vui lòng nhập đúng mã OTP gồm 6 chữ số.");
        return;
    }

    const btnSubmit = document.getElementById("btnSubmitOtp");
    const btnText = btnSubmit.querySelector(".btn-text");
    const spinner = btnSubmit.querySelector(".spinner");

    // Lập tức khóa nút và đổi nhãn thông báo đang xử lý
    state.isSubmittingOtp = true;
    btnSubmit.disabled = true;
    btnText.textContent = "Đang xử lý giao dịch...";
    spinner.classList.remove("hidden");
    document.getElementById("otpErrorAlert").classList.add("hidden");

    try {
        const resp = await fetch(`${API_BASE_URL}/payments/confirm`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
                transaction_id: state.currentTransactionId,
                otp_code: otpCode
            })
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.detail || "Xác thực thanh toán thất bại.");
        }

        // THÀNH CÔNG RỰC RỠ:
        // 1. Dừng đếm ngược và đóng modal OTP
        clearInterval(state.otpTimerInterval);
        state.otpTimerInterval = null;
        document.getElementById("otpModal").classList.add("hidden");

        // 2. TỰ ĐỘNG ĐỒNG BỘ: Cập nhật lại số dư trên Header và nạp lại lịch sử Tab 2
        await loadUserProfile();
        loadTransactionHistory(); // chạy ngầm nạp sẵn dữ liệu mới

        // 3. Mở biên lai thành công
        openReceiptModal(data);

        // 4. Cập nhật lại trạng thái học phí (lúc này đã PAID)
        await searchStudentTuition();
        showToast("Thanh toán học phí thành công!", "success");
    } catch (err) {
        showOtpError(err.message);
        showToast(err.message, "error");
    } finally {
        state.isSubmittingOtp = false;
        btnSubmit.disabled = false;
        btnText.textContent = "Xác nhận thanh toán";
        spinner.classList.add("hidden");
    }
}

function openReceiptModal(data) {
    const detailsContainer = document.getElementById("receiptDetailsBody");
    detailsContainer.innerHTML = `
        <div class="info-item"><span class="info-label">Mã giao dịch (TxID):</span><span class="info-val" style="font-family: monospace;">${data.transaction_id}</span></div>
        <div class="info-item"><span class="info-label">Mã số sinh viên:</span><span class="info-val">${data.student_code}</span></div>
        <div class="info-item"><span class="info-label">Họ tên sinh viên:</span><span class="info-val font-bold">${data.student_name}</span></div>
        <div class="info-item"><span class="info-label">Học kỳ:</span><span class="info-val">${data.semester}</span></div>
        <div class="info-item highlight"><span class="info-label">Số tiền đã gạch nợ:</span><span class="info-val text-success font-bold text-lg">${formatVND(data.amount)}</span></div>
        <div class="info-item"><span class="info-label">Thời gian hoàn tất:</span><span class="info-val">${new Date(data.completed_at).toLocaleString('vi-VN')}</span></div>
    `;

    document.getElementById("receiptModal").classList.remove("hidden");
}

function closeReceiptModal() {
    document.getElementById("receiptModal").classList.add("hidden");
}

// ========================================================
// 6. LỊCH SỬ GIAO DỊCH (TRANSACTION HISTORY)
// ========================================================
async function loadTransactionHistory() {
    const tbody = document.getElementById("historyTableBody");
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Đang tải lịch sử giao dịch...</td></tr>`;

    try {
        const resp = await fetch(`${API_BASE_URL}/payments/history`, {
            headers: getAuthHeaders()
        });

        if (!resp.ok) {
            throw new Error("Không thể tải lịch sử giao dịch.");
        }

        const list = await resp.json();

        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">Chưa có giao dịch thanh toán nào được thực hiện.</td></tr>`;
            return;
        }

        tbody.innerHTML = list.map(tx => {
            let statusBadge = "";
            if (tx.status === "SUCCESS") {
                statusBadge = `<span class="status-badge success">Thành công</span>`;
            } else if (tx.status === "PENDING_OTP") {
                statusBadge = `<span class="status-badge pending">Chờ OTP</span>`;
            } else if (tx.status === "FAILED") {
                statusBadge = `<span class="status-badge failed" title="${tx.failure_reason || ''}">Thất bại</span>`;
            } else {
                statusBadge = `<span class="status-badge cancelled">${tx.status}</span>`;
            }

            return `
                <tr>
                    <td>${new Date(tx.created_at).toLocaleString('vi-VN')}</td>
                    <td style="font-family: monospace; font-size: 0.8rem;">${tx.id.substring(0, 13)}...</td>
                    <td><strong>${tx.student_code}</strong></td>
                    <td>${tx.student_name}</td>
                    <td>${tx.semester}</td>
                    <td class="font-bold text-primary">${formatVND(tx.amount)}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">${err.message}</td></tr>`;
    }
}

// TABS SWITCHING
function switchTab(tabName) {
    const tuitionTab = document.getElementById("tuitionTab");
    const historyTab = document.getElementById("historyTab");
    const tuitionBtn = document.getElementById("tabTuitionBtn");
    const historyBtn = document.getElementById("tabHistoryBtn");

    if (tabName === "tuition") {
        tuitionTab.classList.remove("hidden");
        historyTab.classList.add("hidden");
        tuitionBtn.classList.add("active");
        historyBtn.classList.remove("active");
    } else {
        tuitionTab.classList.add("hidden");
        historyTab.classList.remove("hidden");
        tuitionBtn.classList.remove("active");
        historyBtn.classList.add("active");
        loadTransactionHistory();
    }
}

function showTermsModal(e) {
    if (e) e.preventDefault();
    document.getElementById("termsModal").classList.remove("hidden");
}

function closeTermsModal() {
    document.getElementById("termsModal").classList.add("hidden");
}

// ========================================================
// 5. NẠP TIỀN VÀO TÀI KHOẢN (DEPOSIT)
// ========================================================
function openDepositModal() {
    if (!state.currentUser) return;
    document.getElementById("depositCurrentBalance").textContent = formatVND(state.currentUser.balance);

    // Tính toán số tiền gợi ý: Nếu đang xem học phí chưa đủ tiền, tự động điền phần còn thiếu
    let suggestedAmount = 15000000;
    if (state.currentTuition && state.currentTuition.status === "UNPAID") {
        const needed = Number(state.currentTuition.amount) - Number(state.currentUser.balance);
        if (needed > 0) {
            suggestedAmount = needed;
        }
    }
    document.getElementById("depositAmountInput").value = suggestedAmount;
    document.getElementById("depositErrorAlert").classList.add("hidden");
    document.getElementById("depositModal").classList.remove("hidden");
    setTimeout(() => {
        const inp = document.getElementById("depositAmountInput");
        if (inp) {
            inp.focus();
            inp.select();
        }
    }, 100);
}

function closeDepositModal() {
    document.getElementById("depositModal").classList.add("hidden");
}

function setDepositAmount(amount) {
    document.getElementById("depositAmountInput").value = amount;
}

async function handleDepositSubmit(e) {
    e.preventDefault();
    const amountVal = parseFloat(document.getElementById("depositAmountInput").value);
    const desc = document.getElementById("depositDescInput").value.trim() || "Nạp tiền vào tài khoản iBanking";
    const errorAlert = document.getElementById("depositErrorAlert");
    const btnSubmit = document.getElementById("btnSubmitDeposit");
    const MAX_DEPOSIT = 500000000;

    if (isNaN(amountVal) || amountVal <= 0) {
        errorAlert.textContent = "Vui lòng nhập số tiền nạp hợp lệ (> 0 VNĐ).";
        errorAlert.classList.remove("hidden");
        return;
    }

    if (amountVal > MAX_DEPOSIT) {
        errorAlert.textContent = `Số tiền nạp tối đa là ${formatVND(MAX_DEPOSIT)} cho mỗi giao dịch.`;
        errorAlert.classList.remove("hidden");
        return;
    }

    btnSubmit.disabled = true;
    btnSubmit.querySelector(".spinner").classList.remove("hidden");
    errorAlert.classList.add("hidden");

    try {
        const resp = await fetch(`${API_BASE_URL}/users/me/deposit`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
                amount: amountVal,
                description: desc
            })
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.detail || "Nạp tiền không thành công.");
        }

        // Cập nhật state số dư
        state.currentUser.balance = data.new_balance;
        renderUserInfo(state.currentUser);

        // ĐỒNG BỘ TRẠNG THÁI THANH TOÁN:
        // Nếu màn hình tra cứu đang mở sẵn một sinh viên có nợ, kích hoạt lại điều kiện
        // để nút Xác nhận giao dịch tự động sáng lên ngay mà không bắt gõ lại MSSV!
        if (state.currentTuition && state.currentTuition.status === "UNPAID") {
            const termsCheckbox = document.getElementById("agreeTermsCheckbox");
            if (termsCheckbox) {
                termsCheckbox.checked = true;
            }
            validatePaymentConditions();
        }

        closeDepositModal();
        showToast(`🎉 Nạp thành công ${formatVND(amountVal)}! Số dư mới: ${formatVND(data.new_balance)}. Nút xác nhận thanh toán đã sẵn sàng!`, "success");

        // Nếu đang ở tab lịch sử, tải lại lịch sử
        if (!document.getElementById("historyTab").classList.contains("hidden")) {
            loadTransactionHistory();
        }
    } catch (err) {
        errorAlert.textContent = err.message;
        errorAlert.classList.remove("hidden");
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.querySelector(".spinner").classList.add("hidden");
    }
}

