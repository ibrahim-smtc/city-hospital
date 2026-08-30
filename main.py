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

import os
import secrets

# pyrefly: ignore [missing-import]
from fastapi import Depends, FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi_mcp import AuthConfig, FastApiMCP

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

# ---------------------------------------------------------------------------
#  MCP server — exposes the API above as tools for MCP clients (e.g. Perfox)
#
#  Every route is turned into a tool automatically, except "Chat" (the
#  keyword-matcher stub isn't meant to be called by an agent). Set MCP_API_KEY
#  to require a bearer token; leave it unset for open access during local dev.
# ---------------------------------------------------------------------------
_mcp_bearer_scheme = HTTPBearer(auto_error=False)


async def _verify_mcp_token(
    credentials: HTTPAuthorizationCredentials = Depends(_mcp_bearer_scheme),
):
    expected_key = os.environ.get("MCP_API_KEY")
    if not expected_key:
        return
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing MCP API key")


mcp = FastApiMCP(
    app,
    name="Hospital MCP Server",
    description=(
        "Tools for browsing doctors, hospital specialties, and support services, "
        "and for booking, checking, listing, and cancelling appointments."
    ),
    exclude_tags=["Chat"],
    auth_config=AuthConfig(dependencies=[Depends(_verify_mcp_token)]),
)
mcp.mount_http(mount_path="/mcp")


# pyrefly: ignore [missing-import]
from fastapi.responses import RedirectResponse

# ---------------------------------------------------------------------------
#  Root endpoint — Redirect to frontend
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """Redirects to the frontend application."""
    return RedirectResponse(url="/app/")
