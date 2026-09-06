from __future__ import annotations

import re
from enum import StrEnum

from pydantic import Field

from backend.models import ApiModel
from backend.assistant.safety import inspect_assistant_message


class AssistantIntent(StrEnum):
    FIND_AVAILABLE_ROOMS = "find_available_rooms"
    FIND_LEAST_OCCUPIED_ROOMS = "find_least_occupied_rooms"
    FIND_ROOM_FOR_GROUP = "find_room_for_group"
    FIND_ROOMS_BY_FLOOR = "find_rooms_by_floor"
    FIND_ROOMS_BY_BLOCK = "find_rooms_by_block"
    FIND_NEARBY_ALTERNATIVE = "find_nearby_alternative"
    IDENTIFY_CROWDED_ROOMS = "identify_crowded_rooms"
    COMPARE_ROOMS = "compare_rooms"
    EXPLAIN_ROOM_STATUS = "explain_room_status"
    UNSUPPORTED = "unsupported"


class AssistantSort(StrEnum):
    LOWEST_OCCUPANCY = "lowest_occupancy"
    HIGHEST_OCCUPANCY = "highest_occupancy"
    HIGHEST_AVAILABLE_CAPACITY = "highest_available_capacity"
    ROOM_NUMBER = "room_number"


class AssistantQueryPlan(ApiModel):
    intent: AssistantIntent
    buildings: list[str] = Field(default_factory=list)
    floors: list[int] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    room_reference: str | None = None
    room_references: list[str] = Field(default_factory=list, max_length=10)
    maximum_occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    minimum_occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    minimum_available_capacity: int | None = Field(default=None, ge=1)
    limit: int = Field(default=3, ge=1, le=10)
    sort: AssistantSort = AssistantSort.LOWEST_OCCUPANCY
    clarification_question: str | None = None
    safety_refusal: bool = False


_FLOOR_WORDS = {
    "ground": 0,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _floors(text: str) -> list[int]:
    values: set[int] = set()
    for word, floor in _FLOOR_WORDS.items():
        if re.search(rf"\b{word}(?:\s+floor)?\b", text):
            values.add(floor)
    for value in re.findall(r"\bfloor\s*(\d{1,2})\b", text):
        values.add(int(value))
    for value in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)\s+floor\b", text):
        values.add(int(value))
    return sorted(values)


def _limit(text: str) -> int:
    match = re.search(
        r"\b(?:top|best|first)\s+(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        text,
    )
    if not match:
        return 3
    raw = match.group(1)
    value = _NUMBER_WORDS.get(raw, int(raw) if raw.isdigit() else 3)
    return max(1, min(value, 10))


def _percentage(text: str, direction: str) -> float | None:
    prefixes = (
        r"below|under|less\s+than|at\s+most|no\s+more\s+than|max(?:imum)?"
        if direction == "maximum"
        else r"above|over|more\s+than|at\s+least|min(?:imum)?"
    )
    match = re.search(
        rf"\b(?:{prefixes})\s*(\d{{1,3}}(?:\.\d+)?)\s*(?:%(?!\w)|percent\b)",
        text,
    )
    if not match:
        return None
    return min(float(match.group(1)), 100.0)


