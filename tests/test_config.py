from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.config import Settings


class SettingsEnvironmentTests(unittest.TestCase):
    def test_explicit_empty_live_camera_list_is_not_replaced_by_default(self):
        with patch("backend.config.dotenv_values", return_value={"LIVE_CAMERA_IDS": ""}), \
             patch("backend.config.os.getenv", return_value=None):
            settings = Settings.from_env()
        self.assertEqual(settings.live_camera_ids, ())


if __name__ == "__main__":
    unittest.main()
