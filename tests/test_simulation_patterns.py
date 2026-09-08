import random
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from backend.config import Settings
from mock.generate_mock_data import ROOMS, make_live
from mock.occupancy_patterns import expected_occupancy, occupancy_at


class OccupancyPatternTests(unittest.TestCase):
    def test_classrooms_are_mostly_busy_with_a_smaller_quiet_group(self):
        rooms = [r for r in ROOMS if r['behavior_profile'] == 'classroom']
        for day in range(7):
            for minute in range(0, 1440, 15):
                values = [expected_occupancy('classroom', minute / 60, day, r['camera_id']) for r in rooms]
                self.assertGreater(sum(v >= .5 for v in values) / len(values), .70)
                self.assertLess(sum(v < .25 for v in values) / len(values), .20)
                self.assertTrue(all(0 <= v <= 1 for v in values))

    def test_common_rooms_have_short_quiet_periods_and_smooth_transitions(self):
        for room in (r for r in ROOMS if r['behavior_profile'] != 'classroom'):
            values = [expected_occupancy(room['behavior_profile'], m / 60, 1, room['camera_id']) for m in range(1440)]
            self.assertGreater(sum(v >= .5 for v in values) / len(values), .85)
            self.assertGreater(sum(v < .5 for v in values) / len(values), .03)
            self.assertLess(max(abs(a - b) for a, b in zip(values, values[1:])), .07)

    def test_schedule_uses_dhaka_day_and_time(self):
        utc = datetime(2026, 9, 10, 22, 30, tzinfo=timezone.utc)
        self.assertAlmostEqual(occupancy_at('classroom', utc, 'cam_093'),
                               expected_occupancy('classroom', 4.5, 4, 'cam_093'))
        self.assertEqual(occupancy_at('library', utc, 'cam_010'),
                         occupancy_at('library', utc.astimezone(timezone(timedelta(hours=6))), 'cam_010'))
        with self.assertRaises(ValueError):
            occupancy_at('classroom', utc.replace(tzinfo=None), 'cam_093')

    def test_mock_snapshot_uses_same_pattern_as_live_simulation(self):
        now = datetime(2026, 9, 8, 16, tzinfo=timezone.utc)
        live = make_live(random.Random(42), now)
        for room, state in zip(ROOMS, live['cameras']):
            expected = occupancy_at(room['behavior_profile'], now, room['camera_id'])
            self.assertLess(abs(state['occupancy'] / room['capacity'] - expected), .10)

    def test_model_feeds_and_backend_exclusions_match_requested_rooms(self):
        root = Path(__file__).resolve().parents[1]
        config = yaml.safe_load((root / 'model_server/config/cameras.yaml').read_text())
        camera_ids = tuple(c['camera_id'] for c in config['cameras'])
        names = {r['camera_id']: r['name'] for r in ROOMS}
        self.assertEqual(tuple(names[c] for c in camera_ids), ('7A03', '7B03', '7C07'))
        self.assertEqual(Settings().live_camera_ids, camera_ids)


if __name__ == '__main__':
    unittest.main()
