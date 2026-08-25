"""
main.py
-------
Entry point for the Hospital Demo API.

This is a FastAPI application that provides endpoints for:
  - Browsing doctors and their availability
  - Listing hospital specialties and services
  - Booking and managing appointments

Start the server with:
  uvicorn main:app --reload
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles

from routers import appointments, chat, doctors, services, specialties  # type: ignore # pyrefly: ignore [missing-import]

# ---------------------------------------------------------------------------
#  Create the FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Hospital Demo API",
    description=(
        "A hospital API for discovering doctors, browsing specialties, "
        "booking appointments, and checking appointment status.\n\n"
        "## Getting started\n"
        "1. Call `GET /doctors` to find a doctor (filter by department).\n"
        "2. Call `GET /doctors/{id}` to see available days and time slots.\n"
        "3. Send doctor ID, date, and slot to `POST /appointments`.\n"
        "4. Use the returned appointment ID with `GET /appointments/{id}`.\n\n"
        "## Other endpoints\n"
        "- `GET /specialties` — browse hospital specialties\n"
        "- `GET /services` — browse support services and clinics\n"
        "- `POST /chat` — send queries to the hospital assistant"
    ),
    version="2.0.0",
    contact={"name": "Hospital API Team"},
)

# ---------------------------------------------------------------------------
#  Register routers (each router handles one group of endpoints)
# ---------------------------------------------------------------------------
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(specialties.router)
app.include_router(services.router)
app.include_router(chat.router)

# ---------------------------------------------------------------------------
#  Mount the static frontend (if it exists)
# ---------------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")


# pyrefly: ignore [missing-import]
from fastapi.responses import RedirectResponse

# ---------------------------------------------------------------------------
#  Root endpoint — Redirect to frontend
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """Redirects to the frontend application."""
    return RedirectResponse(url="/app/")
