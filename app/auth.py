# app/auth.py
from __future__ import annotations

import os
from fastapi import Request
from starlette.responses import RedirectResponse

# Admin-Zugang NUR über Environment-Variablen
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_USERNAME und ADMIN_PASSWORD müssen als Environment-Variablen gesetzt sein."
    )


def login_admin(request: Request) -> None:
    request.session["is_admin"] = True


def logout_admin(request: Request) -> None:
    request.session.clear()


def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def require_admin(request: Request):
    """Hilfsfunktion für Admin-Routen."""
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None
