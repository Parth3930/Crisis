import os
import logging
from datetime import datetime


LOG_PATH = os.path.join("uploads", "notifications.log")
os.makedirs("uploads", exist_ok=True)


def notify_emergency_locally(emergency_report) -> bool:
    try:
        entry = (
            f"[{datetime.utcnow().isoformat()}] EMERGENCY: {emergency_report.title} | "
            f"Severity: {getattr(emergency_report, 'severity', 'unknown')} | "
            f"UserID: {getattr(emergency_report, 'user_id', 'unknown')} | "
            f"Location: {getattr(emergency_report, 'location', 'N/A')}\n"
        )
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        logging.info(f"Local notification logged: {entry.strip()}")
        return True
    except Exception as e:
        logging.error(f"Failed to write local notification: {e}")
        return False


