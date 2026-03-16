"""Tool functions for the Motif agent."""

import asyncio
import contextvars
import logging
import os

from backend.animation.generator import generate_animation
from backend.config import LOCAL_CHARACTERS_DIR

logger = logging.getLogger(__name__)

# ContextVar to pass the current character_id into sync tool functions
current_character_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_character_id", default=""
)


def search_web(query: str) -> dict:
    """Search the web for information about a topic.

    Args:
        query: The search query string.

    Returns:
        A dict with search results.
    """
    return {
        "results": [
            {
                "title": f"Search result for: {query}",
                "snippet": f"This is a mock search result for '{query}'. Real search will be implemented with Google Search grounding.",
                "url": "https://example.com",
            }
        ]
    }


def generate_image(prompt: str) -> dict:
    """Generate an image based on a text description.

    Args:
        prompt: A description of the image to generate.

    Returns:
        A dict with the generated image info.
    """
    return {
        "status": "generated",
        "description": f"[Mock image: {prompt}]",
        "url": None,
        "message": "Image generation will be powered by Imagen 4. For now, here's a description of what I'd draw.",
    }



def manage_states(
    action: str,
    name: str,
    label: str = "",
    prompt: str = "",
    color: str = "#7c5cff",
) -> dict:
    """Create, update, or remove animation states for your body.

    Args:
        action: "add", "update", or "remove"
        name: State name (lowercase, no spaces, e.g. "singing")
        label: Display label shown under your body (e.g. "Singing...")
        prompt: Description of the animation for video generation
        color: Hex color for the visual glow effect (e.g. "#ff6600")

    Returns:
        Result with the updated state definition.
    """
    from backend.agent.callbacks import get_state_queue, _state_queues, _character_images
    from backend.character.context import get_context

    char_id = current_character_id.get("")
    if not char_id:
        return {"error": "No character context available"}

    ctx = get_context(char_id)

    try:
        if action == "add":
            if not label or not prompt:
                return {"error": "label and prompt are required for 'add' action"}
            result = ctx.registry.register(name=name, label=label, prompt=prompt, color=color)

            # Trigger background animation generation
            _trigger_generation_for_state(name, char_id)

            # Push states_updated to the character's session
            _push_states_updated(char_id)

            # Also push state_change so frontend transitions to the new state
            if char_id in _state_queues:
                _state_queues[char_id].put_nowait({
                    "type": "state_change",
                    "state": name,
                    "label": label,
                })

            return {"status": "created", "state": result}

        elif action == "update":
            kwargs = {}
            if label:
                kwargs["label"] = label
            if prompt:
                kwargs["prompt"] = prompt
            if color:
                kwargs["color"] = color
            result = ctx.registry.update(name=name, **kwargs)

            # If prompt changed, retrigger animation
            if prompt:
                _trigger_generation_for_state(name, char_id)

            _push_states_updated(char_id)
            return {"status": "updated", "state": result}

        elif action == "remove":
            result = ctx.registry.remove(name=name)
            _push_states_updated(char_id)
            return {"status": "removed", "state": result}

        else:
            return {"error": f"Unknown action '{action}'. Use 'add', 'update', or 'remove'."}

    except ValueError as e:
        return {"error": str(e)}


def _trigger_generation_for_state(state_name: str, character_id: str) -> None:
    """Trigger background Veo 3 generation for a newly created/updated state."""
    from backend.agent.callbacks import _character_images, _state_queues
    from backend.character.context import get_context

    ctx = get_context(character_id)
    anim_prompt = ctx.registry.get_prompt(state_name)
    if not anim_prompt:
        return

    ref_image = _character_images.get(character_id)

    async def _gen():
        try:
            result = await generate_animation(
                anim_prompt, state_name,
                reference_image_path=ref_image,
                store=ctx.store,
            )
            if result and character_id in _state_queues:
                url = await ctx.library.get_animation_url(state_name)
                if url:
                    await _state_queues[character_id].put({
                        "type": "animation_ready",
                        "state": state_name,
                        "animation_url": url,
                    })
        except Exception as e:
            logger.error(f"Background generation failed for new state '{state_name}': {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_gen())
        else:
            loop.run_until_complete(_gen())
    except RuntimeError:
        pass


def _push_states_updated(character_id: str) -> None:
    """Push a states_updated message to the character's session queue."""
    from backend.agent.callbacks import _state_queues
    from backend.character.context import get_context

    ctx = get_context(character_id)
    all_states = ctx.registry.get_all()
    msg = {"type": "states_updated", "states": all_states}

    if character_id in _state_queues:
        try:
            _state_queues[character_id].put_nowait(msg)
        except Exception:
            pass


def _memory_path(character_id: str) -> str:
    """Path to the character's long-term memory file."""
    return os.path.join(LOCAL_CHARACTERS_DIR, character_id, "memory.md")


def load_memory(character_id: str) -> str:
    """Load memory content from disk. Returns empty string if no memory."""
    path = _memory_path(character_id)
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                return f.read()
        except IOError:
            pass
    return ""


def remember(action: str, content: str = "") -> dict:
    """Read or write your long-term memory about the user.

    Use this to remember important things across conversations — the user's name,
    preferences, interests, things they've shared with you.

    Args:
        action: "read" to recall your memories, "write" to save/update them.
        content: When action="write", the full updated memory in markdown.
                 This replaces your entire memory, so include everything you want to keep.

    Returns:
        Your current memory content, or confirmation of write.
    """
    char_id = current_character_id.get("")
    if not char_id:
        return {"error": "No character context available"}

    if action == "read":
        mem = load_memory(char_id)
        if mem:
            return {"status": "ok", "memory": mem}
        return {"status": "ok", "memory": "", "message": "No memories yet."}

    elif action == "write":
        if not content:
            return {"error": "content is required for 'write' action"}
        path = _memory_path(char_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return {"status": "saved", "message": "Memory updated successfully."}

    else:
        return {"error": f"Unknown action '{action}'. Use 'read' or 'write'."}
