# main.py
from __future__ import annotations

import os
from typing import List, Dict

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from deta import Deta

# =====================
# Konfiguration
# =====================

EVENT_ID = "dlrg-sommerfest-2025"
EVENT_TITLE = "DLRG Sommerfest 2025"
EVENT_DESCRIPTION = "Dienst- und Helferplanung für das Sommerfest."

# Zeitslots: id, Label, Zeit, Kategorie
SLOTS = [
    {"id": "SLOT_1", "label": "Aufbau", "time": "08:00–10:00"},
    {"id": "SLOT_2", "label": "Frühe Schicht", "time": "10:00–13:00"},
    {"id": "SLOT_3", "label": "Spätschicht", "time": "13:00–16:00"},
    {"id": "SLOT_4", "label": "Abbau", "time": "16:00–18:00"},
]

# Optional: einfacher PIN-Schutz pro Event
EVENT_PIN = os.getenv("EVENT_PIN", "").strip()  # leer = kein PIN

# =====================
# Deta Base initialisieren
# =====================

# In Deta Space brauchst du den Key nicht explizit; lokal kannst du ihn setzen
DETA_PROJECT_KEY = os.getenv("DETA_PROJECT_KEY")
deta = Deta(DETA_PROJECT_KEY) if DETA_PROJECT_KEY else Deta()
signups_db = deta.Base(f"signups_{EVENT_ID}")

# =====================
# FastAPI + Templates
# =====================

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _load_signups() -> List[Dict]:
    """Alle Anmeldungen aus der DB holen."""
    res = signups_db.fetch()
    items = res.items
    # Bei vielen Einträgen müsste man hier paginieren; für DLRG reicht fetch() einmal
    while res.last:
        res = signups_db.fetch(last=res.last)
        items.extend(res.items)
    # Sortierung nach Name
    items.sort(key=lambda x: x.get("name", "").lower())
    return items


@app.get("/", response_class=HTMLResponse)
async def root_redirect():
    return RedirectResponse(url=f"/event/{EVENT_ID}")


@app.get("/event/{event_id}", response_class=HTMLResponse)
async def show_event(request: Request, event_id: str):
    if event_id != EVENT_ID:
        return HTMLResponse("Unbekanntes Event", status_code=404)

    signups = _load_signups()

    # Übersicht pro Slot vorbereiten: Slot -> [Namen]
    slot_to_names: Dict[str, List[str]] = {slot["id"]: [] for slot in SLOTS}
    for s in signups:
        for sid in s.get("slots", []):
            if sid in slot_to_names:
                slot_to_names[sid].append(s["name"])

    return templates.TemplateResponse(
        "event.html",
        {
            "request": request,
            "event_id": EVENT_ID,
            "event_title": EVENT_TITLE,
            "event_description": EVENT_DESCRIPTION,
            "slots": SLOTS,
            "signups": signups,
            "slot_to_names": slot_to_names,
            "event_pin_required": bool(EVENT_PIN),
        },
    )


@app.post("/event/{event_id}/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    event_id: str,
    name: str = Form(...),
    note: str = Form(""),
    slots: List[str] = Form(default=[]),
    pin: str = Form(""),
):
    if event_id != EVENT_ID:
        return HTMLResponse("Unbekanntes Event", status_code=404)

    name = name.strip()
    if not name:
        return HTMLResponse("Name darf nicht leer sein.", status_code=400)

    # PIN prüfen (falls gesetzt)
    if EVENT_PIN and pin != EVENT_PIN:
        # Du kannst hier auch eine Fehlermeldung im Template rendern
        return HTMLResponse("Falscher PIN.", status_code=403)

    # Nur gültige Slots übernehmen
    valid_slot_ids = {s["id"] for s in SLOTS}
    cleaned_slots = [s for s in slots if s in valid_slot_ids]

    key = name.lower()  # "Identität" der Person

    signups_db.put(
        {
            "name": name,
            "slots": cleaned_slots,
            "note": note.strip(),
        },
        key=key,
    )

    # Nach dem Speichern zurück zur Event-Seite
    return RedirectResponse(url=f"/event/{EVENT_ID}", status_code=303)
