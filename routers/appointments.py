from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from models import AppointmentCreateRequest
from store import get_appointments, get_doctors, save_appointments

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _generate_appointment_id(appointments: list) -> str:
    max_num = 1000
    for a in appointments:
        try:
            num = int(str(a["id"]).split("-")[1])
        except (IndexError, ValueError):
            num = 0
        max_num = max(max_num, num)
    return f"appt-{max_num + 1}"


@router.post("", status_code=201)
def book_appointment(payload: AppointmentCreateRequest):
    """Book an appointment with a doctor for a given date and slot."""
    doctors = get_doctors()
    doctor = next((d for d in doctors if d["id"] == payload.doctorId), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if payload.slot not in doctor["availableSlots"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Slot {payload.slot} is not available for {doctor['name']}",
                "availableSlots": doctor["availableSlots"],
            },
        )

    appointments = get_appointments()

    already_booked = any(
        a["doctorId"] == payload.doctorId
        and a["date"] == payload.date
        and a["slot"] == payload.slot
        and a["status"] != "cancelled"
        for a in appointments
    )
    if already_booked:
        raise HTTPException(
            status_code=409,
            detail=f"Slot {payload.slot} on {payload.date} is already booked for {doctor['name']}",
        )

    new_appointment = {
        "id": _generate_appointment_id(appointments),
        "patientName": payload.patientName,
        "patientPhone": payload.patientPhone,
        "doctorId": doctor["id"],
        "doctorName": doctor["name"],
        "specialization": doctor["specialization"],
        "date": payload.date,
        "slot": payload.slot,
        "status": "pending",
        "reason": payload.reason or "",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    appointments.append(new_appointment)
    save_appointments(appointments)

    return {"success": True, "message": "Appointment booked successfully", "data": new_appointment}


@router.get("/{appointment_id}")
def check_appointment(appointment_id: str):
    """Check the status of a booked appointment by its id."""
    appointments = get_appointments()
    appointment = next((a for a in appointments if a["id"] == appointment_id), None)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"success": True, "data": appointment}


@router.get("")
def list_appointments(patientPhone: Optional[str] = None, status: Optional[str] = None):
    """List all appointments, optionally filtered by patient phone or status."""
    appointments = get_appointments()

    if patientPhone:
        appointments = [a for a in appointments if a["patientPhone"] == patientPhone]
    if status:
        appointments = [a for a in appointments if a["status"] == status]

    return {"success": True, "count": len(appointments), "data": appointments}
