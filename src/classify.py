"""
classify.py
-----------
Part 1: Message Classification into 6 categories:
Action Required, Meeting or Event, Personal Information,
General Information, Promotional, Sensitive Information.

Approach
--------
Inspecting the dataset shows every message is generated from a small set
of ~60 content templates, each optionally wrapped in one of 8 "noise"
prefixes (e.g. "For today:", "FYI:", "Important:", "Just checking—").
The prefixes are distributed EVENLY across all templates (90 each) — i.e.
they carry no category signal at all. This is a deliberate trap: a naive
classifier that keys off words like "Important:" will misfire, because
"Important:" is glued onto trivial status updates just as often as onto
real tasks.

So the strategy is:
  1. Strip the known noise prefix (if any) to get the core sentence.
  2. Run the core sentence through ordered regex rule groups, most
     specific/highest-stakes category first:
       Sensitive Information -> Meeting or Event -> Action Required
       -> Promotional -> Personal Information -> General Information (fallback)
  3. Sensitive Information is checked first because a message that both
     requests an action AND contains a password, for example, must still
     be flagged as sensitive above all else.

Every rule carries a human-readable reason template so Part 1's output
always explains itself, and a confidence score reflecting how specific
the matched pattern is (fixed template phrase = high confidence; the
General Information fallback = lower confidence since it's "nothing else
matched" rather than a positive signal).
"""
import re
from sensitive import detect_sensitive

NOISE_PREFIXES = [
    "For today: ", "FYI: ", "One more thing: ", "Important: ",
    "Just checking—", "Please note: ", "Quick update: ", "Personal note: ",
    "Can you help? ", "Hi, ",
]


def strip_noise_prefix(text: str):
    """Strip noise prefixes iteratively — some messages stack two, e.g.
    'Can you help? Personal note: ...'. Returns (core_text, list_of_prefixes_removed)."""
    removed = []
    changed = True
    while changed:
        changed = False
        for p in NOISE_PREFIXES:
            if text.startswith(p):
                text = text[len(p):]
                removed.append(p.strip(" :—?"))
                changed = True
                break
    return text, (removed or None)


MEETING_PATTERNS = [
    re.compile(r"\bcalendar update:", re.I),
    re.compile(r"\breminder:.*\bhappens on\b", re.I),
    re.compile(r"\bare you available for\b.*\bat\b.*\bon\b", re.I),
    re.compile(r"\bplease join the\b.*\bon\b.*,\s*\d{1,2}:\d{2}", re.I),
    re.compile(r"\bis scheduled for\b.*\bat\b.*\bin\b", re.I),
]

ACTION_PATTERNS = [
    re.compile(r"\bcan you\b.*\b(before|by)\b\s+\d{4}-\d{2}-\d{2}", re.I),
    re.compile(r"\bi need you to\b.*\bby\b\s+\d{4}-\d{2}-\d{2}", re.I),
    re.compile(r"\bdon'?t forget to\b.*\bdeadline is\b\s+\d{4}-\d{2}-\d{2}", re.I),
    re.compile(r"\bplease (complete|confirm|reply|submit)\b.*\b(by|before)\b\s+\d{4}-\d{2}-\d{2}", re.I),
    re.compile(r"^\w[\w ]+ is due on\s+\d{4}-\d{2}-\d{2}", re.I),
    re.compile(r"^\w[\w ]+ is due on\s+\d{4}-\d{2}-\d{2}", re.I),
]

PROMO_PATTERNS = [
    re.compile(r"\buse code\s+SAVE\w*", re.I),
    re.compile(r"\b(discount|flash sale|cashback|reward points|free delivery|premium plan|subscription|coupon)\b", re.I),
]

PERSONAL_PATTERNS = [
    re.compile(r"\bfor my profile,\b", re.I),
    re.compile(r"\bremember that\b", re.I),
    re.compile(r"\bjust so you know,\b", re.I),
    re.compile(r"\bmy emergency contact is\b", re.I),
    re.compile(r"\bmy favourite\b", re.I),
    re.compile(r"\bi (prefer|usually|drink|use|live|am)\b", re.I),
]


def classify_message(message_id: str, text: str):
    core, prefix_used = strip_noise_prefix(text)

    # 1. Sensitive Information takes priority over every other label.
    sensitive_hit = detect_sensitive(message_id, core)
    if sensitive_hit:
        return {
            "message_id": message_id,
            "category": "sensitive_information",
            "confidence": 0.97,
            "reason": sensitive_hit["reason"] + " Sensitive content overrides any other category.",
        }

    # 2. Meeting or Event
    for pat in MEETING_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "meeting_or_event",
                "confidence": 0.93,
                "reason": "Message names a specific date/time and location for a meeting or event.",
            }

    # 3. Action Required
    for pat in ACTION_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "action_required",
                "confidence": 0.9,
                "reason": "Message asks the recipient to complete a task by a stated deadline.",
            }
    # Softer action cue: "before DATE" / "by DATE" anywhere, imperative-ish sentence, no meeting/time.
    if re.search(r"\b(before|by|deadline is|due on)\b\s+\d{4}-\d{2}-\d{2}", core, re.I):
        return {
            "message_id": message_id,
            "category": "action_required",
            "confidence": 0.85,
            "reason": "Message references a deadline date tied to completing a task.",
        }

    # 4. Promotional
    for pat in PROMO_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "promotional",
                "confidence": 0.92,
                "reason": "Message advertises a discount/offer and includes a promo code or sales language.",
            }

    # 5. Personal Information
    for pat in PERSONAL_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "personal_information",
                "confidence": 0.85,
                "reason": "Message shares a personal preference or profile detail about the sender, not classified as sensitive.",
            }

    # 6. Fallback: General Information
    return {
        "message_id": message_id,
        "category": "general_information",
        "confidence": 0.6,
        "reason": "Message is a neutral status update or FYI with no action, schedule, promo, or personal/sensitive content detected.",
    }
