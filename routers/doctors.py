from fastapi import APIRouter, HTTPException

from store import get_doctors

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("")
def list_doctors(
    rating: float = None,
    specialization: str = None,
    department: str = None,
    hospitalBranch: str = None,
):
    """Fetch doctors, optionally filtered by specialization, department, branch, or minimum rating."""
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


@router.get("/{doctor_id}")
def get_doctor(doctor_id: str):
    doctors = get_doctors()
    doctor = next((d for d in doctors if d["id"] == doctor_id), None)

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return {"success": True, "data": doctor}
