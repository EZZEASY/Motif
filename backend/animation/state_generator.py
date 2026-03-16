"""Generate initial animation states dynamically via Gemini based on character description."""

import json
import logging

from google import genai
from google.genai import types

from backend.config import GOOGLE_GENAI_API_KEY

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)
    return _client


GENERATE_STATES_PROMPT = """\
You are designing animation states for an AI companion character.

The character is described as: {description}

Generate exactly 3 animation states for this character. Each state serves a specific role:
1. **rest** — the default idle state when the character is not doing anything
2. **processing** — shown when the character is thinking or working on something
3. **speaking** — shown when the character is talking/responding

For each state, provide:
- **name**: a short, unique snake_case name that fits the character's personality (e.g., "floating_calm", "spark_thinking", "wave_talking"). Do NOT use generic names like "idle", "thinking", "talking".
- **label**: a short display label shown in the UI (e.g., "Floating calmly...", "Sparking ideas...", "Chatting away...")
- **prompt**: a vivid animation prompt describing what the character looks like in this state. Reference the character's appearance. Keep it under 30 words.
- **color**: a hex color code that fits the mood of this state

Respond with ONLY a JSON array, no other text:
[
  {{"name": "...", "label": "...", "prompt": "...", "color": "...", "role": "rest"}},
  {{"name": "...", "label": "...", "prompt": "...", "color": "...", "role": "processing"}},
  {{"name": "...", "label": "...", "prompt": "...", "color": "...", "role": "speaking"}}
]
"""


def _generate_sync(description: str) -> list[dict]:
    """Call Gemini to generate 3 initial states based on character description."""
    client = _get_client()
    prompt = GENERATE_STATES_PROMPT.format(description=description)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.8,
        ),
    )

    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    states = json.loads(text)
    if not isinstance(states, list) or len(states) != 3:
        raise ValueError(f"Expected 3 states, got: {text}")

    # Validate roles
    roles = {s["role"] for s in states}
    if roles != {"rest", "processing", "speaking"}:
        raise ValueError(f"Expected roles rest/processing/speaking, got: {roles}")

    logger.info(f"[StateGen] Generated states: {[s['name'] for s in states]}")
    return states


async def generate_initial_states(description: str) -> list[dict]:
    """Generate 3 initial animation states for a character (async wrapper)."""
    import asyncio
    try:
        return await asyncio.to_thread(_generate_sync, description)
    except Exception as e:
        logger.error(f"[StateGen] Failed to generate states: {e}", exc_info=True)
        # Fallback: generate generic states based on description
        return _fallback_states(description)


def _fallback_states(description: str) -> list[dict]:
    """Fallback states if LLM generation fails."""
    short = description[:50] if description else "the character"
    return [
        {
            "name": "resting",
            "label": "Resting...",
            "prompt": f"{short} standing relaxed, gentle breathing, calm atmosphere",
            "color": "#7c5cff",
            "role": "rest",
        },
        {
            "name": "pondering",
            "label": "Pondering...",
            "prompt": f"{short} in a thoughtful pose, subtle glow pulsing around them",
            "color": "#ffaa00",
            "role": "processing",
        },
        {
            "name": "chatting",
            "label": "Chatting...",
            "prompt": f"{short} animatedly talking, warm expressive gestures",
            "color": "#66bbff",
            "role": "speaking",
        },
    ]
