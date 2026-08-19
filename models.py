from typing import List, Optional
from pydantic import BaseModel, Field


class Doctor(BaseModel):
    id: str
    name: str
    specialization: str
    department: str
    experienceYears: int
    rating: float
    consultationFee: int
    availableDays: List[str]
    availableSlots: List[str]
    hospitalBranch: str


class Appointment(BaseModel):
    id: str
    patientName: str
    patientPhone: str
    doctorId: str
    doctorName: str
    specialization: str
    date: str
    slot: str
    status: str
    reason: str
    createdAt: str


class AppointmentCreateRequest(BaseModel):
    patientName: str = Field(..., min_length=1)
    patientPhone: str = Field(..., min_length=1)
    doctorId: str = Field(..., min_length=1)
    date: str = Field(..., description="Appointment date, e.g. 2026-08-25")
    slot: str = Field(..., description="Appointment time slot, e.g. 09:00")
    reason: Optional[str] = ""
