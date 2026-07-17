# AGENTS.md - AI Assistant Rules for This Codebase

> **READ THIS FIRST** before making any changes.
> This document defines the rules, conventions, and architecture for this FastAPI Google OAuth template.

---

## Project Overview

- **Stack**: FastAPI + Google OAuth 2.0 + JWT + Jinja2
- **Package Manager**: `uv` (NOT pip)
- **Python Version**: 3.14
- **Entry Point**: `main.py` (run with `uv run main.py` or `uv run uvicorn main:app --reload`)

---

## Architecture

```
.
├── main.py                 # Entry point - middleware, page routes, app setup
├── app/
│   ├── __init__.py         # Empty (makes app/ a package)
│   ├── config.py           # Settings via pydantic-settings (loads .env)
│   ├── dependencies.py     # JWT create/verify/revoke utilities
│   ├── auth.py             # OAuth routes (/auth/login, /callback, /logout)
│   └── api.py              # Protected API endpoints (/api/me, /api/refresh)
├── templates/
│   ├── base.html           # Base template (all pages extend this)
│   ├── pages/              # Full page templates
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   └── auth_success.html
│   └── partials/           # Reusable components
│       ├── navbar.html
│       └── footer.html
├── static/
│   ├── css/                # Stylesheets (tokens, base, themes, layout, components)
│   └── js/                 # Client scripts (theme.js, app.js)
├── .env                    # Environment variables (git-ignored)
├── .env.example            # Template for .env
├── pyproject.toml          # Dependencies (uv manages this)
└── README.md               # Setup documentation
```

---

## Critical Rules

### 1. Entry Point Naming

**NEVER rename `main.py` to `app.py`.**

The `app/` directory is a Python package. If you create `app.py` in the root, Python will import the package directory instead of your file, causing:
```
ERROR: Error loading ASGI app. Attribute "app" not found in module "app".
```

The entry point must be `main.py` and the ASGI app must be named `app`:
```python
# main.py
app = FastAPI(title=settings.PROJECT_NAME, docs_url="/docs")
```

Run command: `uv run uvicorn main:app --reload`

---

### 2. Configuration System

**NEVER use `os.getenv()` or `python-dotenv` directly.**

This project uses `pydantic-settings` which auto-loads `.env`:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
    
    PROJECT_NAME: str = "My App"  # Default if not in .env
    GOOGLE_CLIENT_ID: str         # Required, no default

