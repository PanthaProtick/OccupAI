from __future__ import annotations

import tempfile
import time
import unittest
import json
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.assistant import (
    AssistantProviderCoordinator,
    AssistantProviderRequest,
    GeminiAssistantProvider,
)
from backend.config import Settings
from backend.database import Base
from backend.models import AssistantResult, CameraStatus
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


def result() -> AssistantResult:
    return AssistantResult(
        room_id="room_1a02", name="1A02", building="University Building", floor=1,
        block="A", capacity=40, occupancy=6, occupancy_percentage=15,
        available_capacity=34, status=CameraStatus.ONLINE,
        observed_at=datetime(2026, 9, 5, tzinfo=timezone.utc), reason="Verified result.",
    )


class RewritingProvider:
    name = "test-provider"

    def __init__(self, answer: str | None = None, error: Exception | None = None, delay: float = 0):
        self.answer = answer
        self.error = error
        self.delay = delay
        self.request: AssistantProviderRequest | None = None

    def rewrite(self, request: AssistantProviderRequest) -> str:
        self.request = request
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.answer or request.deterministic_answer


class AssistantProviderUnitTests(unittest.TestCase):
    def test_gemini_adapter_uses_fixed_endpoint_and_only_safe_grounded_payload(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def read(self):
                return json.dumps({"candidates":[{"content":{"parts":[
                    {"text":"Room 1A02 is currently 15% occupied."}
                ]}}]}).encode()

        provider = GeminiAssistantProvider("test-api-key", "gemini-3.5-flash-lite", 0.5)
        with patch("backend.assistant.gemini.urlopen", return_value=Response()) as send:
            answer = provider.rewrite(AssistantProviderRequest("Verified fallback", (result(),)))
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        serialized = json.dumps(payload)
        self.assertEqual(request.full_url, (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.5-flash-lite:generateContent"
        ))
        self.assertEqual(request.headers["X-goog-api-key"], "test-api-key")
        self.assertIn("Verified fallback", serialized)
        self.assertIn("room_1a02", serialized)
        self.assertNotIn("password_hash", serialized)
        self.assertEqual(answer, "Room 1A02 is currently 15% occupied.")

    def test_gemini_rejects_missing_key_and_unsafe_model_name(self):
        with self.assertRaisesRegex(ValueError, "ASSISTANT_API_KEY"):
            GeminiAssistantProvider("", "gemini-3.5-flash-lite", 1)
        with self.assertRaisesRegex(ValueError, "model identifier"):
            GeminiAssistantProvider("key", "../unsafe", 1)

    def test_provider_receives_only_grounded_results_and_deterministic_answer(self):
        provider = RewritingProvider("Room 1A02 is currently 15% occupied.")
        coordinator = AssistantProviderCoordinator(provider, 0.5)
        outcome = coordinator.rewrite("Verified fallback", [result()])
        coordinator.close()
        self.assertEqual(outcome.answer, "Room 1A02 is currently 15% occupied.")
        self.assertFalse(outcome.used_fallback)
        self.assertEqual(tuple(provider.request.results), (result(),))
        self.assertEqual(set(vars(provider.request)), {"deterministic_answer", "results"})

    def test_timeout_exception_and_malformed_output_use_deterministic_fallback(self):
        providers = (
            RewritingProvider(delay=0.08),
            RewritingProvider(error=RuntimeError("provider secret must not escape")),
            RewritingProvider("Invented room 9A99 is 99% occupied."),
        )
        for provider in providers:
            with self.subTest(provider=provider):
                coordinator = AssistantProviderCoordinator(provider, 0.01)
                outcome = coordinator.rewrite("Verified fallback", [result()])
                coordinator.close()
                self.assertEqual(outcome.answer, "Verified fallback")
                self.assertTrue(outcome.used_fallback)
                self.assertNotIn("secret", outcome.warning or "")

    def test_deterministic_mode_never_calls_an_external_provider(self):
        coordinator = AssistantProviderCoordinator(None, 0.01)
        outcome = coordinator.rewrite("Local answer", [result()])
        coordinator.close()
        self.assertEqual(outcome.answer, "Local answer")
        self.assertFalse(outcome.used_fallback)
        self.assertIsNone(outcome.warning)


class AssistantProviderConfigurationTests(unittest.TestCase):
    def test_external_provider_requires_model_and_key_in_production(self):
        common = dict(
            app_environment="production", auth_cookie_secure=True,
            auth_session_pepper="a-unique-production-pepper-value", assistant_provider="external",
        )
        with self.assertRaisesRegex(ValueError, "ASSISTANT_MODEL"):
            Settings(**common)
        with self.assertRaisesRegex(ValueError, "ASSISTANT_API_KEY"):
            Settings(**common, assistant_model="campus-model")
        configured = Settings(
            **common, assistant_model="campus-model", assistant_api_key="provider-secret"
        )
        self.assertNotIn("assistant_api_key", configured.safe_summary())
        self.assertNotIn("provider-secret", str(configured.safe_summary()))


class AssistantProviderApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.url = f"sqlite:///{(Path(self.temp.name) / 'provider.db').as_posix()}"
        engine = create_engine(self.url)
        Base.metadata.create_all(engine)
        engine.dispose()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _signup(client: TestClient) -> None:
        response = client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Provider Student", "email": "provider@aust.edu", "password": PASSWORD,
        })
        if response.status_code != 201:
            raise AssertionError(response.text)

    def test_provider_failure_returns_verified_deterministic_answer(self):
        provider = RewritingProvider(error=RuntimeError("do not expose this provider key"))
        settings = Settings(
            database_url=self.url, auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_provider="test", assistant_model="test-model", assistant_api_key="secret",
        )
        with TestClient(create_app(
            settings, MockOccupancyRepository(settings.mock_data_dir), assistant_provider=provider
        )) as client:
            self._signup(client)
            response = client.post(
                "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message":"Free rooms"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["results"])
            self.assertIn("verified deterministic answer", response.json()["warnings"][-1])
            self.assertNotIn("provider key", response.text)

    def test_gemini_configuration_selects_the_gemini_adapter(self):
        settings = Settings(
            database_url=self.url,
            auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_provider="gemini",
            assistant_model="gemini-3.5-flash-lite",
            assistant_api_key="test-only-key",
        )
        with TestClient(create_app(
            settings, MockOccupancyRepository(settings.mock_data_dir)
        )) as client:
            provider = client.app.state.assistant_provider_coordinator.provider
            self.assertIsInstance(provider, GeminiAssistantProvider)
            self.assertNotIn("test-only-key", str(settings.safe_summary()))

    def test_disabled_assistant_returns_standard_safe_error(self):
        settings = Settings(
            database_url=self.url, auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_enabled=False,
        )
        with TestClient(create_app(
            settings, MockOccupancyRepository(settings.mock_data_dir)
        )) as client:
            self._signup(client)
            response = client.post(
                "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message":"Free rooms"}
            )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "assistant_disabled")
            self.assertNotIn("key", response.text.casefold())


if __name__ == "__main__":
    unittest.main()
