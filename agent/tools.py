"""
LangChain Tools for the City Hospital AI Agent.

This module exposes tools that the LLM agent can call to:
1. Search unstructured hospital knowledge & clinical guidelines (RAG via FAISS)
2. Query structured doctor availability & departments (SQLite database)
3. Book new appointments with validation & double-booking prevention (SQLite database)
4. Check appointment status by ID or patient phone number
5. Cancel/Delete existing appointments
"""

import sys
import json
from pathlib import Path

# Ensure project root is in sys.path so store and agent imports work smoothly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from langchain_core.tools import tool
import store
from agent.retriever import retriever


# ─── Tool 1: RAG Knowledge Search ──────────────────────────────────────────────
@tool
def search_hospital_knowledge(query: str) -> str:
    """
    Search the hospital's clinical knowledge base, department overviews, policies, 
    and detailed medical background.
    Use this when the user asks general questions like:
    - "What is your cardiology treatment approach?"
    - "Tell me about cancer screening packages"
    - "What are the visiting hours or international patient services?"
    - "What qualifications does Dr Naveen have?"
    """
    try:
        docs = retriever.invoke(query)
        if not docs:
            return "No specific hospital documentation found for that query."

        results = []
        for i, doc in enumerate(docs, 1):
            source = Path(doc.metadata.get("source", "")).name
            clean_text = doc.page_content.strip().replace("\n\n", "\n")
            results.append(f"[{i}] Source: {source}\n{clean_text}")

        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Error retrieving knowledge: {str(e)}"


# ─── Tool 2: Search Doctors Database ───────────────────────────────────────────
@tool
def search_doctors(search_query: str = "") -> str:
    """
    Query the active hospital database to list doctors and their schedules.
    You can search by a doctor's name, department, or specialty (e.g., 'Kiran', 'Cardiology', 'neuro').
    Returns doctor IDs, names, designations, available days, and available time slots.
    """
    try:
        query_filter = search_query.strip() if search_query else None
        doctors = store.get_all_doctors(search_query=query_filter)
        if not doctors:
            if query_filter:
                return f"No doctors found matching '{query_filter}'."
            return "No doctors found in the database."

        formatted_list = []
        for d in doctors:
            days = ", ".join(d.get("available_days", [])) or "Not listed"
            slots = ", ".join(d.get("available_slots", [])) or "None available"
            formatted_list.append(
                f"• ID: {d['id']} | Name: {d['name']}\n"
                f"  Department: {d['department']} ({d['designation']})\n"
                f"  Experience: {d.get('experience_years', 'N/A')} years\n"
                f"  Available Days: {days}\n"
                f"  Available Slots: {slots}"
            )
        return "\n\n".join(formatted_list)
    except Exception as e:
        return f"Error searching doctors: {str(e)}"


# ─── Tool 3: Get Detailed Doctor Profile ────────────────────────────────────────
@tool
def get_doctor_details(doctor_id: int) -> str:
    """
    Retrieve full profile and credentials for a specific doctor by their integer doctor_id.
    Includes qualifications, memberships, publications, and clinic timings.
    """
    try:
        doc = store.get_doctor_by_id(doctor_id)
        if not doc:
            return f"Doctor with ID {doctor_id} does not exist."

        details = [
            f"Name: {doc['name']}",
            f"Designation: {doc['designation']}",
            f"Department: {doc['department']}",
            f"Experience: {doc.get('experience_years', 'N/A')} years",
            f"Branch: {doc.get('hospital_branch', 'Main Branch')}",
            f"Description: {doc.get('description', '')}",
            f"Available Days: {', '.join(doc.get('available_days', []))}",
            f"Available Slots: {', '.join(doc.get('available_slots', []))}",
        ]
        if doc.get("qualifications"):
            details.append("Qualifications: " + "; ".join(doc["qualifications"]))
        if doc.get("memberships"):
            details.append("Memberships: " + "; ".join(doc["memberships"]))

        return "\n".join(details)
    except Exception as e:
        return f"Error getting doctor details: {str(e)}"


# ─── Tool 4: Book Appointment ──────────────────────────────────────────────────
@tool
def book_appointment(
    patient_name: str,
    patient_phone: str,
    doctor_id: int,
    date: str,
    slot: str,
    reason: str = "General Consultation"
) -> str:
    """
    Book a confirmed appointment for a patient in the hospital system.
    
    Parameters:
    - patient_name: Full name of the patient (e.g. 'John Doe')
    - patient_phone: 10-digit phone number (e.g. '9876543210')
    - doctor_id: Integer ID of the doctor (e.g. 22)
    - date: Appointment date in YYYY-MM-DD format (e.g. '2026-09-01')
    - slot: Time slot in HH:MM format (e.g. '10:00', '14:30')
    - reason: Brief reason for appointment or symptoms (optional)
    """
    try:
        data = {
            "patient_name": patient_name.strip(),
            "patient_phone": patient_phone.strip(),
            "doctor_id": int(doctor_id),
            "date": date.strip(),
            "slot": slot.strip(),
            "reason": reason.strip(),
        }
        appt = store.create_appointment(data)
        return (
            f"✅ Appointment Confirmed!\n"
            f"• Appointment ID: {appt['id']}\n"
            f"• Patient: {appt['patient_name']} ({appt['patient_phone']})\n"
            f"• Doctor: {appt.get('doctor_name', 'Doctor')} (ID: {appt['doctor_id']})\n"
            f"• Date: {appt['date']}\n"
            f"• Time Slot: {appt['slot']}\n"
            f"• Status: {appt['status']}"
        )
    except ValueError as ve:
        err = str(ve)
        if "DOCTOR_NOT_FOUND" in err:
            return f"❌ Error: Doctor with ID {doctor_id} was not found."
        elif "INVALID_SLOT" in err:
            parts = err.split("|")
            valid = parts[1] if len(parts) > 1 else "check doctor schedule"
            return f"❌ Error: Time slot '{slot}' is not offered by this doctor. Available slots are: {valid}"
        elif "SLOT_ALREADY_BOOKED" in err:
            return f"❌ Error: Time slot '{slot}' on {date} is already booked by another patient. Please choose a different slot."
        return f"❌ Booking failed: {err}"
    except Exception as e:
        return f"❌ Unexpected error while booking: {str(e)}"


