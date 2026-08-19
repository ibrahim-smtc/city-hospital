import json
from pathlib import Path
from typing import Any, List

DATA_DIR = Path(__file__).parent / "data"
DOCTORS_FILE = DATA_DIR / "doctors.json"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"


def _read_json(file_path: Path) -> Any:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(file_path: Path, data: Any) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_doctors() -> List[dict]:
    return _read_json(DOCTORS_FILE)


def get_appointments() -> List[dict]:
    return _read_json(APPOINTMENTS_FILE)


def save_appointments(appointments: List[dict]) -> None:
    _write_json(APPOINTMENTS_FILE, appointments)
