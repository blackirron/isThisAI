from fastapi import Header, HTTPException
from app.core.config import settings


async def verify_token(x_auth_token: str | None = Header(default=None)):
    """Simple shared-secret gate. Open in development, enforced in production.
    Not a real user-auth system - just stops randoms from burning your API key."""
    if settings.ENVIRONMENT == "development":
        return True
    if x_auth_token != settings.AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
