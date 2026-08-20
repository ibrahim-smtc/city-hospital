from fastapi import APIRouter, HTTPException, Query

from models import DoctorListResponse, DoctorResponse
from store import get_doctors

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "",
    response_model=DoctorListResponse,
    summary="List doctors",
    description="Return all doctors. Use the optional filters to narrow the results.",
)
def list_doctors(
    rating: float = Query(None, ge=0, le=5, description="Minimum rating from 0 to 5", examples=[4.8]),
    specialization: str = Query(None, description="Exact specialization filter", examples=["Neurology"]),
    department: str = Query(None, description="Exact department filter", examples=["Neurosciences"]),
    hospitalBranch: str = Query(None, description="Exact hospital branch filter", examples=["City Hospital - Main"]),
):
    doctors = get_doctors()

    if specialization:
        doctors = [d for d in doctors if d["specialization"].lower() == specialization.lower()]
    if department:
        doctors = [d for d in doctors if d["department"].lower() == department.lower()]
    if hospitalBranch:
        doctors = [d for d in doctors if d["hospitalBranch"].lower() == hospitalBranch.lower()]
    if rating is not None:
        doctors = [d for d in doctors if d["rating"] >= rating]

    return {"success": True, "count": len(doctors), "data": doctors}


@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Get one doctor",
    description="Return a doctor by ID, including available days and time slots.",
    responses={404: {"description": "Doctor ID was not found."}},
)
def get_doctor(doctor_id: str):
    doctors = get_doctors()
    doctor = next((d for d in doctors if d["id"] == doctor_id), None)

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return {"success": True, "data": doctor}
