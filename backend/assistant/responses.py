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
        return f"**Based on the latest reliable readings**, these are the **{count} busiest matches** for {scope}:"
    if plan.intent is AssistantIntent.FIND_ROOM_FOR_GROUP:
        return f"I found **{count} current room option(s)** matching {scope}:"
    if plan.intent is AssistantIntent.FIND_NEARBY_ALTERNATIVE:
        return f"I found **{count} lower-occupancy nearby alternative(s)** matching {scope}:"
    if plan.intent is AssistantIntent.COMPARE_ROOMS:
        return f"Here is the **current comparison** for {scope}:"
    if plan.intent is AssistantIntent.EXPLAIN_ROOM_STATUS:
        return "Here is the room's **latest reliable occupancy status**:"
    return f"Here are the **{count} best current room option(s)** matching {scope}:"


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
    if plan.intent is AssistantIntent.WEBSITE_HELP:
        return AssistantResponseContent(plan.help_answer or "I can explain the OccupAI website and its live campus features.", [])
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
    if plan.intent is AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS or (
        plan.is_recommendation and plan.intent is AssistantIntent.FIND_AVAILABLE_ROOMS
    ):
        recommendation = min(results, key=lambda room: (room.occupancy_percentage, -room.available_capacity, room.name.casefold()))
        lines.append(
            f"**Go to {recommendation.name}.** It is the least crowded suitable option right now at "
            f"**{_number(recommendation.occupancy_percentage)}% occupied**, with approximately "
            f"**{recommendation.available_capacity} seats available.**"
        )
    if plan.intent is AssistantIntent.COMPARE_ROOMS:
        recommendation = min(results, key=lambda room: (room.occupancy_percentage, -room.available_capacity, room.name.casefold()))
        lines.append(
            f"**Recommendation:** I suggest going to **{recommendation.name}** right now. It is the quieter option at "
            f"**{_number(recommendation.occupancy_percentage)}% occupied**, with approximately "
            f"**{recommendation.available_capacity} seats available.**"
        )
    if plan.intent is AssistantIntent.EXPLAIN_ROOM_STATUS and plan.crowding_comparison and results:
        lead = min(results, key=lambda room: room.occupancy_percentage)
        if plan.crowding_comparison == "less":
            lines.append(f"Yes — {lead.name} currently has relatively few people ({_number(lead.occupancy_percentage)}% occupied).")
        else:
            lines.append(f"It is currently fairly busy ({lead.name} is {_number(lead.occupancy_percentage)}% occupied).")
    for index, room in enumerate(results, start=1):
        capacity_sentence = (
            f"Capacity is {room.capacity} seats. "
            if plan.intent is AssistantIntent.EXPLAIN_ROOM_STATUS else ""
        )
        lines.append(
            f"**{index}. {room.name}** — **{_number(room.occupancy_percentage)}% occupied** "
            f"({_floor_label(room.floor)}, {room.block} Block). "
            f"{capacity_sentence}{room.occupancy} of {room.capacity} seats are currently occupied, leaving approximately "
            f"{room.available_capacity} available. {room.reason}"
        )
    lines.append(
        "These suggestions use the **latest reliable OccupAI data**. Occupancy can change, so availability is not guaranteed."
    )
    warnings = (
        [f"Only {len(results)} reliable matches were available."]
        if len(results) < plan.limit else []
    )
    return AssistantResponseContent("\n\n".join(lines), warnings)
