from slowapi import Limiter
from fastapi import Request

def get_real_ip(request: Request) -> str:
    """Retrieves the real client IP, accounting for Cloud Run load balancers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain: client, proxy1, proxy2...
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

limiter = Limiter(key_func=get_real_ip)
