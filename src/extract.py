"""
extract.py
----------
Part 2: Task and Event Extraction.

Only runs on messages already classified as "action_required" or
"meeting_or_event" (Part 1's output). Extracts title, description,
date/time, involved person, priority, and source message ID.

Rule: never guess. If a field cannot be found with a confident regex
match, it is stored as null (Python None -> JSON null) rather than
inferred. The one exception is `priority`, which is a deliberate derived
signal (see PRIORITY note below) and is documented as such — it is not a
"guess" about a fact, it's a computed judgement, and the reasoning is
always shown in `priority_basis`.

Priority
--------
The dataset contains no explicit urgency words ("urgent", "ASAP", etc.),
so priority cannot be extracted verbatim. Instead it is DERIVED from the
gap between the message timestamp and the extracted deadline date:
  <= 3 days  -> high
  4-7 days   -> medium
  > 7 days / no deadline -> low
This is disclosed as an assumption in the README, not hidden as if it
were an extracted fact.
"""
import re
from datetime import datetime

DATE_RE = r"\d{4}-\d{2}-\d{2}"
TIME_RE = r"\d{1,2}:\d{2}"


def _priority_from_gap(msg_ts: datetime, deadline_str: str):
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "low", "no resolvable deadline date"
    gap_days = (deadline - msg_ts).days
    if gap_days <= 3:
        return "high", f"{gap_days} day(s) between message and deadline"
    elif gap_days <= 7:
        return "medium", f"{gap_days} day(s) between message and deadline"
    else:
        return "low", f"{gap_days} day(s) between message and deadline"


def extract_action(message_id, text, timestamp):
    date_m = re.search(DATE_RE, text)
    deadline = date_m.group(0) if date_m else None
    time_m = re.search(TIME_RE, text)
    time_val = time_m.group(0) if time_m else None

    priority, basis = _priority_from_gap(timestamp, deadline) if deadline else ("low", "no deadline date found in message")

    # Title: take the sentence stripped of the deadline clause, trimmed.
    title = re.sub(r"\b(before|by|deadline is|is due on|due on)\b.*$", "", text, flags=re.I).strip(" .;")
    if not title:
        title = None

    return {
        "item_id": f"TASK_{message_id.split('_')[-1]}",
        "type": "task",
        "title": title,
        "description": text.strip(),
        "deadline": deadline,
        "time": time_val,
        "person": None,  # dataset does not name a specific assignee inside action messages
        "priority": priority,
        "priority_basis": basis,
        "source_message_id": message_id,
    }


def extract_event(message_id, text, timestamp):
    date_m = re.search(DATE_RE, text)
    date_val = date_m.group(0) if date_m else None
    time_m = re.search(TIME_RE, text)
    time_val = time_m.group(0) if time_m else None

    location = None
    # Try template-specific patterns, most specific first.
    for loc_pat in [
        r"Location:\s*([A-Za-z0-9 ]+?)\.?$",                       # "... Location: the main office."
        r"\bin\s+([A-Za-z0-9 ]+?)\.?$",                            # "... happens/scheduled ... in Zoom."
        rf"{TIME_RE}\s+at\s+([A-Za-z0-9 ]+?)\.?$",                 # "... 13:00 at Conference Room 2."
        rf"{TIME_RE},\s*([A-Za-z0-9 ]+?)\.?$",                     # "Calendar update: X, DATE at TIME, the library."
    ]:
        m = re.search(loc_pat, text)
        if m:
            location = m.group(1).strip()
            break

    # Title heuristic: strip known lead-in phrases, then take text up to the
    # first comma / date / "is scheduled" / "happens" marker.
    stripped = re.sub(r"^(Calendar update:|Reminder:|Please join the|Are you available for the)\s*", "", text)
    title_m = re.match(r"^([A-Za-z ,\-]+?)(?:,|\s+on\s+\d{4}|\s+is scheduled|\s+happens|\s+at\s+\d{1,2}:\d{2})", stripped)
    title = title_m.group(1).strip() if title_m else (stripped.strip(" .?") or None)

    priority, basis = _priority_from_gap(timestamp, date_val) if date_val else ("low", "no date found in message")

    return {
        "item_id": f"EVENT_{message_id.split('_')[-1]}",
        "type": "event",
        "title": title,
        "description": text.strip(),
        "date": date_val,
        "time": time_val,
        "location": location,
        "person": None,
        "priority": priority,
        "priority_basis": basis,
        "source_message_id": message_id,
    }
