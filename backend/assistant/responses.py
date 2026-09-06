from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.assistant.parser import AssistantIntent, AssistantQueryPlan
from backend.models import AssistantResult
from backend.assistant.safety import SAFE_SCOPE_RESPONSE


@dataclass(frozen=True)
class AssistantResponseContent:
    answer: str
    warnings: list[str]


def _floor_label(floor: int) -> str:
    return "Ground Floor" if floor == 0 else f"Floor {floor}"


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _filter_summary(plan: AssistantQueryPlan) -> str:
    parts: list[str] = []
    if plan.buildings:
        parts.append("building " + ", ".join(plan.buildings))
    if plan.floors:
        parts.append("floors " + ", ".join(_floor_label(floor) for floor in plan.floors))
    if plan.blocks:
        parts.append("blocks " + ", ".join(f"{block} Block" for block in plan.blocks))
    if plan.maximum_occupancy_percentage is not None:
        parts.append(f"below {_number(plan.maximum_occupancy_percentage)}% occupancy")
    if plan.minimum_occupancy_percentage is not None:
        parts.append(f"above {_number(plan.minimum_occupancy_percentage)}% occupancy")
    if plan.minimum_available_capacity is not None:
        parts.append(f"at least {plan.minimum_available_capacity} available seats")
    return "; ".join(parts) if parts else "all monitored campus rooms"


def _intro(plan: AssistantQueryPlan, count: int) -> str:
    scope = _filter_summary(plan)
    if plan.intent is AssistantIntent.IDENTIFY_CROWDED_ROOMS:
        return f"Based on the latest reliable readings, these are the {count} busiest matches for {scope}:"
    if plan.intent is AssistantIntent.FIND_ROOM_FOR_GROUP:
        return f"I found {count} current room option(s) matching {scope}:"
    if plan.intent is AssistantIntent.FIND_NEARBY_ALTERNATIVE:
        return f"I found {count} lower-occupancy nearby alternative(s) matching {scope}:"
    if plan.intent is AssistantIntent.COMPARE_ROOMS:
        return f"Here is the current comparison for {scope}:"
    if plan.intent is AssistantIntent.EXPLAIN_ROOM_STATUS:
        return "Here is the room's latest reliable occupancy status:"
    return f"Here are the {count} best current room option(s) matching {scope}:"


def compose_assistant_response(
    plan: AssistantQueryPlan,
    results: list[AssistantResult],
    data_timestamp: datetime,
) -> AssistantResponseContent:
    """Compose grounded prose exclusively from validated plan and result fields."""
    if plan.safety_refusal:
        return AssistantResponseContent(
            SAFE_SCOPE_RESPONSE,
            ["That request is outside the assistant's safe, read-only campus occupancy scope."],
        )
    if plan.clarification_question:
        return AssistantResponseContent(plan.clarification_question, ["No room query was executed."])
    if plan.intent is AssistantIntent.UNSUPPORTED:
        return AssistantResponseContent(
            SAFE_SCOPE_RESPONSE,
            ["No room query was executed."],
        )
    if not results:
        return AssistantResponseContent(
            f"I could not find a room with a fresh online reading matching {_filter_summary(plan)}. "
            "Offline, stale, disabled, missing, or otherwise unreliable readings are never presented as available.",
            ["No reliable matching rooms are currently available."],
        )

    lines = [_intro(plan, len(results))]
    for index, room in enumerate(results, start=1):
        lines.append(
            f"{index}. {room.name} — {_number(room.occupancy_percentage)}% occupied "
            f"({_floor_label(room.floor)}, {room.block} Block). "
            f"{room.occupancy} of {room.capacity} seats are currently occupied, leaving approximately "
            f"{room.available_capacity} available. {room.reason} Latest reading: {_timestamp(room.observed_at)}."
        )
    lines.append(
        f"These suggestions use the latest reliable OccupAI data available at {_timestamp(data_timestamp)}. "
        "Occupancy can change, so availability is not guaranteed."
    )
    warnings = (
        [f"Only {len(results)} reliable matches were available."]
        if len(results) < plan.limit else []
    )
    return AssistantResponseContent("\n\n".join(lines), warnings)
