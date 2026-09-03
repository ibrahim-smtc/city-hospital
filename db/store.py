"""
store.py
--------
Data access layer for the Hospital Demo API.

All data lives in a PostgreSQL database (Supabase), connection details
are read from DATABASE_URL in the .env file.

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
    delete_appointment(appt_id)        -> deleted appointment dict or None
"""

import json
import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load DATABASE_URL from .env (no-op if already set in the environment)
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")


# ===========================================================================
#  DATABASE CONNECTION HELPER
# ===========================================================================

def _get_connection() -> psycopg2.extensions.connection:
    """
    Create a new psycopg2 connection to the PostgreSQL database.
    Rows are returned as RealDictRow objects (behave like dicts),
    matching the sqlite3.Row behaviour the rest of the code relies on.
    """
    return psycopg2.connect(DATABASE_URL)


def _cursor(conn):
    """Return a RealDictCursor so rows come back as dict-like objects."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _row_to_dict(row) -> dict:
    """Convert a RealDictRow (or any mapping) to a plain Python dict."""
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
    cur = _cursor(conn)

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

    # If a department filter is provided, add a WHERE clause.
    # Using ILIKE for case-insensitive partial matching.
    if department:
        query += " WHERE d.department ILIKE %s"
        params.append(f"%{department}%")

    query += " ORDER BY d.id"

    cur.execute(query, params)
    rows = cur.fetchall()

    doctors = []
    for row in rows:
        doc = _row_to_dict(row)
        # Parse the JSON lists for days and slots
        doc["available_days"] = json.loads(doc["available_days"]) if doc["available_days"] else []
        doc["available_slots"] = json.loads(doc["available_slots"]) if doc["available_slots"] else []
        doctors.append(doc)

    cur.close()
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
    cur = _cursor(conn)

    # --- Get the main doctor row ---
    cur.execute(
        """
        SELECT
            d.id, d.slug, d.name, d.designation, d.department,
            d.description, d.experience_years, d.hospital_branch,
            da.available_days, da.available_slots
        FROM doctors d
        LEFT JOIN doctor_availability da ON da.doctor_id = d.id
        WHERE d.id = %s
        """,
        (doctor_id,),
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return None

    doctor = _row_to_dict(row)
    doctor["available_days"] = json.loads(doctor["available_days"]) if doctor["available_days"] else []
    doctor["available_slots"] = json.loads(doctor["available_slots"]) if doctor["available_slots"] else []

    # --- Fetch related lists ---
    # Helper: run a simple SELECT and return a flat list of values
    def _fetch_list(table: str, column: str) -> list[str]:
        cur.execute(
            f"SELECT {column} FROM {table} WHERE doctor_id = %s",
            (doctor_id,),
        )
        return [r[column] for r in cur.fetchall()]

    doctor["qualifications"] = _fetch_list("doctor_qualifications", "qualification")
    doctor["expertise"] = _fetch_list("doctor_expertise", "area")
    doctor["memberships"] = _fetch_list("doctor_memberships", "membership")
    doctor["achievements"] = _fetch_list("doctor_achievements", "achievement")
    doctor["publications"] = _fetch_list("doctor_publications", "publication")

    cur.close()
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
    cur = _cursor(conn)
    cur.execute("SELECT id, slug, name, description FROM specialties ORDER BY name")
    rows = cur.fetchall()
    cur.close()
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
    cur = _cursor(conn)
    cur.execute("SELECT id, slug, name, type, description FROM services ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ===========================================================================
#  APPOINTMENTS
# ===========================================================================

def _generate_appointment_id(cur) -> str:
    """
    Generate the next appointment ID in the format APPT-1001, APPT-1002, etc.
    Looks at the highest existing numeric suffix to determine the next number.
    """
    cur.execute(
        "SELECT id FROM appointments ORDER BY created_at DESC, id DESC LIMIT 1"
    )
    row = cur.fetchone()

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
    cur = _cursor(conn)

    try:
        # Step 1: Check doctor exists
        cur.execute(
            "SELECT d.id, d.name FROM doctors d WHERE d.id = %s",
            (data["doctor_id"],),
        )
        doctor = cur.fetchone()

        if not doctor:
            raise ValueError("DOCTOR_NOT_FOUND")

        # Step 2: Validate the time slot
        cur.execute(
            "SELECT available_slots FROM doctor_availability WHERE doctor_id = %s",
            (data["doctor_id"],),
        )
        avail = cur.fetchone()

        if avail:
            available_slots = json.loads(avail["available_slots"])
            if data["slot"] not in available_slots:
                raise ValueError(f"INVALID_SLOT|{json.dumps(available_slots)}")

        # Step 3: Check for double-booking
        cur.execute(
            """
            SELECT id FROM appointments
            WHERE doctor_id = %s
              AND date = %s
              AND slot = %s
              AND status != 'cancelled'
            """,
            (data["doctor_id"], data["date"], data["slot"]),
        )
        if cur.fetchone():
            raise ValueError("SLOT_ALREADY_BOOKED")

        # Step 4: Insert the appointment
        appt_id = _generate_appointment_id(cur)
        created_at = datetime.now(timezone.utc).isoformat()

        cur.execute(
            """
            INSERT INTO appointments
                (id, patient_name, patient_phone, doctor_id, date, slot, status, reason, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
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
        cur.execute("SELECT * FROM appointments WHERE id = %s", (appt_id,))
        appointment = _row_to_dict(cur.fetchone())

        # Add doctor name for convenience
        appointment["doctor_name"] = doctor["name"]

        return appointment

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_appointment_by_id(appointment_id: str) -> dict | None:
    """
    Fetch a single appointment by its ID (e.g. 'APPT-1001').
    Joins with the doctors table to include the doctor's name.
    Returns None if not found.
    """
    conn = _get_connection()
    cur = _cursor(conn)
    cur.execute(
        """
        SELECT
            a.*,
            d.name AS doctor_name,
            d.department
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.id = %s
        """,
        (appointment_id,),
    )
    row = cur.fetchone()
    cur.close()
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
    cur = _cursor(conn)

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
        query += " AND a.patient_phone = %s"
        params.append(phone)

    if appointment_id:
        query += " AND a.id = %s"
        params.append(appointment_id)

    query += " ORDER BY a.created_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
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
    cur = _cursor(conn)

    try:
        # Fetch the appointment first so we can return its details
        cur.execute(
            """
            SELECT
                a.*,
                d.name AS doctor_name,
                d.department
            FROM appointments a
            JOIN doctors d ON d.id = a.doctor_id
            WHERE a.id = %s
            """,
            (appointment_id,),
        )
        row = cur.fetchone()

        if not row:
            return None

        appointment = _row_to_dict(row)

        # Delete the appointment
        cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()

        return appointment

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
