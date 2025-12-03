# app/auth.py
from __future__ import annotations

import os
from fastapi import Request
from starlette.responses import RedirectResponse

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")  # in Render als Secret setzen

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
