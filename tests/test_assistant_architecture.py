from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.assistant import (
    ASSISTANT_ARCHITECTURE,
    BROWSER_SAFE_RESULT_FIELDS,
    FORBIDDEN_BROWSER_FIELDS,
    AssistantArchitecture,
    AssistantOccupancySource,
)


class _CompatibleSource:
    generated_at = datetime.now(timezone.utc)

    def list_rooms(self):
        return []

    def list_occupancy(self):
        return []

    def list_assistant_snapshots(self):
        return []


class AssistantArchitectureTests(unittest.TestCase):
    def test_assistant_is_backend_grounded_and_provider_has_no_direct_tools(self):
        self.assertEqual(ASSISTANT_ARCHITECTURE.execution_tier, "backend")
        self.assertEqual(ASSISTANT_ARCHITECTURE.browser_transport, "occupai_api_only")
        self.assertEqual(ASSISTANT_ARCHITECTURE.data_access, "validated_repository")
        self.assertFalse(ASSISTANT_ARCHITECTURE.provider_database_access)
        self.assertFalse(ASSISTANT_ARCHITECTURE.provider_arbitrary_tool_access)
        self.assertEqual(ASSISTANT_ARCHITECTURE.factual_ranking_owner, "deterministic_backend")

    def test_browser_allowlist_excludes_every_forbidden_field(self):
        self.assertTrue(BROWSER_SAFE_RESULT_FIELDS)
        self.assertFalse(BROWSER_SAFE_RESULT_FIELDS & FORBIDDEN_BROWSER_FIELDS)
        for sensitive_fragment in ("password", "token", "secret", "key", "authorization", "prompt"):
            self.assertFalse(any(
                sensitive_fragment in field for field in BROWSER_SAFE_RESULT_FIELDS
            ))

    def test_occupancy_source_is_a_read_only_structural_boundary(self):
        self.assertIsInstance(_CompatibleSource(), AssistantOccupancySource)
        self.assertNotIn("execute", AssistantOccupancySource.__dict__)
        self.assertNotIn("commit", AssistantOccupancySource.__dict__)

    def test_invalid_architecture_cannot_enable_provider_database_access(self):
        with self.assertRaises(ValueError):
            AssistantArchitecture(provider_database_access=True)
        with self.assertRaises(ValueError):
            AssistantArchitecture(provider_arbitrary_tool_access=True)


if __name__ == "__main__":
    unittest.main()
