from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from google_auth.app.api import router as api_router
from google_auth.app.auth import router as auth_router
from google_auth.app.config import settings

# Validate critical security settings on startup
if settings.SECRET_KEY == "change-me" or settings.JWT_SECRET_KEY == "change-me":
    raise RuntimeError(
        "SECURITY: SECRET_KEY and JWT_SECRET_KEY must be changed from defaults. "
        "Generate new keys with: uv run python -c \"import secrets; print(secrets.token_hex(32))\""
    )

app = FastAPI(title=settings.PROJECT_NAME, docs_url="/docs")

# Required by Authlib for OAuth state storage
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # CSP - adjust if you need to load external resources
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https://lh3.googleusercontent.com data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    # HSTS - only if using HTTPS
    if settings.APP_BASE_URL.startswith("https"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Rate limiting - simple in-memory store
# PRODUCTION: Use Redis-backed rate limiter (e.g., slowapi)
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30  # per window


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic rate limiting per IP."""
    client_ip = request.client.host if request.client else "unknown"
    now = __import__("time").time()

    # Clean old entries
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
        ]
    else:
        _rate_limit_store[client_ip] = []

    # Check rate limit
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return Response(
            content='{"detail":"Too many requests. Please try again later."}',
            status_code=429,
            media_type="application/json",
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_BASE_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory="google_auth/static"), name="static")

templates = Jinja2Templates(directory="google_auth/templates")


def _ctx(request: Request, **extra):
    return {
        "request": request,
        "project_name": settings.PROJECT_NAME,
        "project_tagline": settings.PROJECT_TAGLINE,
        **extra,
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "pages/home.html", _ctx(request))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request, "pages/login.html", _ctx(request, error=error)
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "pages/dashboard.html", _ctx(request))


app.include_router(auth_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
