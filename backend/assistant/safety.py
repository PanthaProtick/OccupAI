from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


SAFE_SCOPE_RESPONSE = (
    "I can help with OccupAI room availability, occupancy, floor maps, "
    "and campus space recommendations."
)


@dataclass(frozen=True)
class AssistantSafetyDecision:
    blocked: bool
    category: str | None = None


_BLOCKED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction_extraction", re.compile(
        r"\b(?:reveal|show|print|repeat|expose|leak|give me)\b.{0,45}\b(?:system|developer|hidden|internal)\s+(?:prompt|message|instruction)s?\b"
        r"|\bignore\b.{0,35}\b(?:previous|prior|system|developer)\b.{0,25}\binstruction",
    )),
    ("secret_extraction", re.compile(
        r"\b(?:reveal|show|print|expose|leak|give me|list|read)\b.{0,55}\b(?:api[\s_-]*keys?|environment\s+variables?|env\s+vars?|credentials?|secrets?|authorization\s+headers?|database\s+(?:url|credentials?))\b",
    )),
    ("authentication_bypass", re.compile(
        r"\b(?:bypass|override|disable|evade|break)\b.{0,40}\b(?:auth(?:entication|orization)?|access\s+control|permissions?|csrf|session)\b"
        r"|\b(?:another|other)\s+user(?:'s|s')?\b.{0,45}\b(?:profile|conversation|history|notifications?|account|data)\b",
    )),
    ("sensitive_account_data", re.compile(
        r"\b(?:reveal|show|print|expose|leak|give me|list|read)\b.{0,55}\b(?:password\s+hash(?:es)?|session\s+tokens?|cookies?|token\s+hash(?:es)?)\b",
    )),
    ("database_operation", re.compile(
        r"\b(?:execute|run)\b.{0,20}\b(?:sql|query)\b|\b(?:drop|alter|truncate)\s+table\b|"
        r"\b(?:insert\s+into|update\s+\w+\s+set|delete\s+from|select\s+.+\s+from)\b|"
        r"\b(?:modify|write|delete|overwrite)\b.{0,35}\b(?:database|records?|occupancy\s+data)\b",
    )),
    ("unsafe_tool_request", re.compile(
        r"\b(?:execute|run|open)\b.{0,25}\b(?:shell|terminal|command\s+prompt|powershell)\b|"
        r"\b(?:curl|wget)\b\s+https?://|\binstall\b.{0,25}\b(?:plugin|package|tool)\b",
    )),
    ("factual_manipulation", re.compile(
        r"\b(?:fabricate|invent|make\s+up|fake)\b.{0,35}\b(?:room|occupancy|availability|data)\b|"
        r"\bmark\b.{0,30}\b(?:offline|stale|unavailable|disabled)\b.{0,25}\b(?:available|free|online)\b",
    )),
)

_STORAGE_SECRET = re.compile(
    r"(?i)\b(password|passcode|api[\s_-]*key|access[\s_-]*token|session[\s_-]*token|authorization)\b\s*(?:is|=|:)?\s*[\"']?([^\s,;\"']+)",
)


def _normalized(message: str) -> str:
    value = unicodedata.normalize("NFKC", message).casefold()
    value = "".join(character for character in value if not unicodedata.category(character).startswith("C"))
    return " ".join(value.split())


def inspect_assistant_message(message: str) -> AssistantSafetyDecision:
    """Classify explicit attempts to cross the assistant's read-only product boundary."""
    normalized = _normalized(message)
    for category, pattern in _BLOCKED_PATTERNS:
        if pattern.search(normalized):
            return AssistantSafetyDecision(True, category)
    return AssistantSafetyDecision(False)


def sanitize_assistant_message_for_storage(message: str) -> str:
    """Remove credential-shaped values before persistent conversation storage."""
    return _STORAGE_SECRET.sub(lambda match: f"{match.group(1)} [REDACTED]", message)
