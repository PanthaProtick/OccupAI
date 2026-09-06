"""Backend-grounded services for the OccupAI Campus Assistant."""

from backend.assistant.architecture import (
    ASSISTANT_ARCHITECTURE,
    BROWSER_SAFE_RESULT_FIELDS,
    FORBIDDEN_BROWSER_FIELDS,
    AssistantArchitecture,
    AssistantOccupancySource,
    AssistantRoomSnapshot,
)
from backend.assistant.parser import (
    AssistantIntent,
    AssistantQueryPlan,
    AssistantSort,
    parse_assistant_query,
)
from backend.assistant.query_engine import execute_query_plan, room_block
from backend.assistant.ranking import rank_query_results
from backend.assistant.responses import AssistantResponseContent, compose_assistant_response
from backend.assistant.conversations import AssistantConversationService
from backend.assistant.safety import (
    SAFE_SCOPE_RESPONSE,
    AssistantSafetyDecision,
    inspect_assistant_message,
    sanitize_assistant_message_for_storage,
)
from backend.assistant.provider import (
    AssistantLanguageProvider,
    AssistantProviderCoordinator,
    AssistantProviderOutcome,
    AssistantProviderRequest,
)
from backend.assistant.gemini import GeminiAssistantProvider

__all__ = [
    "ASSISTANT_ARCHITECTURE",
    "BROWSER_SAFE_RESULT_FIELDS",
    "FORBIDDEN_BROWSER_FIELDS",
    "AssistantArchitecture",
    "AssistantOccupancySource",
    "AssistantRoomSnapshot",
    "AssistantIntent",
    "AssistantQueryPlan",
    "AssistantSort",
    "parse_assistant_query",
    "execute_query_plan",
    "room_block",
    "rank_query_results",
    "AssistantResponseContent",
    "compose_assistant_response",
    "AssistantConversationService",
    "SAFE_SCOPE_RESPONSE",
    "AssistantSafetyDecision",
    "inspect_assistant_message",
    "sanitize_assistant_message_for_storage",
    "AssistantLanguageProvider",
    "AssistantProviderCoordinator",
    "GeminiAssistantProvider",
    "AssistantProviderOutcome",
    "AssistantProviderRequest",
]
