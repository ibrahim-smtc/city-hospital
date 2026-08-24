"""
routers/appointments.py
-----------------------
API endpoints for booking and managing appointments.

Endpoints:
  POST   /appointments                   — book a new appointment
  GET    /appointments                   — list appointments (with filters)
  GET    /appointments/{appointment_id}  — check one appointment's status
  DELETE /appointments/del_appt          — delete an appointment by ID or phone lookup
"""

import json
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query

from models import (  # type: ignore # pyrefly: ignore [missing-import]
    AppointmentCreateRequest,
    AppointmentDeleteLookupResponse,
    AppointmentDeleteResponse,
    AppointmentListResponse,
    AppointmentResponse,
)
from store import (  # type: ignore # pyrefly: ignore [missing-import]
    create_appointment,
    delete_appointment,
    get_appointment_by_id,
    list_appointments,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    status_code=201,
    response_model=AppointmentResponse,
    summary="Book an appointment",
    description=(
        "Create a new appointment. The system will:\n"
        "1. Check that the doctor exists\n"
        "2. Validate the time slot is in the doctor's available slots\n"
        "3. Prevent double-booking (same doctor + date + slot)\n"
        "4. Return a unique appointment ID (e.g. APPT-1001)"
    ),
    responses={
        404: {"description": "Doctor ID was not found."},
        409: {"description": "The slot is unavailable or already booked."},
    },
)
def book_appointment(payload: AppointmentCreateRequest):
    """
    Book a new appointment.
    The store layer handles all validation and raises ValueError
    with specific error codes if something goes wrong.
    """
    try:
        appointment = create_appointment({
            "patient_name": payload.patient_name,
            "patient_phone": payload.patient_phone,
            "doctor_id": payload.doctor_id,
            "date": payload.date,
            "slot": payload.slot,
            "reason": payload.reason or "",
        })
    except ValueError as e:
        error_msg = str(e)

        # Doctor not found
        if error_msg == "DOCTOR_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Invalid time slot — include the available slots in the response
        if error_msg.startswith("INVALID_SLOT"):
            available_slots = json.loads(error_msg.split("|")[1])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"Slot '{payload.slot}' is not available for this doctor",
                    "available_slots": available_slots,
                },
            )

        # Slot already booked by someone else
        if error_msg == "SLOT_ALREADY_BOOKED":
            raise HTTPException(
                status_code=409,
                detail=f"Slot '{payload.slot}' on {payload.date} is already booked for this doctor",
            )

        # Unexpected error
        raise HTTPException(status_code=500, detail="Something went wrong")

    return {
        "success": True,
        "message": "Appointment booked successfully",
        "data": appointment,
    }


@router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List appointments",
    description=(
        "Return appointments, optionally filtered by patient phone number "
        "or appointment ID. Returns date, time slot, status, and doctor info."
    ),
)
def list_all_appointments(
    phone: Optional[str] = Query(
        None,
        description="Filter by patient's phone number",
        examples=["9876543211"],
    ),
    appointment_id: Optional[str] = Query(
        None,
        description="Filter by appointment ID (e.g. APPT-1001)",
        examples=["APPT-1001"],
    ),
):
    """
    List appointments with optional filters.
    If no filters are provided, returns all appointments.
    """
    appointments = list_appointments(phone=phone, appointment_id=appointment_id)
    return {"success": True, "count": len(appointments), "data": appointments}


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Check an appointment",
    description=(
        "Return the booking details and current status for a specific appointment. "
        "Includes doctor name, date, time slot, and patient info."
    ),
    responses={404: {"description": "Appointment ID was not found."}},
)
def check_appointment(appointment_id: str):
    """
    Look up a single appointment by its ID (e.g. APPT-1001).
    Returns 404 if the appointment doesn't exist.
    """
    appointment = get_appointment_by_id(appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"success": True, "data": appointment}


@router.delete(
    "/del_appt",
    response_model=None,
    summary="Delete an appointment",
    description=(
        "Delete an appointment by its ID.\n\n"
        "**Two ways to use this endpoint:**\n"
        "1. **If you know the appointment ID** — pass `appointment_id` (e.g. APPT-1001) "
        "and the appointment will be deleted immediately.\n"
        "2. **If you don't know the ID** — pass `phone` (the patient's mobile number) "
        "and the endpoint will return all appointments for that number. "
        "Then call this endpoint again with the chosen `appointment_id` to delete it."
    ),
    responses={
        200: {
            "description": "Appointment deleted successfully.",
            "model": AppointmentDeleteResponse,
        },
        404: {"description": "Appointment or phone number not found."},
        400: {"description": "Neither appointment_id nor phone was provided."},
    },
)
def del_appt(
    appointment_id: Optional[str] = Query(
        None,
        description="Appointment ID to delete (e.g. APPT-1001)",
        examples=["APPT-1001"],
    ),
    phone: Optional[str] = Query(
        None,
        description="Patient's mobile number to look up appointments",
        examples=["9876543211"],
    ),
):
    """
    Delete an appointment.

    - If `appointment_id` is provided, the appointment is deleted directly.
    - If only `phone` is provided, all appointments for that phone number
      are returned so the user can choose which one to delete.
    - If neither is provided, a 400 error is returned.
    """

    # ── Case 1: appointment_id provided → delete it directly ──
    if appointment_id:
        deleted = delete_appointment(appointment_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {
            "success": True,
            "message": "Appointment deleted successfully",
            "data": deleted,
        }

    # ── Case 2: only phone provided → look up appointments ──
    if phone:
        appointments = list_appointments(phone=phone)
        if not appointments:
            raise HTTPException(
                status_code=404,
                detail="No appointments found for this phone number",
            )
        return {
            "success": True,
            "message": (
                "Multiple appointments found. "
                "Please provide the appointment_id to delete."
            ),
            "count": len(appointments),
            "data": appointments,
        }

    # ── Case 3: nothing provided → bad request ──
    raise HTTPException(
        status_code=400,
        detail="Please provide either 'appointment_id' or 'phone' as a query parameter",
    )
