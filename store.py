"""
store.py
--------
Data access layer for the Hospital Demo API.

All data lives in a single SQLite database (data/hospital.db).
Each function opens a short-lived connection, runs the query,
and returns plain Python dicts — no ORM, no magic.

Functions:
  Doctors:
    get_all_doctors(department=None)   -> list of doctor dicts
    get_doctor_by_id(doctor_id)        -> single doctor dict or None

  Specialties & Services:
    get_all_specialties()              -> list of specialty dicts
    get_all_services()                 -> list of service dicts

  Appointments:
    create_appointment(data)           -> new appointment dict
    get_appointment_by_id(appt_id)     -> single appointment dict or None
    list_appointments(phone, appt_id)  -> list of appointment dicts
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Path to the SQLite database
DB_PATH = Path(__file__).parent / "data" / "hospital.db"


# ===========================================================================
#  DATABASE CONNECTION HELPER
# ===========================================================================

def _get_connection() -> sqlite3.Connection:
    """
    Create a new SQLite connection with row_factory set to sqlite3.Row
    so we can access columns by name (like a dict).
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # lets us do row["column_name"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain Python dict."""
    return dict(row)


# ===========================================================================
#  DOCTORS
# ===========================================================================

def get_all_doctors(department: str = None) -> list[dict]:
    """
    Fetch all doctors, optionally filtered by department.

    Each doctor dict includes: id, slug, name, designation, department,
    description, experience_years, available_days, available_slots.
    """
    conn = _get_connection()

    # Base query: join doctors with their availability
    query = """
        SELECT
            d.id,
            d.slug,
            d.name,
            d.designation,
            d.department,
            d.description,
            d.experience_years,
            d.hospital_branch,
            da.available_days,
            da.available_slots
        FROM doctors d
        LEFT JOIN doctor_availability da ON da.doctor_id = d.id
    """
    params = []

    # If a department filter is provided, add a WHERE clause
    # Using LIKE for partial matching (e.g. "Cardiology" matches "Interventional Cardiologist")
    if department:
        query += " WHERE d.department LIKE ?"
        params.append(f"%{department}%")

    query += " ORDER BY d.id"

    rows = conn.execute(query, params).fetchall()
    doctors = []
    for row in rows:
        doc = _row_to_dict(row)
        # Parse the JSON lists for days and slots
        doc["available_days"] = json.loads(doc["available_days"]) if doc["available_days"] else []
        doc["available_slots"] = json.loads(doc["available_slots"]) if doc["available_slots"] else []
        doctors.append(doc)

    conn.close()
    return doctors


def get_doctor_by_id(doctor_id: int) -> dict | None:
    """
    Fetch a single doctor by ID, including:
    - basic info (name, designation, department, etc.)
    - available days & time slots
    - qualifications, expertise, memberships, achievements, publications

    Returns None if the doctor is not found.
    """
    conn = _get_connection()

    # --- Get the main doctor row ---
    row = conn.execute(
        """
        SELECT
            d.id, d.slug, d.name, d.designation, d.department,
            d.description, d.experience_years, d.hospital_branch,
            da.available_days, da.available_slots
        FROM doctors d
        LEFT JOIN doctor_availability da ON da.doctor_id = d.id
        WHERE d.id = ?
        """,
        (doctor_id,),
    ).fetchone()

    if not row:
        conn.close()
        return None

    doctor = _row_to_dict(row)
    doctor["available_days"] = json.loads(doctor["available_days"]) if doctor["available_days"] else []
    doctor["available_slots"] = json.loads(doctor["available_slots"]) if doctor["available_slots"] else []

    # --- Fetch related lists ---
    # Helper: run a simple SELECT and return a flat list of values
    def _fetch_list(table: str, column: str) -> list[str]:
        rows = conn.execute(
            f"SELECT {column} FROM {table} WHERE doctor_id = ?",
            (doctor_id,),
        ).fetchall()
        return [r[0] for r in rows]

    doctor["qualifications"] = _fetch_list("doctor_qualifications", "qualification")
    doctor["expertise"] = _fetch_list("doctor_expertise", "area")
    doctor["memberships"] = _fetch_list("doctor_memberships", "membership")
    doctor["achievements"] = _fetch_list("doctor_achievements", "achievement")
    doctor["publications"] = _fetch_list("doctor_publications", "publication")

    conn.close()
    return doctor


# ===========================================================================
#  SPECIALTIES
# ===========================================================================

def get_all_specialties() -> list[dict]:
    """
    Fetch all hospital specialties (e.g. Cardiology, Neurology).
    Returns: list of dicts with id, slug, name, description.
    """
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, slug, name, description FROM specialties ORDER BY name"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ===========================================================================
#  SERVICES
# ===========================================================================

def get_all_services() -> list[dict]:
    """
    Fetch all support services and clinics (e.g. Diabetes Clinic, Blood Center).
    Returns: list of dicts with id, slug, name, type, description.
    """
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, slug, name, type, description FROM services ORDER BY name"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ===========================================================================
#  APPOINTMENTS
# ===========================================================================

