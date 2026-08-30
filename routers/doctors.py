"""
routers/doctors.py
------------------
API endpoints for browsing doctors.

Endpoints:
  GET /doctors              — list all doctors (optional department filter)
  GET /doctors/{doctor_id}  — get one doctor with full details
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query

from models import DoctorDetailResponse, DoctorListResponse  # type: ignore # pyrefly: ignore [missing-import]
from store import get_all_doctors, get_doctor_by_id  # type: ignore # pyrefly: ignore [missing-import]

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "",
    response_model=DoctorListResponse,
    summary="List doctors",
    description=(
        "Return all doctors from the hospital database. "
        "Use the optional `department` filter to narrow down by specialty area. "
        "The calling application already renders this list as a table for the "
        "user — reply with a short conversational summary, not a repeated table."
    ),
)
def list_doctors(
    department: str = Query(
        None,
        description="Filter by department (partial match). E.g. 'Cardiology', 'ENT', 'Oncology'",
        examples=["Cardiology"],
    ),
):
    """
    Fetch doctors from the database.
    If a department is provided, only doctors whose department
    contains that text (case-insensitive) are returned.
    """
    doctors = get_all_doctors(department=department)
    return {"success": True, "count": len(doctors), "data": doctors}


@router.get(
    "/{doctor_id}",
    response_model=DoctorDetailResponse,
    summary="Get one doctor",
    description=(
        "Return full details for a specific doctor by ID, including "
        "available days, time slots, qualifications, expertise, and more. "
        "The calling application already renders this as a details card for "
        "the user — reply with a short conversational summary, not a repeated list."
    ),
    responses={404: {"description": "Doctor ID was not found."}},
)
def get_doctor(doctor_id: int):
    """
    Fetch a single doctor by their numeric ID.
    Returns 404 if the doctor doesn't exist.
    """
    doctor = get_doctor_by_id(doctor_id)

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return {"success": True, "data": doctor}
