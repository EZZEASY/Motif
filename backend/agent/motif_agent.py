"""Motif ADK Agent definition."""

from google.adk.agents import Agent

from backend.agent.prompts import MOTIF_SYSTEM_PROMPT
from backend.agent.tools import (
    search_web,
    generate_image,
    manage_states,
    remember,
    load_memory,
)
from backend.agent.callbacks import before_tool_callback


def _get_instruction(context):
    """Dynamic system prompt with long-term memory injection."""
    character_id = context.state.get("_character_id", "")
    prompt = MOTIF_SYSTEM_PROMPT
    if character_id:
        memory = load_memory(character_id)
        if memory:
            prompt += f"\n\n## Your Memories About This User\n{memory}"
    return prompt


motif_agent = Agent(
    name="motif",
    model="gemini-2.5-flash",
    instruction=_get_instruction,
    tools=[search_web, generate_image, manage_states, remember],
    before_tool_callback=before_tool_callback,
)
