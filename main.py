from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import appointments, doctors

app = FastAPI(
    title="Hospital Demo API",
    description="Fetch doctors, book an appointment, and check appointment status.",
    version="1.0.0",
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