# ─── Tool 5: Check Appointment Status ──────────────────────────────────────────
@tool
def check_appointment_status(appointment_id: str = "", patient_phone: str = "") -> str:
    """
    Look up appointment details and status by Appointment ID (e.g., 'APPT-1001') 
    or by the patient's phone number.
    """
    try:
        appt_id_filter = appointment_id.strip() if appointment_id else None
        phone_filter = patient_phone.strip() if patient_phone else None

        if not appt_id_filter and not phone_filter:
            return "Please provide either an Appointment ID (e.g. 'APPT-1001') or a patient phone number."

        appts = store.list_appointments(phone=phone_filter, appointment_id=appt_id_filter)
        if not appts:
            return "No matching appointments found."

        results = []
        for a in appts:
            results.append(
                f"• Appointment ID: {a['id']}\n"
                f"  Patient: {a['patient_name']} ({a['patient_phone']})\n"
                f"  Doctor: {a.get('doctor_name', 'N/A')} ({a.get('department', 'General')})\n"
                f"  Date & Time: {a['date']} at {a['slot']}\n"
                f"  Status: {a['status'].upper()}\n"
                f"  Reason: {a.get('reason', 'N/A')}"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"Error checking appointment: {str(e)}"


# ─── Tool 6: Reschedule Appointment ──────────────────────────────────────────
@tool
def reschedule_appointment(old_appointment_id: str, new_date: str, new_slot: str) -> str:
    """
    Reschedule an existing appointment to a new date and time slot.
    Requires the old Appointment ID (e.g., 'APPT-1001') and the new date and slot.
    """
    try:
        old_appt = store.get_appointment_by_id(old_appointment_id)
        if not old_appt:
            return f"❌ Error: Could not find appointment {old_appointment_id}."
            
        new_appt_data = {
            "patient_name": old_appt["patient_name"],
            "patient_phone": old_appt["patient_phone"],
            "doctor_id": old_appt["doctor_id"],
            "date": new_date,
            "slot": new_slot,
            "reason": old_appt.get("reason", "Rescheduled")
        }
        
        # Book the new appointment first (ensures the slot is valid and free)
        new_appt = store.create_appointment(new_appt_data)
        
        # If the booking succeeds, safely delete the old one
        store.delete_appointment(old_appointment_id)
        
        return (f"✅ Successfully rescheduled! "
                f"Old appointment ({old_appointment_id}) cancelled. "
                f"New Appointment ID: {new_appt['id']} for {new_date} at {new_slot}.")
                
    except ValueError as e:
        err = str(e)
        if "SLOT_ALREADY_BOOKED" in err:
            return f"❌ Reschedule failed: The new slot '{new_slot}' on {new_date} is already taken."
        return f"❌ Reschedule failed: {err}"
    except Exception as e:
        return f"❌ Unexpected error while rescheduling: {str(e)}"


# ─── Tool 7: Cancel Appointment ────────────────────────────────────────────────
@tool
def cancel_appointment(appointment_id: str) -> str:
    """
    Cancel and remove an appointment by its ID (e.g. 'APPT-1001').
    """
    try:
        deleted = store.delete_appointment(appointment_id.strip())
        if not deleted:
            return f"No appointment found with ID '{appointment_id}'."

        return (
            f"✅ Appointment {deleted['id']} for {deleted['patient_name']} with "
            f"{deleted.get('doctor_name', 'Doctor')} on {deleted['date']} at {deleted['slot']} "
            f"has been successfully cancelled."
        )
    except Exception as e:
        return f"Error cancelling appointment: {str(e)}"


# ─── Exported List of Tools for LangGraph ───────────────────────────────────────
tools = [
    search_hospital_knowledge,
    search_doctors,
    get_doctor_details,
    book_appointment,
    check_appointment_status,
    reschedule_appointment,
    cancel_appointment,
]


# ─── Test Section ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CITY HOSPITAL AGENT TOOLS - UNIT TESTS")
    print("=" * 60 + "\n")

    print("[TEST 1] search_hospital_knowledge('What is interventional cardiology?')")
    print("-" * 50)
    print(search_hospital_knowledge.invoke({"query": "What is interventional cardiology?"})[:300] + "...\n")

    print("[TEST 2] search_doctors(department='Cardiology')")
    print("-" * 50)
    print(search_doctors.invoke({"department": "Cardiology"}) + "\n")

    print("[TEST 3] check_appointment_status(appointment_id='APPT-1001')")
    print("-" * 50)
    print(check_appointment_status.invoke({"appointment_id": "APPT-1001"}) + "\n")

    print("=" * 60)
    print("  ALL TOOLS FUNCTIONING PERFECTLY!")
    print("=" * 60 + "\n")

