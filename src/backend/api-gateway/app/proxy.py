import httpx
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from app.config import settings

HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade"
}

async def forward_request(
    target_url: str,
    request: Request,
    headers: dict = None,
    timeout: float = 15.0
):
    """
    Hàm chuyển tiếp (Forward) bất đồng bộ từ API Gateway sang các Microservices:
    1. Tái sử dụng HTTP Client Singleton qua request.app.state.http_client (Connection Pool chống cạn kiệt socket).
    2. Loại bỏ các header hop-by-hop (host, content-length, connection) để httpx tự tính toán chuẩn xác.
    3. Giải mã JWT Token và tự động bổ sung Header định danh nội bộ (X-User-Id, X-Username, X-User-Email).
    4. Gắn kèm X-Internal-Secret để downstream services tin cậy request từ Gateway.
    """
    # Lấy client singleton từ app.state (khởi tạo tại lifespan)
    client = getattr(request.app.state, "http_client", None)
    should_close_client = False
    if not client:
        client = httpx.AsyncClient(timeout=timeout)
        should_close_client = True

    # 1. Trích xuất body
    body = await request.body()

    # 2. Làm sạch headers
    forward_headers = {}
    for key, value in request.headers.items():
        if key.lower() not in HOP_BY_HOP_HEADERS:
            forward_headers[key] = value

    # 3. Phân giải context người dùng từ Authorization Bearer Token
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                forward_headers["X-User-Id"] = str(user_id)
            if payload.get("username"):
                forward_headers["X-Username"] = str(payload.get("username"))
            if payload.get("email"):
                forward_headers["X-User-Email"] = str(payload.get("email"))
        except JWTError:
            pass

    # 4. Gắn header xác thực nội bộ và truy vết phân tán (Correlation-ID)
    forward_headers["X-Internal-Secret"] = settings.INTERNAL_API_KEY
    corr_id = getattr(request.state, "correlation_id", None) or request.headers.get("x-correlation-id") or request.headers.get("X-Correlation-ID")
    if corr_id:
        forward_headers["X-Correlation-ID"] = corr_id

    # Đảm bảo Idempotency-Key (nếu có) được chuyển tiếp sang Payment Service
    idemp_key = request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key")
    if idemp_key:
        forward_headers["Idempotency-Key"] = idemp_key

    if headers:
        forward_headers.update(headers)

    try:
        resp = await client.request(
            method=request.method,
            url=target_url,
            params=dict(request.query_params),
            content=body if body else None,
            headers=forward_headers
        )

        response_headers = {}
        if corr_id:
            response_headers["X-Correlation-ID"] = corr_id

        try:
            content = resp.json()
            return JSONResponse(status_code=resp.status_code, content=content, headers=response_headers)
        except Exception:
            return JSONResponse(status_code=resp.status_code, content={"detail": resp.text}, headers=response_headers)

    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dịch vụ đích ({target_url}) tạm thời không thể kết nối. Vui lòng thử lại sau."
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Dịch vụ đích ({target_url}) phản hồi quá thời gian quy định (Timeout)."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi chuyển tiếp request tại API Gateway: {str(e)}"
        )
    finally:
        if should_close_client:
            await client.aclose()
