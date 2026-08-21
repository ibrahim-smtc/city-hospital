"""
routers/services.py
-------------------
API endpoint for listing hospital support services and clinics.

Endpoint:
  GET /services  — list all services (Diabetes Clinic, Blood Center, etc.)
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter

from models import ServiceListResponse 
from store import get_all_services 

router = APIRouter(prefix="/services", tags=["Services"])


@router.get(
    "",
    response_model=ServiceListResponse,
    summary="List services",
    description=(
        "Return all hospital support services and clinics such as "
        "Diabetes Clinic, Blood Center, COPD Clinic, etc. "
        "Each service includes a name, type, and description."
    ),
)
def list_services():
    """Fetch all support services from the database."""
    services = get_all_services()
    return {"success": True, "count": len(services), "data": services}
