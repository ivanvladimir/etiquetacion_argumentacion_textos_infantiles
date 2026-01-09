from datetime import datetime, timezone
import humanize
from typing import Any

def naturaltime(value: Any) -> str:
    if value is None:
        return "N/A"

    # If already a datetime
    if isinstance(value, datetime):
        dt = value

    # If ISO string
    elif isinstance(value, str):
        try:
            # Handle Zulu time
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(value)
        except ValueError:
            return "N/A"

    else:
        return "N/A"

    # Ensure timezone-aware (humanize expects this to be sane)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return humanize.naturaltime(dt)
