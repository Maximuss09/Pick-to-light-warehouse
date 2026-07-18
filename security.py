"""NEW: temporary shared-admin protection for destructive inventory uploads."""

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# NEW: HTTP Basic is intentionally temporary until individual supervisor accounts are designed.
upload_security = HTTPBasic()


def require_layout_upload_access(
    credentials: HTTPBasicCredentials = Depends(upload_security),
) -> str:
    """Allow the configured shared admin account to replace inventory."""
    expected_username = os.getenv("PICK_TO_LIGHT_ADMIN_USERNAME")
    expected_password = os.getenv("PICK_TO_LIGHT_ADMIN_PASSWORD")

    # NEW: fail closed when credentials have not been configured for this environment.
    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload access is not configured on this server.",
        )

    username_is_valid = secrets.compare_digest(credentials.username, expected_username)
    password_is_valid = secrets.compare_digest(credentials.password, expected_password)
    if not username_is_valid or not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid upload credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
