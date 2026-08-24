"""
models.py
---------
Pydantic models for request/response validation.

These models define the shape of data that flows through the API.
FastAPI uses them to:
  1. Validate incoming request bodies
  2. Serialize outgoing responses
  3. Generate the Swagger/OpenAPI docs automatically
"""

from typing import List, Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


# ===========================================================================
#  DOCTOR MODELS
# ===========================================================================

class Doctor(BaseModel):
    """A doctor record with basic info and availability."""
    id: int = Field(..., examples=[1])
    slug: str = Field(..., examples=["dr-naveen-a-j"])
    name: str = Field(..., examples=["Dr Naveen A J"])
    designation: str = Field(..., examples=["Senior Consultant - Interventional Cardiologist"])
    department: str = Field(..., examples=["Interventional Cardiologist"])
    description: Optional[str] = Field("", examples=["Senior Consultant Interventional Cardiologist at New Care Med Center"])
    experience_years: Optional[int] = Field(None, examples=[12])
    hospital_branch: str = Field("New Care Med Center Hospitals, Bangalore")
    available_days: List[str] = Field([], examples=[["Monday", "Wednesday", "Friday"]])
    available_slots: List[str] = Field([], examples=[["09:00", "10:30", "14:00"]])


class DoctorDetail(Doctor):
    """Extended doctor info — includes qualifications, expertise, etc."""
    qualifications: List[str] = Field([], examples=[["MBBS - JJM Medical College"]])
    expertise: List[str] = Field([], examples=[["Complex coronary interventions"]])
    memberships: List[str] = Field([], examples=[["Indian Medical Association"]])
    achievements: List[str] = Field([], examples=[["Gold Medal - Best Outgoing Trainee"]])
    publications: List[str] = Field([], examples=[["Published in BMJ Case Reports"]])


class DoctorListResponse(BaseModel):
    """Response for GET /doctors — returns a list of doctors."""
    success: bool = True
    count: int
    data: List[Doctor]


class DoctorDetailResponse(BaseModel):
    """Response for GET /doctors/{id} — returns one doctor with full details."""
    success: bool = True
    data: DoctorDetail


# ===========================================================================
#  SPECIALTY MODELS
# ===========================================================================

class Specialty(BaseModel):
    """A hospital specialty (e.g. Cardiology, Neurology)."""
    id: int = Field(..., examples=[1])
    slug: str = Field(..., examples=["cardiology"])
    name: str = Field(..., examples=["Cardiology"])
    description: Optional[str] = Field("", examples=["Advanced cardiology treatment and well-being"])


class SpecialtyListResponse(BaseModel):
    """Response for GET /specialties."""
    success: bool = True
    count: int
    data: List[Specialty]


# ===========================================================================
#  SERVICE MODELS
# ===========================================================================

class Service(BaseModel):
    """A support service or clinic (e.g. Diabetes Clinic, Blood Center)."""
    id: int = Field(..., examples=[1])
    slug: str = Field(..., examples=["diabetes-clinic"])
    name: str = Field(..., examples=["Diabetes Clinic"])
    type: Optional[str] = Field("", examples=["clinic"])
    description: Optional[str] = Field("", examples=["Best diabetes treatment from experienced specialists"])


class ServiceListResponse(BaseModel):
    """Response for GET /services."""
    success: bool = True
    count: int
    data: List[Service]


# ===========================================================================
#  APPOINTMENT MODELS
# ===========================================================================

class AppointmentCreateRequest(BaseModel):
    """
    Request body for POST /appointments — booking a new appointment.
    All fields are required except 'reason'.
    """
    patient_name: str = Field(
        ..., min_length=1,
        description="Patient's full name",
        examples=["Riya Sharma"],
    )
    patient_phone: str = Field(
        ..., min_length=1,
        description="Patient's contact number",
        examples=["9876543211"],
    )
    doctor_id: int = Field(
        ...,
        description="Doctor ID from GET /doctors",
        examples=[22],
    )
    date: str = Field(
        ...,
        description="Appointment date in YYYY-MM-DD format",
        examples=["2026-08-24"],
    )
    slot: str = Field(
        ...,
        description="One of the doctor's available time slots",
        examples=["10:30"],
    )
    reason: Optional[str] = Field(
        "",
        description="Reason for the visit (optional)",
        examples=["Cardiology consultation"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_name": "Riya Sharma",
                "patient_phone": "9876543211",
                "doctor_id": 22,
                "date": "2026-08-24",
                "slot": "10:30",
                "reason": "Cardiology consultation",
            }
        }
    }


class Appointment(BaseModel):
    """A single appointment record."""
    id: str = Field(..., examples=["APPT-1001"])
    patient_name: str = Field(..., examples=["Riya Sharma"])
    patient_phone: str = Field(..., examples=["9876543211"])
    doctor_id: int = Field(..., examples=[22])
    doctor_name: str = Field(..., examples=["Dr Naveen A J"])
    department: Optional[str] = Field("", examples=["Interventional Cardiologist"])
    date: str = Field(..., examples=["2026-08-24"])
    slot: str = Field(..., examples=["10:30"])
    status: str = Field(..., examples=["pending"])
    reason: str = Field("", examples=["Cardiology consultation"])
    created_at: str = Field(..., examples=["2026-08-20T10:15:00+00:00"])


class AppointmentResponse(BaseModel):
    """Response for POST /appointments and GET /appointments/{id}."""
    success: bool = True
    message: Optional[str] = None
    data: Appointment


class AppointmentListResponse(BaseModel):
    """Response for GET /appointments — returns a list of appointments."""
    success: bool = True
    count: int
    data: List[Appointment]


class AppointmentDeleteResponse(BaseModel):
    """Response for DELETE /appointments/{id} — appointment deleted successfully."""
    success: bool = True
    message: str = "Appointment deleted successfully"
    data: Appointment
