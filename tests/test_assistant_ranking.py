from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.assistant import parse_assistant_query, rank_query_results
from backend.models import AssistantResult, CameraStatus


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def result(
    name: str,
    percentage: float,
    available: int,
    *,
    building: str = "University Building",
    floor: int = 2,
    block: str | None = None,
) -> AssistantResult:
    resolved_block = block or name[1]
    capacity = 40
    occupancy = capacity - available
    return AssistantResult(
        room_id=f"room_{name.lower()}", name=name, building=building, floor=floor,
        block=resolved_block, capacity=capacity, occupancy=occupancy,
        occupancy_percentage=percentage, available_capacity=available,
        status=CameraStatus.ONLINE, observed_at=NOW, reason="candidate",
    )


class AssistantRankingTests(unittest.TestCase):
    def test_available_rooms_rank_by_percentage_then_capacity_then_room_number(self):
        candidates = [
            result("2A10", 25, 30), result("2A02", 10, 20),
            result("2A01", 10, 30), result("2A03", 10, 30),
        ]
        ranked = rank_query_results(candidates, parse_assistant_query("top 4 available rooms"))
        self.assertEqual([room.name for room in ranked], ["2A01", "2A03", "2A02", "2A10"])

    def test_default_and_explicit_limits_are_applied(self):
        candidates = [result(f"2A0{index}", index, 40 - index) for index in range(1, 7)]
        self.assertEqual(len(rank_query_results(candidates, parse_assistant_query("available rooms"))), 3)
        self.assertEqual(len(rank_query_results(candidates, parse_assistant_query("top 5 available rooms"))), 5)

    def test_group_search_prefers_highest_available_capacity(self):
        candidates = [result("2A01", 10, 20), result("2A02", 20, 35), result("2A03", 5, 30)]
        ranked = rank_query_results(candidates, parse_assistant_query("find a room for 20 people"))
        self.assertEqual([room.name for room in ranked], ["2A02", "2A03", "2A01"])

    def test_crowded_search_ranks_highest_percentage_first(self):
        candidates = [result("2A01", 82, 5), result("2A02", 95, 2), result("2A03", 88, 4)]
        ranked = rank_query_results(candidates, parse_assistant_query("crowded rooms"))
        self.assertEqual([room.name for room in ranked], ["2A02", "2A03", "2A01"])

    def test_nearby_alternative_excludes_source_and_requires_lower_occupancy(self):
        source = result("2A03", 85, 6)
        candidates = [
            result("2A01", 35, 26),
            result("2B01", 20, 32),
            result("3A01", 10, 36, floor=3),
            result("2A09", 5, 38, building="Engineering Annex"),
            result("2C01", 15, 34),
            source,
            result("2A04", 90, 4),
        ]
        ranked = rank_query_results(
            candidates, parse_assistant_query("top 5 nearby alternatives to 2A03")
        )
        self.assertEqual(
            [room.name for room in ranked],
            ["2A01", "2B01", "2C01", "3A01", "2A09"],
        )
        self.assertNotIn("2A03", [room.name for room in ranked])
        self.assertTrue(all(room.occupancy_percentage < 85 for room in ranked))

    def test_unknown_explicit_source_produces_no_unjustified_alternative(self):
        ranked = rank_query_results(
            [result("2A01", 10, 36)],
            parse_assistant_query("find an alternative to 9A99"),
        )
        self.assertEqual(ranked, [])

    def test_fewer_matches_are_returned_without_padding(self):
        ranked = rank_query_results(
            [result("2A01", 10, 36)], parse_assistant_query("top 3 available rooms")
        )
        self.assertEqual([room.name for room in ranked], ["2A01"])


if __name__ == "__main__":
    unittest.main()
