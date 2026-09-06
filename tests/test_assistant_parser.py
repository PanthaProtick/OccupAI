from __future__ import annotations

import unittest

from backend.assistant import AssistantIntent, AssistantSort, parse_assistant_query


class AssistantParserTests(unittest.TestCase):
    def test_ground_and_first_floors_are_recognized(self):
        plan = parse_assistant_query("Give me free spaces on the ground and first floors")
        self.assertEqual(plan.intent, AssistantIntent.FIND_AVAILABLE_ROOMS)
        self.assertEqual(plan.floors, [0, 1])
        self.assertEqual(plan.limit, 3)
        self.assertEqual(plan.sort, AssistantSort.LOWEST_OCCUPANCY)

    def test_numeric_ordinal_and_floor_number_are_recognized(self):
        self.assertEqual(parse_assistant_query("rooms on the 5th floor").floors, [5])
        self.assertEqual(parse_assistant_query("rooms on floor 2").floors, [2])

    def test_top_limit_is_parsed_and_server_bounded(self):
        self.assertEqual(parse_assistant_query("top three quiet rooms").limit, 3)
        self.assertEqual(parse_assistant_query("best 50 available rooms").limit, 10)
        self.assertEqual(parse_assistant_query("top 0 available rooms").limit, 1)

    def test_percentage_capacity_building_and_block_filters_are_structured(self):
        plan = parse_assistant_query(
            "Find the best 3 rooms in A Block in the University Building below 40 percent for 25 people"
        )
        self.assertEqual(plan.intent, AssistantIntent.FIND_ROOM_FOR_GROUP)
        self.assertEqual(plan.blocks, ["A"])
        self.assertEqual(plan.buildings, ["University Building"])
        self.assertEqual(plan.maximum_occupancy_percentage, 40)
        self.assertEqual(plan.minimum_available_capacity, 25)

    def test_nearby_alternative_extracts_room_reference(self):
        plan = parse_assistant_query("Find a quiet nearby alternative to room 2a03")
        self.assertEqual(plan.intent, AssistantIntent.FIND_NEARBY_ALTERNATIVE)
        self.assertEqual(plan.room_reference, "2A03")

    def test_crowded_rooms_use_highest_occupancy_sort(self):
        plan = parse_assistant_query("Which rooms are more than 80% occupied?")
        self.assertEqual(plan.intent, AssistantIntent.IDENTIFY_CROWDED_ROOMS)
        self.assertEqual(plan.minimum_occupancy_percentage, 80)
        self.assertEqual(plan.sort, AssistantSort.HIGHEST_OCCUPANCY)

    def test_maximum_occupancy_alone_is_a_low_occupancy_room_query(self):
        plan = parse_assistant_query("Show rooms below 40% occupancy.")
        self.assertEqual(plan.intent, AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS)
        self.assertEqual(plan.maximum_occupancy_percentage, 40)
        self.assertEqual(plan.sort, AssistantSort.LOWEST_OCCUPANCY)

    def test_comparison_requires_two_room_references(self):
        clear = parse_assistant_query("Compare 2A03 vs 2B04")
        self.assertEqual(clear.intent, AssistantIntent.COMPARE_ROOMS)
        self.assertEqual(clear.room_references, ["2A03", "2B04"])
        self.assertIsNone(clear.clarification_question)
        unclear = parse_assistant_query("Compare room 2A03")
        self.assertIn("Which two rooms", unclear.clarification_question or "")

    def test_unspecified_floor_asks_for_clarification(self):
        plan = parse_assistant_query("Show me rooms on the floor")
        self.assertEqual(plan.intent, AssistantIntent.FIND_ROOMS_BY_FLOOR)
        self.assertIn("Which floor", plan.clarification_question or "")

    def test_unrelated_question_is_unsupported(self):
        plan = parse_assistant_query("Write a poem about the moon")
        self.assertEqual(plan.intent, AssistantIntent.UNSUPPORTED)
        self.assertEqual(plan.floors, [])

    def test_room_recommendation_is_a_bounded_availability_query(self):
        for message in ("Suggest me a room", "Recommend a quiet space"):
            with self.subTest(message=message):
                plan = parse_assistant_query(message)
                self.assertEqual(plan.intent, AssistantIntent.FIND_AVAILABLE_ROOMS)
                self.assertIsNone(plan.clarification_question)

    def test_unscoped_suggestion_does_not_execute_a_room_query(self):
        self.assertEqual(
            parse_assistant_query("Suggest a poem").intent,
            AssistantIntent.UNSUPPORTED,
        )

    def test_every_declared_intent_has_a_deterministic_route(self):
        cases = {
            "Which rooms are available right now?": AssistantIntent.FIND_AVAILABLE_ROOMS,
            "Show the least occupied rooms": AssistantIntent.FIND_LEAST_OCCUPIED_ROOMS,
            "Find a room for 25 people": AssistantIntent.FIND_ROOM_FOR_GROUP,
            "Show rooms on Floor 2": AssistantIntent.FIND_ROOMS_BY_FLOOR,
            "Show rooms in C Block": AssistantIntent.FIND_ROOMS_BY_BLOCK,
            "Find a nearby alternative to 2A03": AssistantIntent.FIND_NEARBY_ALTERNATIVE,
            "Which rooms are crowded?": AssistantIntent.IDENTIFY_CROWDED_ROOMS,
            "Compare 2A03 versus 2B04": AssistantIntent.COMPARE_ROOMS,
            "Is room 2A03 available?": AssistantIntent.EXPLAIN_ROOM_STATUS,
            "Tell me a joke": AssistantIntent.UNSUPPORTED,
        }
        for message, intent in cases.items():
            with self.subTest(message=message):
                self.assertEqual(parse_assistant_query(message).intent, intent)

    def test_most_free_capacity_uses_capacity_sort(self):
        plan = parse_assistant_query("Which room on the first floor has the most free capacity?")
        self.assertEqual(plan.floors, [1])
        self.assertEqual(plan.sort, AssistantSort.HIGHEST_AVAILABLE_CAPACITY)


if __name__ == "__main__":
    unittest.main()
