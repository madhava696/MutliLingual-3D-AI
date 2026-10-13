"""
Orchestrator Engine — the central brain of the text-only vertical slice.

Flow: User text → IntentClassifier → route to deterministic tool OR LLM
     → format response → track cost → return to WebSocket handler.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.classifier import ClassifiedIntent, IntentClassifier, IntentType
from app.orchestrator.cost_tracker import calculate_cost_usd, record_usage_log
from app.orchestrator.prompts import format_conversation_history, get_system_prompt
from app.providers.base import ModelTier
from app.providers.factory import get_model_provider
from app.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResponse:
    """Response from the orchestrator pipeline."""
    text: str
    is_tool_result: bool = False
    needs_confirmation: bool = False
    confirmation_payload: Optional[dict] = None
    cost_usd: float = 0.0
    model_used: Optional[str] = None
    latency_ms: int = 0
    tool_data: Optional[dict] = None


# Map intent types to tool names
INTENT_TO_TOOL = {
    IntentType.REMINDER_CREATE: "reminder_create",
    IntentType.REMINDER_LIST: "reminder_list",
    IntentType.NOTE_SAVE: "note_save",
    IntentType.NOTE_LIST: "note_list",
}


class OrchestratorEngine:
    """
    Central orchestrator that:
    1. Classifies user intent
    2. Routes deterministic intents to tools (zero LLM cost)
    3. Routes conversational/complex intents to LLM (with cost tracking)
    """

    def __init__(self):
        self.classifier = IntentClassifier()

    async def process_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        text: str,
        language: str = "en",
        conversation_history: Optional[list] = None,
    ) -> OrchestratorResponse:
        """
        Main entry point: classify → route → execute → return response.
        """
        start_time = time.perf_counter()

        # Step 1: Classify intent
        classified = self.classifier.classify(text, language)
        logger.info(
            f"Intent classified: {classified.intent_type.value} "
            f"(confidence={classified.confidence:.2f}, deterministic={classified.is_deterministic})"
        )

        # Step 2: Route to appropriate handler
        if classified.is_deterministic:
            response = await self._handle_deterministic(
                db=db,
                session_id=session_id,
                language=language,
                classified=classified,
            )
        else:
            response = await self._handle_llm(
                db=db,
                session_id=session_id,
                text=text,
                language=language,
                classified=classified,
                conversation_history=conversation_history or [],
            )

        response.latency_ms = int((time.perf_counter() - start_time) * 1000)
        return response

    async def _handle_deterministic(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        classified: ClassifiedIntent,
    ) -> OrchestratorResponse:
        """Route deterministic intents to the tool registry."""
        tool_name = INTENT_TO_TOOL.get(classified.intent_type)
        if not tool_name:
            return OrchestratorResponse(
                text="I couldn't determine which action to take. Could you rephrase?",
                is_tool_result=False,
            )

        registry = get_tool_registry()
        result = await registry.execute_tool(
            name=tool_name,
            db=db,
            session_id=session_id,
            language=language,
            **classified.parameters,
        )

        # Record zero-cost usage for deterministic tools
        await record_usage_log(
            db=db,
            session_id=session_id,
            provider="deterministic",
            model="tool:" + tool_name,
            task_type=classified.intent_type.value,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
        )

        return OrchestratorResponse(
            text=result.message,
            is_tool_result=True,
            needs_confirmation=result.needs_confirmation,
            confirmation_payload=result.confirmation_payload,
            cost_usd=0.0,
            model_used=f"tool:{tool_name}",
            tool_data=result.data if isinstance(result.data, dict) else None,
        )

    async def _handle_llm(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        text: str,
        language: str,
        classified: ClassifiedIntent,
        conversation_history: list,
    ) -> OrchestratorResponse:
        """Route conversational/complex intents to the LLM provider."""
        # Select model tier based on intent complexity
        tier = (
            ModelTier.CAPABLE
            if classified.intent_type == IntentType.COMPLEX_REASONING
            else ModelTier.ECONOMICAL
        )

        # Build prompt with system instruction and conversation context
        system_prompt = get_system_prompt(language=language)
        context = ""
        if conversation_history:
            context = format_conversation_history(conversation_history) + "\n\n"
        full_prompt = f"{context}User: {text}"

        # Call LLM
        provider = get_model_provider()
        try:
            llm_response = await provider.generate(
                prompt=full_prompt,
                tier=tier,
                system_instruction=system_prompt,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = (
                "నేను ప్రస్తుతం AI సేవకు కనెక్ట్ కాలేకపోతున్నాను. దయచేసి మళ్ళీ ప్రయత్నించండి." if language == "te"
                else "मैं वर्तमान में AI सेवा से कनेक्ट नहीं हो पा रहा हूँ। कृपया पुनः प्रयास करें।" if language == "hi"
                else "I couldn't connect to the AI service right now. Please try again."
            )
            return OrchestratorResponse(text=fallback, is_tool_result=False)

        # Calculate and record cost
        cost = calculate_cost_usd(
            model=llm_response.model_name,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
        )

        await record_usage_log(
            db=db,
            session_id=session_id,
            provider=llm_response.provider,
            model=llm_response.model_name,
            task_type=classified.intent_type.value,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            estimated_cost_usd=cost,
            latency_ms=llm_response.latency_ms,
        )

        return OrchestratorResponse(
            text=llm_response.text,
            is_tool_result=False,
            cost_usd=cost,
            model_used=llm_response.model_name,
        )


# Module-level singleton
_engine: Optional[OrchestratorEngine] = None


def get_orchestrator() -> OrchestratorEngine:
    """Return the global orchestrator engine singleton."""
    global _engine
    if _engine is None:
        _engine = OrchestratorEngine()
    return _engine
