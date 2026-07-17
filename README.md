# FastAPI Google Auth Template

A production-ready FastAPI template with Google OAuth 2.0, JWT authentication, token revocation, dark/light themes, and responsive UI.

---

## Project Structure

```
.
├── main.py                     # Entry point (your app's main file)
├── google_auth/                # All auth-related code (copy this folder)
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api.py              # API endpoints (/api/me, /api/refresh)
│   │   ├── auth.py             # Google OAuth routes
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   └── dependencies.py     # JWT utilities
│   ├── static/
│   │   ├── css/                # Stylesheets
│   │   └── js/                 # Client scripts
│   ├── templates/
│   │   ├── base.html           # Base template
│   │   ├── pages/              # Page templates
│   │   └── partials/           # Reusable components
│   ├── AGENTS.md               # AI assistant rules
│   └── README.md               # Detailed documentation
├── .env.example                # Environment template
├── pyproject.toml              # Dependencies
└── README.md                   # This file
```

---

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add redirect URI: `http://127.0.0.1:8000/auth/callback`
5. Copy Client ID and Client Secret

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=generate-with-this-command
JWT_SECRET_KEY=generate-with-this-command
```

Generate secure keys:
```bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run

```bash
uv run main.py
```

Open **http://127.0.0.1:8000**

---

## Using This Template

### Copy to Your Project

```bash
# Copy the google_auth folder to your project
cp -r google_auth/ /path/to/your/project/

# Copy required files
cp main.py /path/to/your/project/
cp .env.example /path/to/your/project/
cp pyproject.toml /path/to/your/project/

# Add dependencies to your project
uv add fastapi uvicorn python-jose[cryptography] python-multipart authlib httpx pydantic-settings jinja2
```

### Integrate with Your FastAPI App

In your existing `main.py`:

```python
from fastapi import FastAPI
from google_auth.app.api import router as api_router
from google_auth.app.auth import router as auth_router
from google_auth.app.config import settings

app = FastAPI()

# Mount static files
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="google_auth/static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(api_router)
```

---

## Features

- **Google OAuth 2.0** - One-click sign in
- **JWT Tokens** - Access + Refresh tokens with expiry
- **Token Revocation** - JTI-based blacklist system
- **Security Headers** - CSP, HSTS, X-Frame-Options, etc.
- **Rate Limiting** - 30 requests/minute per IP
- **Dark/Light Theme** - Toggle with persistence
- **Responsive UI** - Works on all devices

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auth/login` | No | Start Google OAuth |
| GET | `/auth/callback` | No | OAuth callback |
| GET | `/auth/success` | No | Token exchange page |
| POST | `/auth/logout` | Yes | Revoke token |
| GET | `/api/me` | Yes | Get user info |
| POST | `/api/refresh` | Yes | Refresh access token |

---

## Security

- Tokens transferred via httponly cookies (not URLs)
- All security headers applied (CSP, HSTS, etc.)
- Rate limiting on all endpoints
- Secret key validation on startup
- Input validation on all parameters

---

## Detailed Documentation

See `google_auth/README.md` for:
- Full setup guide
- API testing with Postman/cURL
- Database integration
- Production deployment

See `google_auth/AGENTS.md` for:
- Code conventions
- Architecture rules
- Security architecture
