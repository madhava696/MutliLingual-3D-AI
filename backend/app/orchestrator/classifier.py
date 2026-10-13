"""
Intent Classifier — classifies user messages into deterministic tool intents
or LLM conversational routes, with multilingual support (Telugu, Hindi, English).
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Dict, Optional


class IntentType(str, Enum):
    REMINDER_CREATE = "reminder_create"
    REMINDER_LIST = "reminder_list"
    NOTE_SAVE = "note_save"
    NOTE_LIST = "note_list"
    GENERAL_CHAT = "general_chat"
    COMPLEX_REASONING = "complex_reasoning"


@dataclass
class ClassifiedIntent:
    intent_type: IntentType
    confidence: float
    parameters: Dict[str, Any]
    is_deterministic: bool


class IntentClassifier:
    """Classifies user messages using fast rule-based patterns."""

    def classify(self, text: str, language: str = "en") -> ClassifiedIntent:
        clean = text.strip()
        lower = clean.lower()

        # 1. Reminder List Patterns
        if any(p in lower for p in [
            "list reminder", "show reminder", "show my reminder", "what are my reminder",
            "నా రిమైండర్", "రిమైండర్లు చూపించు",
            "मेरे रिमाइंडर", "रिमाइंडर दिखाओ", "रिमाइंडर बताओ",
        ]):
            return ClassifiedIntent(
                intent_type=IntentType.REMINDER_LIST,
                confidence=0.95,
                parameters={},
                is_deterministic=True,
            )

        # 2. Reminder Create Patterns
        # e.g., "remind me to buy milk at 5 PM", "set reminder to submit project"
        remind_match = re.search(
            r"(?:remind me to|set (?:a )?reminder (?:to|for)|create reminder (?:to|for)|reminder:?)\s+(.+)",
            clean,
            re.IGNORECASE,
        )
        if remind_match:
            raw_target = remind_match.group(1).strip()
            # Split time hint if 'at' or 'in' is present
            time_split = re.split(r"\s+(?:at|in|by|on)\s+", raw_target, maxsplit=1, flags=re.IGNORECASE)
            title = time_split[0]
            time_hint = time_split[1] if len(time_split) > 1 else None
            return ClassifiedIntent(
                intent_type=IntentType.REMINDER_CREATE,
                confidence=0.92,
                parameters={"title": title, "time_hint": time_hint},
                is_deterministic=True,
            )

        # Telugu reminder create: "... గుర్తు చేయి"
        if "గుర్తు చేయి" in clean or "గుర్తుపెట్టుకో" in clean or "రిమైండర్ పెట్టు" in clean:
            title = clean.replace("గుర్తు చేయి", "").replace("గుర్తుపెట్టుకో", "").replace("రిమైండర్ పెట్టు", "").strip()
            return ClassifiedIntent(
                intent_type=IntentType.REMINDER_CREATE,
                confidence=0.90,
                parameters={"title": title or "రిమైండర్", "time_hint": None},
                is_deterministic=True,
            )

        # Hindi reminder create: "... याद दिलाना"
        if "याद दिला" in clean or "रिमाइंडर सेट" in clean or "रिमाइंडर लगा" in clean:
            title = clean.replace("याद दिलाना", "").replace("याद दिलाओ", "").replace("रिमाइंडर सेट करो", "").strip()
            return ClassifiedIntent(
                intent_type=IntentType.REMINDER_CREATE,
                confidence=0.90,
                parameters={"title": title or "रिमाइंडर", "time_hint": None},
                is_deterministic=True,
            )

        # 3. Note List Patterns
        if any(p in lower for p in [
            "list note", "show note", "show my note", "what are my note", "read note",
            "నోట్స్ చూపించు", "నా నోట్స్",
            "नोट्स दिखाओ", "मेरे नोट्स",
        ]):
            return ClassifiedIntent(
                intent_type=IntentType.NOTE_LIST,
                confidence=0.95,
                parameters={},
                is_deterministic=True,
            )

        # 4. Note Save Patterns
        note_match = re.search(
            r"(?:take (?:a )?note:?|save (?:a )?note:?|note down:?|write (?:a )?note:?)\s+(.+)",
            clean,
            re.IGNORECASE,
        )
        if note_match:
            content = note_match.group(1).strip()
            return ClassifiedIntent(
                intent_type=IntentType.NOTE_SAVE,
                confidence=0.92,
                parameters={"content": content},
                is_deterministic=True,
            )

        # Telugu note save: "... నోట్ చేసుకో"
        if "నోట్ చేసుకో" in clean or "నోట్ రాయి" in clean:
            content = clean.replace("నోట్ చేసుకో", "").replace("నోట్ రాయి", "").strip()
            return ClassifiedIntent(
                intent_type=IntentType.NOTE_SAVE,
                confidence=0.90,
                parameters={"content": content or "నోట్"},
                is_deterministic=True,
            )

        # Hindi note save: "... नोट लिखो"
        if "नोट लिखो" in clean or "नोट कर लो" in clean:
            content = clean.replace("नोट लिखो", "").replace("नोट कर लो", "").strip()
            return ClassifiedIntent(
                intent_type=IntentType.NOTE_SAVE,
                confidence=0.90,
                parameters={"content": content or "नोट"},
                is_deterministic=True,
            )

        # 5. Complex Reasoning check (long queries, research keywords, complex prompts)
        if len(clean.split()) > 40 or any(k in lower for k in [
            "explain in detail", "analyze", "synthesize", "deep dive", "step by step reasoning"
        ]):
            return ClassifiedIntent(
                intent_type=IntentType.COMPLEX_REASONING,
                confidence=0.85,
                parameters={"query": clean},
                is_deterministic=False,
            )

        # 6. Default General Chat
        return ClassifiedIntent(
            intent_type=IntentType.GENERAL_CHAT,
            confidence=0.80,
            parameters={"query": clean},
            is_deterministic=False,
        )
