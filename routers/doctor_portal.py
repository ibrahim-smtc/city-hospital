"""
routers/doctor_portal.py
------------------------
Endpoints for doctor authentication and management of their appointments.

Endpoints:
  POST /doctor-login                                       — authenticate doctor, return session token
  GET  /doctor/appointments                               — view logged-in doctor's appointments
  POST /doctor/appointments/{appointment_id}/confirm      — confirm a pending appointment belonging to this doctor
  POST /doctor/appointments/{appointment_id}/complete     — complete a confirmed consultation (fires Perfox webhook notification)
"""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from db.store import (
    complete_consultation,
    confirm_appointment_for_doctor,
    create_doctor_session,
    get_appointments_for_doctor,
    get_doctor_account_by_email,
    get_doctor_by_id,
    get_doctor_id_from_token,
)
from models import ConsultationCompleteRequest
from notification_service import notify_consultation_complete

router = APIRouter(tags=["DoctorPortal"])

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
#  Request / Response Models
# ---------------------------------------------------------------------------

class DoctorLoginRequest(BaseModel):
    email: str = Field(..., examples=["adithya.v.naragund@drcityhospital.com"])
    password: str = Field(..., examples=["Demo@2026"])


class DoctorLoginResponse(BaseModel):
    success: bool = True
    token: str
    doctor_id: int
    name: str


# ---------------------------------------------------------------------------
#  Auth Dependency
# ---------------------------------------------------------------------------

async def get_current_doctor_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> int:
    """
    Dependency that extracts and validates the Bearer token from the
    Authorization header. Returns the doctor_id associated with the session.
    Raises 401 if missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")

    doctor_id = get_doctor_id_from_token(credentials.credentials)
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")

    return doctor_id


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/doctor-login",
    response_model=DoctorLoginResponse,
    summary="Doctor login",
    description="Authenticate with doctor email and password. Returns a session token on success.",
)
def doctor_login(payload: DoctorLoginRequest):
    """
    Authenticate a doctor and return a session token.
    Generic error returned whether email or password is invalid.
    """
    account = get_doctor_account_by_email(payload.email)
    if not account:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password with bcrypt
    try:
        is_valid = bcrypt.checkpw(
            payload.password.encode("utf-8"),
            account["password_hash"].encode("utf-8"),
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    doctor_id = account["doctor_id"]
    doc = get_doctor_by_id(doctor_id)
    name = doc["name"] if doc else ""

    token = create_doctor_session(doctor_id)

    return DoctorLoginResponse(
        success=True,
        token=token,
        doctor_id=doctor_id,
        name=name,
    )


@router.get(
    "/doctor/appointments",
    summary="Get doctor's appointments",
    description="List all appointments assigned to the currently authenticated doctor.",
)
def list_doctor_appointments(doctor_id: int = Depends(get_current_doctor_id)):
    """
    Fetch all appointments for the logged-in doctor.
    """
    appointments = get_appointments_for_doctor(doctor_id)
    return {
        "success": True,
        "count": len(appointments),
        "data": appointments,
    }


@router.post(
    "/doctor/appointments/{appointment_id}/confirm",
    summary="Confirm appointment",
    description="Confirm a pending appointment assigned to the currently authenticated doctor.",
)
def confirm_doctor_appointment(
    appointment_id: str,
    doctor_id: int = Depends(get_current_doctor_id),
):
    """
    Confirm an appointment if it belongs to the authenticated doctor and is in 'pending' status.
    """
    updated = confirm_appointment_for_doctor(appointment_id, doctor_id)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found, does not belong to you, or is not in pending status",
        )

    return {
        "success": True,
        "message": "Appointment confirmed successfully",
        "data": updated,
    }


@router.post(
    "/doctor/appointments/{appointment_id}/complete",
    summary="Complete consultation",
    description="Complete a consultation for a confirmed appointment assigned to the currently authenticated doctor. Fires a Perfox webhook notification when patient_email is provided.",
)
def complete_doctor_consultation(
    appointment_id: str,
    payload: ConsultationCompleteRequest,
    doctor_id: int = Depends(get_current_doctor_id),
):
    """
    Complete an appointment consultation if it belongs to the authenticated doctor
    and is currently in 'confirmed' status.

    If payload.patient_email is non-blank, fires a Perfox webhook notification
    synchronously. Webhook failures are captured in email_sent/email_error and
    never cause this endpoint to fail.
    """
    updated = complete_consultation(
        appointment_id=appointment_id,
        doctor_id=doctor_id,
        patient_email=payload.patient_email,
        labs_ordered=payload.labs_ordered,
        imaging_ordered=payload.imaging_ordered,
        meds_prescribed=payload.meds_prescribed,
        billing_pending=payload.billing_pending,
        followup_needed=payload.followup_needed,
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found, does not belong to you, or is not in confirmed status",
        )

    # Build response base
    response: dict = {
        "success": True,
        "message": "Consultation completed successfully",
        "data": updated,
    }

    # Fire notification only when patient_email is non-blank
    if payload.patient_email:
        # doctor_name and patient_name come from the dict returned by complete_consultation
        doctor_name = updated.get("doctor_name") or ""
        patient_name = updated.get("patient_name") or ""

        email_ok, email_err = notify_consultation_complete(
            patient_email=payload.patient_email,
            patient_name=patient_name,
            doctor_name=doctor_name,
            labs_ordered=payload.labs_ordered,
            imaging_ordered=payload.imaging_ordered,
            meds_prescribed=payload.meds_prescribed,
            billing_pending=payload.billing_pending,
            followup_needed=payload.followup_needed,
        )
        response["email_sent"] = email_ok
        if not email_ok:
            response["email_error"] = email_err
    else:
        response["email_sent"] = False

    return response
