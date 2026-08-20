from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import appointments, doctors

app = FastAPI(
    title="Hospital Demo API",
    description=(
        "A demo hospital API for discovering doctors, booking appointments, "
        "listing appointments, and checking appointment status.\n\n"
        "## Getting started\n"
        "1. Call `GET /doctors` to find a doctor and available slots.\n"
        "2. Send the doctor's ID, date, and slot to `POST /appointments`.\n"
        "3. Use the returned appointment ID with `GET /appointments/{appointment_id}`."
    ),
    version="1.0.0",
    contact={"name": "Hospital API Team"},
)

app.include_router(doctors.router)
app.include_router(appointments.router)
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
def root():
    return {
        "success": True,
        "message": "Hospital Demo API",
        "endpoints": {
            "fetchDoctors": "GET /doctors",
            "bookAppointment": "POST /appointments",
            "checkAppointment": "GET /appointments/{id}",
        },
        "docs": "/docs",
    }
