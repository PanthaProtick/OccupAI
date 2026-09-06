from __future__ import annotations

import re

from backend.assistant.parser import AssistantIntent, AssistantQueryPlan, AssistantSort
from backend.models import AssistantResult


def _natural_room_key(room: AssistantResult) -> tuple[tuple[int, object], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", room.name)
        if part
    )


def _reference(results: list[AssistantResult], reference: str | None) -> AssistantResult | None:
    if not reference:
        return None
    target = reference.casefold()
    return next(
        (room for room in results if room.name.casefold() == target or room.room_id.casefold() == target),
        None,
    )


def _block_distance(left: str, right: str) -> int:
    order = {"A": 0, "B": 1, "C": 2}
    if left not in order or right not in order:
        return 3
    return abs(order[left] - order[right])


def _context_key(room: AssistantResult, source: AssistantResult | None) -> tuple[int, int, int, int]:
    if source is None:
        return (0, 0, 0, 0)
    return (
        0 if room.building == source.building else 1,
        0 if room.floor == source.floor else 1,
        _block_distance(room.block, source.block),
        abs(room.floor - source.floor),
    )


def _general_key(
    room: AssistantResult,
    plan: AssistantQueryPlan,
    source: AssistantResult | None,
) -> tuple:
    context = _context_key(room, source)
    natural = _natural_room_key(room)
    if plan.sort is AssistantSort.HIGHEST_OCCUPANCY:
        return (-room.occupancy_percentage, -room.available_capacity, *context, natural)
    if plan.sort is AssistantSort.HIGHEST_AVAILABLE_CAPACITY:
        return (-room.available_capacity, room.occupancy_percentage, *context, natural)
    if plan.sort is AssistantSort.ROOM_NUMBER:
        return (*context, natural)
    return (room.occupancy_percentage, -room.available_capacity, *context, natural)


def _reason(plan: AssistantQueryPlan, source: AssistantResult | None) -> str:
    if plan.intent is AssistantIntent.FIND_NEARBY_ALTERNATIVE and source:
        return f"Lower-occupancy alternative near {source.name}, based on a fresh online reading."
    if plan.intent is AssistantIntent.FIND_ROOM_FOR_GROUP:
        return "Meets the requested available-capacity requirement with a fresh online reading."
    if plan.intent is AssistantIntent.IDENTIFY_CROWDED_ROOMS:
        return "One of the highest reliable occupancy readings in the requested area."
    if plan.intent in {
        AssistantIntent.FIND_AVAILABLE_ROOMS,
        AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS,
    }:
        return "One of the lowest reliable occupancy readings in the requested area."
    return "Fresh online reading that matches the requested filters."


def rank_query_results(
    candidates: list[AssistantResult],
    plan: AssistantQueryPlan,
) -> list[AssistantResult]:
    """Deterministically rank trusted candidates and apply the bounded plan limit."""
    source = _reference(candidates, plan.room_reference)
    ranked_candidates = list(candidates)

    if plan.intent is AssistantIntent.FIND_NEARBY_ALTERNATIVE:
        if source is None and plan.room_reference:
            return []
        if source is None and ranked_candidates:
            source = max(
                ranked_candidates,
                key=lambda room: (room.occupancy_percentage, -room.available_capacity, _natural_room_key(room)),
            )
        if source is None:
            return []
        ranked_candidates = [
            room for room in ranked_candidates
            if room.room_id != source.room_id
            and room.occupancy_percentage < source.occupancy_percentage
        ]
        ranked_candidates.sort(key=lambda room: (
            0 if room.building == source.building else 1,
            0 if room.floor == source.floor else 1,
            _block_distance(room.block, source.block),
            0 if room.occupancy_percentage < 40 else 1,
            room.occupancy_percentage,
            -room.available_capacity,
            _natural_room_key(room),
        ))
    else:
        ranked_candidates.sort(key=lambda room: _general_key(room, plan, source))

    reason = _reason(plan, source)
    return [room.model_copy(update={"reason": reason}) for room in ranked_candidates[:plan.limit]]
