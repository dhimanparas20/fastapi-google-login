from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth

from app.config import settings
from app.dependencies import (
    create_access_token,
    create_refresh_token,
    revoke_token,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")
security = HTTPBearer(auto_error=False)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login")
async def login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/login?error=auth_failed")

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(url="/login?error=no_user_info")

    user_data = {
        "sub": user_info["sub"],
        "email": user_info["email"],
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
    }

    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data=user_data)

    return RedirectResponse(
        url=f"/auth/success?access_token={access_token}&refresh_token={refresh_token}"
    )


@router.get("/success")
async def auth_success(request: Request, access_token: str, refresh_token: str):
    return templates.TemplateResponse(
        request,
        "pages/auth_success.html",
        {
            "request": request,
            "project_name": settings.PROJECT_NAME,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Revoke the current access token so it can no longer be used."""
    if credentials:
        payload = verify_token(credentials.credentials, token_type="access")
        jti = payload.get("jti")
        if jti:
            revoke_token(jti)
    return {"message": "Logged out"}


@router.get("/logout")
async def logout_get():
    """GET logout for browser navigation (clears client-side tokens)."""
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
