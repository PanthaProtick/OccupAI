import unittest

from model_server.stabilization import OccupancyStabilizer


class OccupancyStabilizerTests(unittest.TestCase):
    def test_mode_suppresses_single_frame_noise(self) -> None:
        stabilizer = OccupancyStabilizer(window_seconds=2.0)
        values = [12, 12, 11, 12, 13, 12]
        stable = [stabilizer.update(value, timestamp=index / 3) for index, value in enumerate(values)]
        self.assertEqual(stable[-1], 12)

    def test_expired_samples_are_removed(self) -> None:
        stabilizer = OccupancyStabilizer(window_seconds=2.0)
        stabilizer.update(12, timestamp=0.0)
        stabilizer.update(12, timestamp=0.5)
        self.assertEqual(stabilizer.update(11, timestamp=2.1), 11)
        self.assertEqual(list(stabilizer.history), [(0.5, 12), (2.1, 11)])

    def test_tie_prefers_most_recent_tied_value(self) -> None:
        stabilizer = OccupancyStabilizer(window_seconds=2.0)
        stabilizer.update(12, timestamp=0.0)
        self.assertEqual(stabilizer.update(13, timestamp=0.1), 13)

    def test_cameras_need_separate_stabilizers(self) -> None:
        camera_one = OccupancyStabilizer()
        camera_two = OccupancyStabilizer()
        camera_one.update(15, timestamp=0.0)
        camera_two.update(8, timestamp=0.0)
        self.assertEqual(camera_one.get_stable_count(), 15)
        self.assertEqual(camera_two.get_stable_count(), 8)


if __name__ == "__main__":
    unittest.main()
