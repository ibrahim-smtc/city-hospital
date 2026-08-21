"""
routers/specialties.py
----------------------
API endpoint for listing hospital specialties.

Endpoint:
  GET /specialties  — list all specialties (Cardiology, Neurology, etc.)
"""

from fastapi import APIRouter

from models import SpecialtyListResponse  # type: ignore # pyrefly: ignore [missing-import]
from store import get_all_specialties  # type: ignore # pyrefly: ignore [missing-import]

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get(
    "",
    response_model=SpecialtyListResponse,
    summary="List specialties",
    description=(
        "Return all hospital specialties such as Cardiology, Neurology, "
        "Orthopaedics, etc. Each specialty includes a name, slug, and description."
    ),
)
def list_specialties():
    """Fetch all specialties from the database."""
    specialties = get_all_specialties()
    return {"success": True, "count": len(specialties), "data": specialties}
