# app/main.py
from __future__ import annotations

import os
from datetime import datetime, date, time
from typing import List, Optional, Dict

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Event, Slot, Signup, SignupSlot
from .auth import ADMIN_USERNAME, ADMIN_PASSWORD, login_admin, logout_admin, require_admin

# DB-Schema erzeugen (für erste Version ohne Alembic ok)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Sessions für Admin-Login
SECRET_KEY = os.getenv("SESSION_SECRET", "change-this-secret")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static + Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/admin/events", status_code=302)

# =========================
# Admin Auth
# =========================

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        login_admin(request)
        return RedirectResponse(url="/admin/events", status_code=303)
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Benutzername oder Passwort falsch."},
        status_code=401,
    )


@app.get("/admin/logout")
async def admin_logout(request: Request):
    logout_admin(request)
    return RedirectResponse(url="/admin/login", status_code=303)


# =========================
# Admin: Events
# =========================

@app.get("/admin/events", response_class=HTMLResponse)
async def admin_events(
    request: Request,
    db: Session = Depends(get_db),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    events = db.query(Event).order_by(Event.start_date, Event.title).all()
    return templates.TemplateResponse(
        "admin_events.html",
        {"request": request, "events": events},
    )


@app.get("/admin/events/new", response_class=HTMLResponse)
async def admin_event_new(
    request: Request,
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    return templates.TemplateResponse(
        "admin_event_form.html",
        {
            "request": request,
            "event": None,
        },
    )


@app.post("/admin/events/new", response_class=HTMLResponse)
async def admin_event_create(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    slug: str = Form(...),
    location: str = Form(""),
    description: str = Form(""),
    stand_number: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    event_pin: str = Form(""),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    slug = slug.strip().lower()
    if not slug:
        return HTMLResponse("Slug darf nicht leer sein.", status_code=400)

    if db.query(Event).filter_by(slug=slug).first():
        return HTMLResponse("Slug bereits vergeben.", status_code=400)

    def parse_date(value: str) -> Optional[date]:
        value = value.strip()
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    ev = Event(
        slug=slug,
        title=title.strip(),
        location=location.strip() or None,
        description=description.strip() or None,
        stand_number=stand_number.strip() or None,
        start_date=parse_date(start_date),
        end_date=parse_date(end_date),
        event_pin=event_pin.strip() or None,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return RedirectResponse(url=f"/admin/events/{ev.id}/edit", status_code=303)


@app.get("/admin/events/{event_id}/edit", response_class=HTMLResponse)
async def admin_event_edit(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    ev = db.query(Event).filter_by(id=event_id).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    slots = (
        db.query(Slot)
        .filter_by(event_id=ev.id)
        .order_by(Slot.date, Slot.time_start)
        .all()
    )

    return templates.TemplateResponse(
        "admin_event_form.html",
        {
            "request": request,
            "event": ev,
            "slots": slots,
        },
    )


@app.post("/admin/events/{event_id}/edit", response_class=HTMLResponse)
async def admin_event_update(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    title: str = Form(...),
    slug: str = Form(...),
    location: str = Form(""),
    description: str = Form(""),
    stand_number: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    event_pin: str = Form(""),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    ev = db.query(Event).filter_by(id=event_id).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    slug = slug.strip().lower()
    if not slug:
        return HTMLResponse("Slug darf nicht leer sein.", status_code=400)

    exists = db.query(Event).filter(Event.slug == slug, Event.id != ev.id).first()
    if exists:
        return HTMLResponse("Slug bereits vergeben.", status_code=400)

    def parse_date(value: str) -> Optional[date]:
        value = value.strip()
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    ev.slug = slug
    ev.title = title.strip()
    ev.location = location.strip() or None
    ev.description = description.strip() or None
    ev.stand_number = stand_number.strip() or None
    ev.start_date = parse_date(start_date)
    ev.end_date = parse_date(end_date)
    ev.event_pin = event_pin.strip() or None

    db.commit()
    return RedirectResponse(url=f"/admin/events/{ev.id}/edit", status_code=303)


@app.post("/admin/events/{event_id}/delete")
async def admin_event_delete(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    ev = db.query(Event).filter_by(id=event_id).first()
    if ev:
        db.delete(ev)
        db.commit()
    return RedirectResponse(url="/admin/events", status_code=303)


# =========================
# Admin: Slots
# =========================

@app.get("/admin/events/{event_id}/slots", response_class=HTMLResponse)
async def admin_slots_form(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    ev = db.query(Event).filter_by(id=event_id).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    slots = (
        db.query(Slot)
        .filter_by(event_id=ev.id)
        .order_by(Slot.date, Slot.time_start)
        .all()
    )

    return templates.TemplateResponse(
        "admin_slots_form.html",
        {
            "request": request,
            "event": ev,
            "slots": slots,
        },
    )


@app.post("/admin/events/{event_id}/slots/add", response_class=HTMLResponse)
async def admin_slot_add(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    label: str = Form(...),
    date_str: str = Form(...),
    time_start: str = Form(...),
    time_end: str = Form(...),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    ev = db.query(Event).filter_by(id=event_id).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    t_start = datetime.strptime(time_start, "%H:%M").time()
    t_end = datetime.strptime(time_end, "%H:%M").time()

    slot = Slot(
        event_id=ev.id,
        label=label.strip(),
        date=d,
        time_start=t_start,
        time_end=t_end,
    )
    db.add(slot)
    db.commit()
    return RedirectResponse(url=f"/admin/events/{ev.id}/slots", status_code=303)


@app.post("/admin/events/{event_id}/slots/{slot_id}/delete")
async def admin_slot_delete(
    request: Request,
    event_id: int,
    slot_id: int,
    db: Session = Depends(get_db),
):
    maybe_redirect = require_admin(request)
    if maybe_redirect:
        return maybe_redirect

    slot = db.query(Slot).filter_by(id=slot_id, event_id=event_id).first()
    if slot:
        db.delete(slot)
        db.commit()
    return RedirectResponse(url=f"/admin/events/{event_id}/slots", status_code=303)


# =========================
# Öffentliche Event-Seite
# =========================

@app.get("/e/{slug}", response_class=HTMLResponse)
async def public_event(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
):
    ev = db.query(Event).filter_by(slug=slug).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    slots = (
        db.query(Slot)
        .filter_by(event_id=ev.id)
        .order_by(Slot.date, Slot.time_start)
        .all()
    )

    # Signups + Zuordnung
    signups = db.query(Signup).filter_by(event_id=ev.id).order_by(Signup.name).all()

    slot_to_names: Dict[int, List[str]] = {s.id: [] for s in slots}
    for su in signups:
        for link in su.slots:
            if link.slot_id in slot_to_names:
                slot_to_names[link.slot_id].append(su.name)

    return templates.TemplateResponse(
        "event_public.html",
        {
            "request": request,
            "event": ev,
            "slots": slots,
            "signups": signups,
            "slot_to_names": slot_to_names,
            "event_pin_required": bool(ev.event_pin),
        },
    )


@app.post("/e/{slug}/signup", response_class=HTMLResponse)
async def public_signup(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    name: str = Form(...),
    contact: str = Form(""),
    note: str = Form(""),
    selected_slots: List[int] = Form(default=[]),
    pin: str = Form(""),
):
    ev = db.query(Event).filter_by(slug=slug).first()
    if not ev:
        return HTMLResponse("Event nicht gefunden", status_code=404)

    name = name.strip()
    if not name:
        return HTMLResponse("Name darf nicht leer sein.", status_code=400)

    # PIN prüfen (falls vorhanden)
    if ev.event_pin and pin != ev.event_pin:
        return HTMLResponse("Falscher PIN.", status_code=403)

    # Sicherstellen, dass Slots zum Event gehören
    valid_slot_ids = {
        s.id
        for s in db.query(Slot).filter_by(event_id=ev.id).all()
    }
    cleaned_slot_ids = [sid for sid in selected_slots if int(sid) in valid_slot_ids]

    # bestehenden Signup suchen
    signup = db.query(Signup).filter_by(event_id=ev.id, name=name).first()
    if not signup:
        signup = Signup(event_id=ev.id, name=name)

    signup.contact = contact.strip() or None
    signup.note = note.strip() or None

    # alte Links löschen
    signup.slots.clear()
    db.flush()

    # neue Links anlegen
    for sid in cleaned_slot_ids:
        link = SignupSlot(slot_id=int(sid))
        signup.slots.append(link)

    db.add(signup)
    db.commit()
    return RedirectResponse(url=f"/e/{slug}", status_code=303)
