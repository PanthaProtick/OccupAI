from __future__ import annotations

import re

from backend.assistant.architecture import AssistantOccupancySource, AssistantRoomSnapshot
from backend.assistant.parser import AssistantIntent, AssistantQueryPlan
from backend.models import AssistantResult, CameraStatus


def room_block(snapshot: AssistantRoomSnapshot) -> str:
    for value in (snapshot.room.name, snapshot.room.room_id):
        match = re.search(r"(?:^|_)(?:room_)?\d+([abc])\d+", value.lower())
        if match:
            return match.group(1).upper()
    return "Shared"


def _is_trusted(snapshot: AssistantRoomSnapshot) -> bool:
    room = snapshot.room
    occupancy = snapshot.occupancy
    return bool(
        snapshot.camera_enabled and snapshot.is_fresh and snapshot.observed_at is not None
        and occupancy.status is CameraStatus.ONLINE
        and occupancy.room_id == room.room_id and occupancy.camera_id == room.camera_id
        and occupancy.capacity == room.capacity
        and occupancy.occupancy is not None and room.capacity > 0
        and 0 <= occupancy.occupancy <= room.capacity
    )


def _matches(snapshot: AssistantRoomSnapshot, plan: AssistantQueryPlan) -> bool:
    room = snapshot.room
    occupancy_value = snapshot.occupancy.occupancy
    assert occupancy_value is not None
    percentage = occupancy_value * 100 / room.capacity
    available = room.capacity - occupancy_value
    block = room_block(snapshot)
    if plan.buildings and room.building.casefold() not in {value.casefold() for value in plan.buildings}:
        return False
    if plan.floors and room.floor not in plan.floors:
        return False
    if plan.blocks and block not in plan.blocks:
        return False
    if plan.maximum_occupancy_percentage is not None and percentage >= plan.maximum_occupancy_percentage:
        return False
    if plan.minimum_occupancy_percentage is not None and percentage <= plan.minimum_occupancy_percentage:
        return False
    if plan.minimum_available_capacity is not None and available < plan.minimum_available_capacity:
        return False
    if plan.intent in {AssistantIntent.COMPARE_ROOMS, AssistantIntent.EXPLAIN_ROOM_STATUS}:
        references = {value.casefold() for value in plan.room_references}
        if references and room.name.casefold() not in references:
            return False
    return True


def execute_query_plan(source: AssistantOccupancySource, plan: AssistantQueryPlan) -> list[AssistantResult]:
    """Return trusted matching candidates in repository order, without ranking."""
    results: list[AssistantResult] = []
    for snapshot in source.list_assistant_snapshots():
        if not _is_trusted(snapshot) or not _matches(snapshot, plan):
            continue
        room = snapshot.room
        occupancy = snapshot.occupancy.occupancy
        assert occupancy is not None and snapshot.observed_at is not None
        results.append(AssistantResult(
            room_id=room.room_id, name=room.name, building=room.building, floor=room.floor,
            block=room_block(snapshot), capacity=room.capacity, occupancy=occupancy,
            occupancy_percentage=round(occupancy * 100 / room.capacity, 2),
            available_capacity=room.capacity - occupancy, status=CameraStatus.ONLINE,
            observed_at=snapshot.observed_at,
            reason="Fresh online reading that matches the requested filters.",
        ))
    return results