def _generate_appointment_id(conn: sqlite3.Connection) -> str:
    """
    Generate the next appointment ID in the format APPT-1001, APPT-1002, etc.
    Looks at the highest existing ID to determine the next number.
    """
    row = conn.execute(
        "SELECT id FROM appointments ORDER BY ROWID DESC LIMIT 1"
    ).fetchone()

    if row is None:
        # No appointments yet, start at 1001
        return "APPT-1001"

    # Extract the number from the last ID (e.g. "APPT-1005" -> 1005)
    try:
        last_num = int(row["id"].split("-")[1])
    except (IndexError, ValueError):
        last_num = 1000

    return f"APPT-{last_num + 1}"


def create_appointment(data: dict) -> dict:
    """
    Book a new appointment.

    Steps:
    1. Check that the doctor exists
    2. Validate the slot is in the doctor's available slots
    3. Check for double-booking (same doctor + date + slot, non-cancelled)
    4. Insert and return the new appointment

    Parameters:
        data: dict with keys: patient_name, patient_phone, doctor_id, date, slot, reason

    Returns:
        The newly created appointment dict

    Raises:
        ValueError: with a descriptive message if validation fails
    """
    conn = _get_connection()

    # Step 1: Check doctor exists
    doctor = conn.execute(
        "SELECT d.id, d.name FROM doctors d WHERE d.id = ?",
        (data["doctor_id"],),
    ).fetchone()

    if not doctor:
        conn.close()
        raise ValueError("DOCTOR_NOT_FOUND")

    # Step 2: Validate the time slot
    avail = conn.execute(
        "SELECT available_slots FROM doctor_availability WHERE doctor_id = ?",
        (data["doctor_id"],),
    ).fetchone()

    if avail:
        available_slots = json.loads(avail["available_slots"])
        if data["slot"] not in available_slots:
            conn.close()
            raise ValueError(f"INVALID_SLOT|{json.dumps(available_slots)}")

    # Step 3: Check for double-booking
    conflict = conn.execute(
        """
        SELECT id FROM appointments
        WHERE doctor_id = ?
          AND date = ?
          AND slot = ?
          AND status != 'cancelled'
        """,
        (data["doctor_id"], data["date"], data["slot"]),
    ).fetchone()

    if conflict:
        conn.close()
        raise ValueError("SLOT_ALREADY_BOOKED")

    # Step 4: Insert the appointment
    appt_id = _generate_appointment_id(conn)
    created_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO appointments
            (id, patient_name, patient_phone, doctor_id, date, slot, status, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            appt_id,
            data["patient_name"],
            data["patient_phone"],
            data["doctor_id"],
            data["date"],
            data["slot"],
            data.get("reason", ""),
            created_at,
        ),
    )
    conn.commit()

    # Fetch the newly created appointment to return it
    appointment = _row_to_dict(conn.execute(
        "SELECT * FROM appointments WHERE id = ?", (appt_id,)
    ).fetchone())

    # Add doctor name for convenience
    appointment["doctor_name"] = doctor["name"]

    conn.close()
    return appointment


def get_appointment_by_id(appointment_id: str) -> dict | None:
    """
    Fetch a single appointment by its ID (e.g. 'APPT-1001').
    Joins with the doctors table to include the doctor's name.
    Returns None if not found.
    """
    conn = _get_connection()
    row = conn.execute(
        """
        SELECT
            a.*,
            d.name AS doctor_name,
            d.department
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    conn.close()

    if not row:
        return None
    return _row_to_dict(row)


def list_appointments(
    phone: str = None,
    appointment_id: str = None,
) -> list[dict]:
    """
    List appointments with optional filters.

    Filters:
    - phone:          match by patient_phone
    - appointment_id: match by appointment id

    Returns a list of appointment dicts, each including doctor_name.
    """
    conn = _get_connection()

    query = """
        SELECT
            a.*,
            d.name AS doctor_name,
            d.department
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE 1=1
    """
    params = []

    if phone:
        query += " AND a.patient_phone = ?"
        params.append(phone)

    if appointment_id:
        query += " AND a.id = ?"
        params.append(appointment_id)

    query += " ORDER BY a.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [_row_to_dict(r) for r in rows]


def delete_appointment(appointment_id: str) -> dict | None:
    """
    Delete an appointment by its ID (e.g. 'APPT-1001').

    Steps:
    1. Fetch the appointment (with doctor info) so we can return it
    2. Delete it from the database
    3. Return the deleted appointment dict

    Returns None if the appointment doesn't exist.
    """
    conn = _get_connection()

    # Fetch the appointment first so we can return its details
    row = conn.execute(
        """
        SELECT
            a.*,
            d.name AS doctor_name,
            d.department
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if not row:
        conn.close()
        return None

    appointment = _row_to_dict(row)

    # Delete the appointment
    conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    return appointment