settings = Settings()  # Singleton - import and use this
```

**Priority order** (highest to lowest):
1. Actual environment variables (shell)
2. `.env` file values
3. Default values in class

**To add a new setting:**
1. Add field to `Settings` class in `app/config.py`
2. Add to `.env` and `.env.example`
3. Access via `settings.NEW_SETTING`

---

### 3. JWT Token System

**Every token MUST have a `jti` claim for revocation support.**

```python
# app/dependencies.py
from uuid import uuid4

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    jti = uuid4().hex  # REQUIRED
    to_encode.update({
        "exp": ...,
        "type": "access",  # or "refresh"
        "jti": jti         # REQUIRED for revocation
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
```

**Token verification flow:**
```python
payload = verify_token(token, token_type="access")
# 1. Decodes JWT
# 2. Checks token type matches
# 3. Checks if JTI is revoked
# 4. Returns payload or raises HTTPException
```

**Revocation storage:**
- Development: In-memory `set()` in `app/dependencies.py`
- **PRODUCTION**: Replace with Redis or database

---

### 4. API Authentication Pattern

**All protected routes MUST use `HTTPBearer()` dependency:**

```python
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

@router.get("/protected")
async def protected_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    # Process request...
```

**For optional auth (public routes that can optionally use auth):**
```python
security = HTTPBearer(auto_error=False)

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials:
        # Token provided, revoke it
        ...
```

---

### 5. Template Rules

**All page templates MUST:**
1. Extend `base.html`
2. Use `_ctx()` helper for context

```python
# main.py
def _ctx(request: Request, **extra):
    return {
        "request": request,
        "project_name": settings.PROJECT_NAME,
        "project_tagline": settings.PROJECT_TAGLINE,
        **extra,
    }

@app.get("/my-page", response_class=HTMLResponse)
async def my_page(request: Request):
    return templates.TemplateResponse(
        request, "pages/my_page.html", _ctx(request)
    )
```

**Template structure:**
```html
{% extends "base.html" %}

{% block title %}Page Title - {{ project_name }}{% endblock %}

{% block content %}
<!-- Page content here -->
{% endblock %}

{% block scripts %}
<!-- Page-specific JS here (optional) -->
{% endblock %}
```

**Static file references:**
```html
<!-- CORRECT -->
<link rel="stylesheet" href="{{ url_for('static', path='css/base.css') }}" />
<script src="{{ url_for('static', path='js/app.js') }}"></script>

<!-- WRONG -->
<link rel="stylesheet" href="/static/css/base.css" />
```

---

### 6. JavaScript Rules

**Use vanilla JS only. NO frameworks (React, Vue, etc.).**

**Pattern - IIFE (Immediately Invoked Function Expression):**
```javascript
(function () {
  "use strict";
  
  // Your code here
  var token = localStorage.getItem("access_token");
  
  // Event listeners
  document.getElementById("btn").addEventListener("click", function () {
    // ...
  });
})();
```

**Auth token handling:**
```javascript
// Storage keys
localStorage.getItem("access_token");
localStorage.getItem("refresh_token");

// API calls with auth
fetch("/api/me", {
  headers: { "Authorization": "Bearer " + token }
});

// Logout - revoke server-side, then clear client
fetch("/auth/logout", {
  method: "POST",
  headers: { "Authorization": "Bearer " + token }
}).finally(function () {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
});
```

---

### 7. CSS Architecture

**File load order in `base.html`:**
1. `tokens.css` - CSS variables (colors, spacing, typography)
2. `base.css` - Reset and base styles
3. `themes.css` - Dark/light theme definitions
4. `layout.css` - Grid and layout utilities
5. `components.css` - UI component styles

**Theme system:**
```html
<html data-theme="dark">
```

```css
:root[data-theme="dark"] {
  --color-bg: #0f1117;
}

:root[data-theme="light"] {
  --color-bg: #ffffff;
}
```

**Customize by editing `static/css/tokens.css` for design tokens.**

---

### 8. Import Order

**Python imports MUST follow this order:**
```python
# 1. Standard library
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt

# 3. Local imports (app.*)
from app.config import settings
from app.dependencies import verify_token
```

---

### 9. Error Handling

**API errors:**
```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid token"
)
```

**OAuth errors (redirect with query param):**
```python
return RedirectResponse(url="/login?error=auth_failed")
```

**Frontend error handling:**
```javascript
.catch(function () {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login?error=session_expired";
});
```

---

### 10. Security Rules

**NEVER:**
- Log tokens, secrets, or credentials
- Commit `.env` file to git
- Use HTTP (always HTTPS in production)
- Store passwords (this template uses OAuth only)
- Expose `SECRET_KEY` or `JWT_SECRET_KEY`

**ALWAYS:**
- Validate token type before processing
- Revoke tokens on logout
- Rotate refresh tokens on use
- Lock CORS to specific origins
- Use `url_for()` for static files

---

## Adding New Features

### Add a New Page

1. Create template at `templates/pages/my-page.html`:
```html
{% extends "base.html" %}
{% block title %}My Page - {{ project_name }}{% endblock %}
{% block content %}
<h1>My Page</h1>
{% endblock %}
```

2. Add route in `main.py`:
```python
@app.get("/my-page", response_class=HTMLResponse)
async def my_page(request: Request):
    return templates.TemplateResponse(
        request, "pages/my-page.html", _ctx(request)
    )
```

### Add a New API Endpoint

1. Add to `app/api.py`:
```python
@router.get("/my-endpoint")
async def my_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = verify_token(credentials.credentials)
    return {"data": "value"}
```

### Add a New Protected Route

1. Add to `main.py` with auth dependency:
```python
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

@app.get("/protected-page", response_class=HTMLResponse)
async def protected_page(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = verify_token(credentials.credentials)
    return templates.TemplateResponse(
        request, "pages/protected.html", 
        _ctx(request, user=payload)
    )
```

---

## Common Pitfalls

1. **`app.py` conflicts with `app/` directory** → Use `main.py`
2. **Missing `request` in template context** → Use `_ctx(request)` helper
3. **Token not revoking** → Ensure `jti` claim exists in token
4. **CORS errors** → Check `APP_BASE_URL` matches your frontend URL
5. **Template not found** → Check path is `pages/filename.html`, not just `filename.html`

---

## Security Architecture

### Token Transfer (OAuth Callback)
**NEVER pass tokens via URL query params** - they leak to logs, browser history, Referer header.

Current implementation uses signed session cookie:
```
/auth/callback → Set-Cookie: _auth_tokens (httponly, secure) → Redirect to /auth/success
/auth/success → Read cookie → Set localStorage → Delete cookie
```

### Security Headers (Applied via Middleware)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...`
- `Strict-Transport-Security: max-age=31536000` (HTTPS only)

### Rate Limiting
- In-memory rate limiter: 30 requests per 60 seconds per IP
- **PRODUCTION**: Replace with Redis-backed rate limiter (slowapi)

### Input Validation
- Error query params validated against whitelist: `auth_failed`, `no_user_info`, `session_expired`
- Never render user input directly in templates without escaping

### Token Security
- Tokens use `jti` claim for revocation support
- Refresh tokens rotate on use (old token revoked)
- Tokens passed via `Authorization: Bearer <header>` only
- Frontend checks token expiry before API calls

### Secret Key Validation
App refuses to start if `SECRET_KEY` or `JWT_SECRET_KEY` equals "change-me"

### CORS Configuration
```python
allow_origins=[settings.APP_BASE_URL]  # Specific origin only
allow_methods=["GET", "POST"]          # Minimal methods
allow_headers=["Authorization", "Content-Type"]  # Required headers only
```

---

## Development Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn main:app --reload --port 8000

# Or simply
uv run main.py

# Generate secret keys
uv run python -c "import secrets; print(secrets.token_hex(32))"

# Add a new dependency
uv add package-name

# Remove a dependency
uv remove package-name
```

---

## Production Checklist

Before deploying:
- [ ] Set `APP_BASE_URL` to your production domain (must be HTTPS)
- [ ] Generate new `SECRET_KEY` and `JWT_SECRET_KEY` (app won't start with defaults)
- [ ] Replace in-memory `_revoked_jtis` with Redis/database
- [ ] Add database for user storage (currently stateless)
- [ ] Enable HTTPS (app adds HSTS header automatically)
- [ ] Update Google OAuth redirect URIs to production URL
- [ ] Set `PROJECT_NAME` and `PROJECT_TAGLINE`
- [ ] Disable `/docs` endpoint or add auth protection
- [ ] Set up proper logging (tokens are NOT logged in requests)

---

## Version Control

**Git-ignored files:**
- `.env` (secrets)
- `.venv/` (virtual environment)
- `__pycache__/` (Python cache)

**Always commit:**
- `.env.example` (template)
- `pyproject.toml` (dependencies)
- `README.md` (documentation)
