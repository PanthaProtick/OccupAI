from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.assistant import compose_assistant_response, parse_assistant_query
from backend.models import AssistantResult, CameraStatus


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def result(name: str, floor: int, occupancy: int, capacity: int) -> AssistantResult:
    percentage = round(occupancy * 100 / capacity, 2)
    return AssistantResult(
        room_id=f"room_{name.lower()}", name=name, building="University Building",
        floor=floor, block=name[1], capacity=capacity, occupancy=occupancy,
        occupancy_percentage=percentage, available_capacity=capacity - occupancy,
        status=CameraStatus.ONLINE, observed_at=NOW,
        reason="One of the lowest reliable occupancy readings in the requested area.",
    )


class AssistantResponseTests(unittest.TestCase):
    def test_answer_contains_only_grounded_room_facts_filters_and_freshness(self):
        plan = parse_assistant_query("top 3 free rooms on the ground and first floors below 40%")
        results = [result("1A02", 1, 6, 40), result("0B01", 0, 10, 50)]
        content = compose_assistant_response(plan, results, NOW)
        self.assertIn("Ground Floor, Floor 1", content.answer)
        self.assertIn("below 40% occupancy", content.answer)
        self.assertIn("1. 1A02 — 15% occupied", content.answer)
        self.assertIn("6 of 40 seats", content.answer)
        self.assertIn("approximately 34 available", content.answer)
        self.assertNotIn("2026-09-05T12:00:00Z", content.answer)
        self.assertIn("availability is not guaranteed", content.answer)
        self.assertNotIn("2A99", content.answer)
        self.assertEqual(content.warnings, ["Only 2 reliable matches were available."])

    def test_no_results_never_describes_unavailable_data_as_free(self):
        content = compose_assistant_response(parse_assistant_query("available rooms"), [], NOW)
        self.assertIn("could not find", content.answer)
        self.assertIn("Offline, stale, disabled, missing", content.answer)
        self.assertEqual(content.warnings, ["No reliable matching rooms are currently available."])

    def test_clarification_is_returned_without_room_claims(self):
        plan = parse_assistant_query("show rooms on the floor")
        content = compose_assistant_response(plan, [], NOW)
        self.assertEqual(content.answer, plan.clarification_question)
        self.assertEqual(content.warnings, ["No room query was executed."])

    def test_unsupported_request_stays_within_occupai_scope(self):
        content = compose_assistant_response(parse_assistant_query("write a poem"), [], NOW)
        self.assertEqual(
            content.answer,
            "I can help with OccupAI room availability, occupancy, floor maps, and campus space recommendations.",
        )

    def test_crowded_and_group_intros_match_the_factual_intent(self):
        crowded = compose_assistant_response(
            parse_assistant_query("rooms above 80%"), [result("2A03", 2, 36, 40)], NOW
        )
        group = compose_assistant_response(
            parse_assistant_query("room for 20 people"), [result("2B01", 2, 5, 40)], NOW
        )
        self.assertIn("busiest matches", crowded.answer)
        self.assertIn("at least 20 available seats", group.answer)


if __name__ == "__main__":
    unittest.main()
