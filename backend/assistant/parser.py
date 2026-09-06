from __future__ import annotations

import re
from difflib import SequenceMatcher
from enum import StrEnum

from pydantic import Field

from backend.models import ApiModel
from backend.assistant.safety import inspect_assistant_message


class AssistantIntent(StrEnum):
    WEBSITE_HELP = "website_help"
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
    help_answer: str | None = None
    crowding_comparison: str | None = None
    is_recommendation: bool = False


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
    # Support the named spaces users naturally ask about, not only coded rooms.
    aliases = (
        (r"\b(?:the\s+)?canteen\b", "Canteen"),
        (r"\bteacher'?s\s+canteen\b", "Teacher's Canteen"),
        (r"\bgirls'?\s+common\s+room\b", "Girls' Common Room"),
        (r"\bt\.?t\.?\s+ground\b", "T.T. Ground"),
        (r"\b(?:tt|t\.?t\.?)\b", "T.T. Ground"),
        (r"\b(?:study\s+room|study\s+space|study)\b", "Study Room"),
        (r"\b(?:library|libary|lib)\b", "Library"),
    )
    matched_named = [(pattern, name) for pattern, name in aliases if re.search(pattern, text)]
    if any(name == "Teacher's Canteen" for _, name in matched_named):
        matched_named = [(pattern, name) for pattern, name in matched_named if name != "Canteen"]
    references.update(name for _, name in matched_named)

    # Be forgiving with small spelling mistakes and shorthand. Compare short
    # word windows to the canonical room vocabulary, then use the canonical
    # name for the trusted query engine.
    fuzzy_names = {"canteen": "Canteen", "library": "Library", "study": "Study Room"}
    words = re.findall(r"[a-z0-9]+", text)
    windows = {" ".join(words[index:index + size]) for size in (1, 2, 3) for index in range(len(words) - size + 1)}
    for candidate in windows:
        for phrase, name in fuzzy_names.items():
            if len(candidate) >= 4 and SequenceMatcher(None, candidate, phrase).ratio() >= .78:
                references.add(name)
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

    available = any(word in text for word in ("free", "quiet", "quieter", "calm", "peaceful", "vacant", "available", "availability", "empty", "less crowded", "fewer people", "less people", "less person"))
    # A bare recommendation is still a room-discovery request. Keep this
    # scoped to room/space nouns so unrelated prompts such as "suggest a poem"
    # remain unsupported rather than accidentally executing a room query.
    recommendation = bool(re.search(
        r"\b(?:suggest|recommend|recommendation)\b.*\b(?:room|rooms|space|spaces)\b"
        r"|\b(?:room|rooms|space|spaces)\b.*\b(?:suggest|recommend|recommendation)\b",
        text,
    )) or bool(re.search(r"\b(?:where|which|should)\b.*\b(?:go|choose|pick)\b|\bplace\s+to\s+go\b", text))
    least = bool(re.search(r"\b(?:least\s+occupied|lowest\s+occupancy|quietest|least\s+busy|not\s+busy|(?:most\s+)?less\s+crowded|least\s+crowded)\b", text))
    alternative = any(word in text for word in ("alternative", "nearby", "avoid crowded"))
    crowded = not least and (
        bool(re.search(r"\b(?:crowded|packed|full|busiest|busy|high(?:est)?\s+occupancy)\b", text))
        or minimum is not None
    )
    compare = bool(re.search(r"\b(?:compare|versus|vs\.?|difference\s+between)\b", text)) or (
        len(references) >= 2 and bool(re.search(r"\b(?:or|and)\b", text))
    )
    status = bool(re.search(r"\b(?:status|condition|state|how\s+(?:full|busy)|occupancy\s+(?:of|in)|how\s+is)\b", text))
    capacity_question = bool(re.search(r"\b(?:cap\w{3,}|seating\s+limit|how\s+many\s+(?:people|students|seats?)|how\s+much\s+space)\b", text))
    crowding_comparison = (
        "less" if re.search(r"\b(?:less|fewer|few|quiet|quieter|calm|peaceful)\b", text)
        else "many" if re.search(r"\b(?:many|more|crowded|busy|packed|full)\b", text)
        else None
    )
    location_question = bool(re.search(r"\b(?:where\s+is|where\s+can\s+i\s+find|which\s+floor|which\s+block)\b", text))
    most_capacity = bool(re.search(
        r"\b(?:most\s+(?:free|available)\s+(?:capacity|seats?)|highest\s+available\s+capacity)\b",
        text,
    ))

    help_answer = None
    if re.search(r"\b(?:what is occupai|what does occupai do|how does occupai work|what can this website do)\b", text):
        help_answer = "OccupAI is a campus space-intelligence website. It shows live room occupancy, capacity, availability, floor maps, room details, history, alerts, and recommendations so you can find a suitable space quickly."
    elif re.search(r"\b(?:how do i use|how can i use|what is the overview|what does the overview)\b", text):
        help_answer = "Use Overview for the campus summary and live insights, Floor map to explore rooms by floor and block, Rooms to inspect individual spaces, and AI Assistant to ask about availability, occupancy, capacity, and alternatives."
    elif re.search(r"\b(?:what is the floor map|how does the floor map|explain the floor map)\b", text):
        help_answer = "The floor map shows monitored rooms grouped by A, B, and C Block. Use the floor and block filters, then select a room to view its latest occupancy and history."
    elif re.search(r"\b(?:what are notifications|how do notifications|what is the bell|alerts)\b", text):
        help_answer = "Notifications highlight important occupancy changes and high-demand spaces. You can review them from the bell icon and manage notification preferences from your profile."
    elif re.search(r"\b(?:what can you answer|what can the assistant|what questions can you ask)\b", text):
        help_answer = "I can answer questions about current room availability, occupancy, capacity, floors, A/B/C Blocks, room status, quiet or busy spaces, nearby alternatives, comparisons, floor maps, notifications, and how to use OccupAI."
    elif re.search(r"\b(?:is this live|is this real[- ]time|how current|when was the data|how often.*update|last updated)\b", text):
        help_answer = "OccupAI answers from the latest trusted readings available to the system. Each result shows its data time, and rooms with stale, offline, or unreliable readings are not presented as currently available."
    elif re.search(r"\b(?:opening hours|open|close|closing time|when does.*open)\b", text):
        help_answer = "OccupAI currently tracks room occupancy, capacity, availability, and location. Opening hours are not part of the available campus data, so I cannot reliably confirm them yet."
    elif re.search(r"\b(?:history|historical|trend|over time|last week|yesterday)\b", text):
        help_answer = "Open a room from the floor map or room directory to view its occupancy history and trend chart. The chart includes averages, peaks, coverage, and selectable time ranges when data is available."
    elif re.search(r"\b(?:private|privacy|identify people|track people|security)\b", text):
        help_answer = "OccupAI is designed around privacy: it uses occupancy counts and space signals rather than identifying individuals. Authentication uses a protected session, and the assistant only returns verified campus-space information."

    clarification = None
    sort = AssistantSort.LOWEST_OCCUPANCY
    if help_answer:
        intent = AssistantIntent.WEBSITE_HELP
    elif compare:
        intent = AssistantIntent.COMPARE_ROOMS
        sort = AssistantSort.ROOM_NUMBER
        if len(references) < 2:
            clarification = "Which two rooms would you like me to compare?"
    elif alternative:
        intent = AssistantIntent.FIND_NEARBY_ALTERNATIVE
    elif references and (status or available or capacity_question or location_question):
        intent = AssistantIntent.EXPLAIN_ROOM_STATUS
    elif crowded:
        intent = AssistantIntent.IDENTIFY_CROWDED_ROOMS
        sort = AssistantSort.HIGHEST_OCCUPANCY
    elif capacity is not None:
        intent = AssistantIntent.FIND_ROOM_FOR_GROUP
        sort = AssistantSort.HIGHEST_AVAILABLE_CAPACITY
    elif least:
        intent = AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS
    elif maximum is not None:
        # A bounded occupancy request is itself a complete room-search intent,
        # even when the user does not also say "available" or "quiet".
        intent = AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS
    elif not references and any(phrase in text for phrase in ("less crowded", "fewer people", "less people", "less person")):
        intent = AssistantIntent.UNSUPPORTED
        clarification = "I can compare how crowded a space is. Which room should I check, such as Canteen, Library, or T.T. Ground?"
    elif available or recommendation:
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
    elif status or any(phrase in text for phrase in ("less crowded", "fewer people", "less people", "less person")):
        intent = AssistantIntent.UNSUPPORTED
        clarification = "I can compare how crowded a space is. Which room should I check, such as Canteen, Library, or T.T. Ground?"
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
        help_answer=help_answer,
        crowding_comparison=crowding_comparison,
        is_recommendation=recommendation,
    )
