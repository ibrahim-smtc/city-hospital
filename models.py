from typing import List, Optional

from pydantic import BaseModel, Field


class Doctor(BaseModel):
    id: str = Field(..., examples=["doc-005"])
    name: str = Field(..., examples=["Dr. Fatima Sheikh"])
    specialization: str = Field(..., examples=["Neurology"])
    department: str = Field(..., examples=["Neurosciences"])
    experienceYears: int = Field(..., examples=[20])
    rating: float = Field(..., ge=0, le=5, examples=[4.95])
    consultationFee: int = Field(..., ge=0, examples=[1200])
    availableDays: List[str] = Field(..., examples=[["Monday", "Thursday"]])
    availableSlots: List[str] = Field(..., examples=[["10:00", "10:30", "13:00"]])
    hospitalBranch: str = Field(..., examples=["City Hospital - Main"])


class Appointment(BaseModel):
    id: str = Field(..., examples=["appt-1020"])
    patientName: str = Field(..., examples=["Riya Sharma"])
    patientPhone: str = Field(..., examples=["9876543211"])
    doctorId: str = Field(..., examples=["doc-005"])
    doctorName: str = Field(..., examples=["Dr. Fatima Sheikh"])
    specialization: str = Field(..., examples=["Neurology"])
    date: str = Field(..., examples=["2026-08-24"])
    slot: str = Field(..., examples=["10:30"])
    status: str = Field(..., examples=["pending"])
    reason: str = Field(..., examples=["Neurology consultation"])
    createdAt: str = Field(..., examples=["2026-08-20T10:15:00+00:00"])


class AppointmentCreateRequest(BaseModel):
    patientName: str = Field(..., min_length=1, description="Patient's full name", examples=["Riya Sharma"])
    patientPhone: str = Field(..., min_length=1, description="Patient's contact number", examples=["9876543211"])
    doctorId: str = Field(..., min_length=1, description="ID from GET /doctors", examples=["doc-005"])
    date: str = Field(..., description="Appointment date in YYYY-MM-DD format", examples=["2026-08-24"])
    slot: str = Field(..., description="One of the selected doctor's availableSlots", examples=["10:30"])
    reason: Optional[str] = Field("", description="Reason for the visit", examples=["Neurology consultation"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "patientName": "Riya Sharma",
                "patientPhone": "9876543211",
                "doctorId": "doc-005",
                "date": "2026-08-24",
                "slot": "10:30",
                "reason": "Neurology consultation",
            }
        }
    }


class DoctorListResponse(BaseModel):
    success: bool = True
    count: int
    data: List[Doctor]


class DoctorResponse(BaseModel):
    success: bool = True
    data: Doctor


class AppointmentResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Appointment


class AppointmentListResponse(BaseModel):
    success: bool = True
    count: int
    data: List[Appointment]
