"""
notification_service.py
-----------------------
Handles outbound webhook notifications for the City Hospital system.

Currently supports one event:
  - notify_consultation_complete: fires after a doctor marks a consultation done.

Sends a POST request to the Perfox webhook URL configured in the environment.
The secret is sent as an X-Webhook-Secret header.

Environment variables (loaded via python-dotenv):
  EMAIL_WEBHOOK_URL    -- full URL of the Perfox webhook endpoint
  EMAIL_WEBHOOK_SECRET -- secret sent as X-Webhook-Secret header
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

_WEBHOOK_URL = os.getenv("EMAIL_WEBHOOK_URL", "")
_WEBHOOK_SECRET = os.getenv("EMAIL_WEBHOOK_SECRET", "")

logger = logging.getLogger(__name__)


def notify_consultation_complete(
    patient_email: str,
    patient_name: str,
    doctor_name: str,
    labs_ordered: bool,
    imaging_ordered: bool,
    meds_prescribed: bool,
    billing_pending: bool,
    followup_needed: bool,
) -> tuple[bool, str | None]:
    """
    Fire a Perfox webhook notification when a consultation is marked complete.

    Sends a POST to EMAIL_WEBHOOK_URL with the seven fields as a flat JSON body
    and X-Webhook-Secret header set to EMAIL_WEBHOOK_SECRET.

    Returns:
        (True, None)       -- webhook returned HTTP 200.
        (False, error_str) -- any other status code or network exception;
                              never raises.
    """
    if not _WEBHOOK_URL:
        msg = "EMAIL_WEBHOOK_URL is not configured"
        logger.warning(msg)
        return False, msg

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": _WEBHOOK_SECRET,
    }

    body = {
        "patient_email": patient_email,
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "labs_ordered": labs_ordered,
        "imaging_ordered": imaging_ordered,
        "meds_prescribed": meds_prescribed,
        "billing_pending": billing_pending,
        "followup_needed": followup_needed,
    }

    try:
        resp = requests.post(_WEBHOOK_URL, json=body, headers=headers, timeout=10)
        if resp.status_code == 200:
            logger.info("Webhook delivered successfully (status=200)")
            return True, None
        else:
            msg = f"Webhook returned status {resp.status_code}: {resp.text[:200]}"
            logger.warning(msg)
            return False, msg
    except requests.exceptions.RequestException as exc:
        msg = f"Webhook request failed: {exc}"
        logger.error(msg)
        return False, msg
