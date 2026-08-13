"""
sensitive.py
------------
Part 3: Sensitive Information Detection.

Approach: deterministic regex matching against known sensitive value shapes
(OTP, password, card number, bank account number, recovery code, ID number,
access token, home address, private phone contact). Regex over ML here
because these values follow fixed, well-defined formats — a pattern match
is both more accurate and fully explainable than a trained classifier for
this task, and it lets us guarantee no sensitive value is ever logged
unmasked (see mask_value()).

Each detector returns: sensitivity_type, risk, masked_text, recommended_action.
"""
import re

# (name, compiled regex, risk level, recommended_action, reason)
# Order matters: more specific patterns first.
SENSITIVE_PATTERNS = [
    (
        "one_time_password",
        re.compile(r"\bOTP is\s+([\d-]+)", re.I),
        "high",
        "do_not_store",
        "Message contains a one-time password (OTP) value.",
    ),
    (
        "password",
        re.compile(r"\bpassword\s+([A-Za-z0-9#\-]+)\s+to sign in", re.I),
        "high",
        "do_not_store",
        "Message contains a plaintext login password.",
    ),
    (
        "payment_card_number",
        re.compile(r"\bcard number is\s+([\d ]{10,}-?\d*)", re.I),
        "high",
        "do_not_send_to_external_service",
        "Message contains a payment card number.",
    ),
    (
        "bank_account_number",
        re.compile(r"\bbank account number\s+([\d-]+)", re.I),
        "high",
        "do_not_send_to_external_service",
        "Message contains a bank account number.",
    ),
    (
        "auth_token",
        re.compile(r"\baccess token is\s+([A-Za-z0-9_\-]+)", re.I),
        "high",
        "do_not_store",
        "Message contains a temporary authentication/access token.",
    ),
    (
        "account_recovery_code",
        re.compile(r"\baccount recovery code is\s+([A-Za-z0-9\-]+)", re.I),
        "high",
        "do_not_store",
        "Message contains an account recovery code.",
    ),
    (
        "identification_number",
        re.compile(r"\bidentification number is\s+([A-Za-z0-9\-]+)", re.I),
        "medium",
        "ask_for_confirmation",
        "Message contains a personal identification number.",
    ),
    (
        "home_address",
        re.compile(r"\bhome address is\s+(.+?)(?:\.|$)", re.I),
        "medium",
        "ask_for_confirmation",
        "Message contains a private home address.",
    ),
    (
        "private_phone_contact",
        re.compile(r"\byou can contact me on\s+([\d \-]+)", re.I),
        "medium",
        "ask_for_confirmation",
        "Message contains a private phone number for direct contact.",
    ),
    (
        "health_information",
        re.compile(r"\btest result says\s+(.+?)(?:\.|$)", re.I),
        "medium",
        "ask_for_confirmation",
        "Message contains a personal health/medical detail.",
    ),
]


def mask_value(raw: str) -> str:
    """Mask a captured sensitive value, keeping only a short non-identifying hint."""
    raw = raw.strip()
    if len(raw) <= 4:
        return "*" * len(raw)
    # Keep first 2 characters as a shape hint (e.g. "RC-...", "ID-...") and mask the rest.
    visible = raw[:2]
    return visible + "*" * (len(raw) - 2)


def detect_sensitive(message_id: str, text: str):
    """
    Return a sensitive-info finding dict if the message matches a known
    sensitive pattern, else None. Only the FIRST matching pattern is used —
    in this dataset each sensitive message carries exactly one sensitive
    value, and using the first match keeps the output deterministic.
    """
    for sensitivity_type, pattern, risk, action, reason in SENSITIVE_PATTERNS:
        m = pattern.search(text)
        if m:
            raw_value = m.group(1)
            masked_full_text = text[: m.start(1)] + mask_value(raw_value) + text[m.end(1):]
            return {
                "message_id": message_id,
                "sensitivity_type": sensitivity_type,
                "risk": risk,
                "masked_text": masked_full_text,
                "recommended_action": action,
                "reason": reason,
            }
    return None