def _minimum_capacity(text: str) -> int | None:
    patterns = (
        r"\bfor\s+(\d{1,4})\s+(?:people|persons?|students?|seats?)\b",
        r"\b(?:fit|fits|hold|holds|seat|seats)\s+(\d{1,4})\b",
        r"\b(?:available\s+)?capacity\s+(?:of\s+|for\s+|at\s+least\s+)?(\d{1,4})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return max(1, int(match.group(1)))
    return None


def _room_references(text: str) -> list[str]:
    references = {
        match.upper() for match in re.findall(r"\b(?:room\s*)?(\d{1,2}[abc]\d{2})\b", text)
    }
    return sorted(references)


def _buildings(text: str) -> list[str]:
    # The current canonical fixture uses this building. More canonical names can
    # be supplied by the query engine in Module 4 without loosening this parser.
    return ["University Building"] if "university building" in text else []


def parse_assistant_query(message: str) -> AssistantQueryPlan:
    """Convert a normalized user message into a bounded, non-executable plan."""
    if inspect_assistant_message(message).blocked:
        return AssistantQueryPlan(intent=AssistantIntent.UNSUPPORTED, safety_refusal=True)
    text = " ".join(message.lower().split())
    floors = _floors(text)
    blocks = sorted(set(re.findall(r"\b([abc])\s*block\b|\bblock\s*([abc])\b", text)))
    # The alternation above returns pairs; flatten only the populated group.
    normalized_blocks = sorted({part.upper() for pair in blocks for part in pair if part})
    references = _room_references(text)
    maximum = _percentage(text, "maximum")
    minimum = _percentage(text, "minimum")
    capacity = _minimum_capacity(text)

    available = any(word in text for word in ("free", "quiet", "available", "availability"))
    least = bool(re.search(r"\b(?:least\s+occupied|lowest\s+occupancy|quietest)\b", text))
    alternative = any(word in text for word in ("alternative", "nearby", "avoid crowded"))
    crowded = bool(re.search(r"\b(?:crowded|busiest|busy|high(?:est)?\s+occupancy)\b", text)) or minimum is not None
    compare = bool(re.search(r"\b(?:compare|versus|vs\.?|difference\s+between)\b", text))
    status = bool(re.search(r"\b(?:status|how\s+(?:full|busy)|occupancy\s+(?:of|in))\b", text))
    most_capacity = bool(re.search(
        r"\b(?:most\s+(?:free|available)\s+(?:capacity|seats?)|highest\s+available\s+capacity)\b",
        text,
    ))

    clarification = None
    sort = AssistantSort.LOWEST_OCCUPANCY
    if compare:
        intent = AssistantIntent.COMPARE_ROOMS
        sort = AssistantSort.ROOM_NUMBER
        if len(references) < 2:
            clarification = "Which two rooms would you like me to compare?"
    elif alternative:
        intent = AssistantIntent.FIND_NEARBY_ALTERNATIVE
    elif references and (status or available):
        intent = AssistantIntent.EXPLAIN_ROOM_STATUS
    elif crowded:
        intent = AssistantIntent.IDENTIFY_CROWDED_ROOMS
        sort = AssistantSort.HIGHEST_OCCUPANCY
    elif capacity is not None:
        intent = AssistantIntent.FIND_ROOM_FOR_GROUP
        sort = AssistantSort.HIGHEST_AVAILABLE_CAPACITY
    elif least:
        intent = AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS
    elif available:
        intent = AssistantIntent.FIND_AVAILABLE_ROOMS
    elif normalized_blocks:
        intent = AssistantIntent.FIND_ROOMS_BY_BLOCK
        sort = AssistantSort.ROOM_NUMBER
    elif floors:
        intent = AssistantIntent.FIND_ROOMS_BY_FLOOR
        sort = AssistantSort.ROOM_NUMBER
    elif "floor" in text:
        intent = AssistantIntent.FIND_ROOMS_BY_FLOOR
        sort = AssistantSort.ROOM_NUMBER
        clarification = "Which floor should I search: Ground Floor, Floor 1, or another floor?"
    else:
        intent = AssistantIntent.UNSUPPORTED

    if most_capacity and intent is not AssistantIntent.UNSUPPORTED:
        sort = AssistantSort.HIGHEST_AVAILABLE_CAPACITY

    return AssistantQueryPlan(
        intent=intent,
        buildings=_buildings(text),
        floors=floors,
        blocks=normalized_blocks,
        room_reference=references[0] if references else None,
        room_references=references,
        maximum_occupancy_percentage=maximum,
        minimum_occupancy_percentage=minimum,
        minimum_available_capacity=capacity,
        limit=_limit(text),
        sort=sort,
        clarification_question=clarification,
    )
