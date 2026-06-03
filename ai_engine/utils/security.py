from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verifies that the request contains the correct X-API-Key header.
    
    Fails closed (returns HTTP 500) if the server does not have INTERNAL_API_KEY configured.
    """
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API Key is not configured on the server."
        )
    
    if api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key."
        )
    
    return api_key
