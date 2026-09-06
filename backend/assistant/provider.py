from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.models import AssistantResult


@dataclass(frozen=True)
class AssistantProviderRequest:
    """The complete and deliberately narrow fact set visible to a language provider."""

    deterministic_answer: str
    results: tuple[AssistantResult, ...]


@runtime_checkable
class AssistantLanguageProvider(Protocol):
    name: str

    def rewrite(self, request: AssistantProviderRequest) -> str:
        """Improve phrasing without adding, removing, or deciding factual results."""


@dataclass(frozen=True)
class AssistantProviderOutcome:
    answer: str
    used_fallback: bool
    provider_used: str
    warning: str | None = None
    error_category: str | None = None


_ROOM_ID = re.compile(r"\broom_[a-z0-9_]+\b", re.IGNORECASE)
_ROOM_NAME = re.compile(r"\b\d{1,2}[abc]\d{2}\b", re.IGNORECASE)
_PERCENTAGE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")
MAX_PROVIDER_ANSWER_LENGTH = 10_000


class AssistantProviderCoordinator:
    """Bound optional provider work and preserve deterministic behavior on every failure."""

    def __init__(
        self,
        provider: AssistantLanguageProvider | None,
        timeout_seconds: float,
    ) -> None:
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="assistant-provider")

    def rewrite(
        self, deterministic_answer: str, results: list[AssistantResult]
    ) -> AssistantProviderOutcome:
        if self.provider is None:
            return AssistantProviderOutcome(
                deterministic_answer, used_fallback=False, provider_used="deterministic"
            )
        request = AssistantProviderRequest(deterministic_answer, tuple(results))
        future = self._executor.submit(self.provider.rewrite, request)
        try:
            answer = future.result(timeout=self.timeout_seconds)
        except FutureTimeout:
            future.cancel()
            return self._fallback(deterministic_answer, "provider_timeout")
        except Exception:
            return self._fallback(deterministic_answer, "provider_error")
        if not self._is_grounded(answer, request):
            return self._fallback(deterministic_answer, "provider_invalid_output")
        return AssistantProviderOutcome(
            answer.strip(), used_fallback=False, provider_used=self.provider.name
        )

    @staticmethod
    def _fallback(answer: str, error_category: str) -> AssistantProviderOutcome:
        return AssistantProviderOutcome(
            answer,
            used_fallback=True,
            provider_used="deterministic",
            warning="Enhanced phrasing was unavailable; the verified deterministic answer is shown.",
            error_category=error_category,
        )

    @staticmethod
    def _is_grounded(answer: object, request: AssistantProviderRequest) -> bool:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_PROVIDER_ANSWER_LENGTH:
            return False
        allowed_ids = {result.room_id.casefold() for result in request.results}
        if any(value.casefold() not in allowed_ids for value in _ROOM_ID.findall(answer)):
            return False
        allowed_names = {result.name.casefold() for result in request.results}
        if any(value.casefold() not in allowed_names for value in _ROOM_NAME.findall(answer)):
            return False
        allowed_percentages = {round(result.occupancy_percentage, 6) for result in request.results}
        if any(round(float(value), 6) not in allowed_percentages for value in _PERCENTAGE.findall(answer)):
            return False
        return True

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
