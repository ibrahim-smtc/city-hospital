"""
routers/chat.py
---------------
API endpoint for hospital chatbot / AI assistant.

Endpoint:
  POST /chat  — send a chat message and receive an assistant response
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter

from models import ChatRequest, ChatResponse  # type: ignore # pyrefly: ignore [missing-import]

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send chat message",
    description=(
        "Send a message to the hospital assistant / chatbot. "
        "Processes inquiries about doctors, appointments, services, and hospital information."
    ),
)
def chat_endpoint(request: ChatRequest):
    """
    Process incoming chat inquiry and return response.
    """
    msg_lower = request.message.strip().lower()
    
    if any(w in msg_lower for w in ["book", "appointment", "schedule"]):
        reply = "You can easily book an appointment by clicking 'Find a Doctor' in the menu, choosing your specialist, and selecting an available time slot!"
    elif any(w in msg_lower for w in ["status", "check", "cancel", "delete"]):
        reply = "To check or manage an existing appointment, head to the 'Check Status' tab and enter your Appointment ID (e.g. APPT-1001) or phone number."
    elif any(w in msg_lower for w in ["doctor", "specialist", "cardiologist", "neurologist", "pediatric"]):
        reply = "We have top specialists in Cardiology, Orthopedics, Neurology, and Pediatrics. Head over to 'Find a Doctor' to view schedules and qualifications!"
    elif any(w in msg_lower for w in ["hour", "time", "timing", "open", "emergency"]):
        reply = "New Care Med Center provides 24/7 emergency care and round-the-clock patient support. Doctor consultation timings vary by specialist."
    elif any(w in msg_lower for w in ["service", "clinic", "specialt"]):
        reply = "You can browse all hospital departments and specialized support clinics under the 'Specialties & Services' section."
    else:
        reply = "Thank you for reaching out to New Care Med Center! We're here to assist you with appointments, doctors, and hospital services."

    return ChatResponse(
        success=True,
        reply=reply,
        session_id=request.session_id,
    )

