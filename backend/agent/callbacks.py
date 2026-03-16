"""ADK Agent callbacks for state transitions + unlock tracking."""

import asyncio
import json
import logging
import os

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

from backend.config import LOCAL_CHARACTERS_DIR
from backend.character.context import get_context
from backend.animation.generator import generate_animation
from backend.animation.state_generator import generate_initial_states
from backend.animation import router as animation_router

logger = logging.getLogger(__name__)

# Registry of per-session state queues
_state_queues: dict[str, asyncio.Queue] = {}

# Per-session unlocked states
_unlocked_states: dict[str, set[str]] = {}

# Per-session selected character image path (absolute)
_character_images: dict[str, str] = {}

# Per-session character description
_character_descriptions: dict[str, str] = {}


def set_character_image(session_id: str, image_path: str) -> None:
    """Store the selected character image path for a session."""
    _character_images[session_id] = image_path


def get_character_image(session_id: str) -> str | None:
    """Get the selected character image path for a session."""
    return _character_images.get(session_id)


def set_character_description(session_id: str, description: str) -> None:
    """Store the character description for a session."""
    _character_descriptions[session_id] = description


def get_character_description(session_id: str) -> str | None:
    """Get the character description for a session."""
    return _character_descriptions.get(session_id)


def get_state_queue(session_id: str) -> asyncio.Queue:
    """Get or create the state queue for a session."""
    if session_id not in _state_queues:
        _state_queues[session_id] = asyncio.Queue()
    return _state_queues[session_id]


def remove_state_queue(session_id: str) -> None:
    """Clean up the state queue for a session."""
    _state_queues.pop(session_id, None)


def _unlocked_path(character_id: str) -> str:
    """Path to the persistent unlocked states file."""
    return os.path.join(LOCAL_CHARACTERS_DIR, character_id, "unlocked_states.json")


def _load_unlocked(character_id: str) -> set[str]:
    """Load unlocked states from disk."""
    path = _unlocked_path(character_id)
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return set()


def _save_unlocked(character_id: str, states: set[str]) -> None:
    """Persist unlocked states to disk."""
    path = _unlocked_path(character_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(states), f)


def record_state(session_id: str, state: str, character_id: str | None = None) -> bool:
    """Record a state as unlocked. Returns True if this is a new unlock.
    Also triggers background animation generation if needed.
    """
    cid = character_id or session_id
    if session_id not in _unlocked_states:
        _unlocked_states[session_id] = _load_unlocked(cid)
    if state in _unlocked_states[session_id]:
        return False
    _unlocked_states[session_id].add(state)
    _save_unlocked(cid, _unlocked_states[session_id])
    # Trigger animation generation for every newly unlocked state
    _maybe_trigger_generation(state, session_id=session_id, character_id=character_id)
    return True


def get_unlocked_count(session_id: str) -> int:
    """Get the number of unique states unlocked for a session."""
    if session_id not in _unlocked_states:
        _unlocked_states[session_id] = _load_unlocked(session_id)
    return len(_unlocked_states[session_id])


def get_unlocked_states(session_id: str) -> set[str]:
    """Get the set of unlocked state names for a session."""
    if session_id not in _unlocked_states:
        _unlocked_states[session_id] = _load_unlocked(session_id)
    return _unlocked_states[session_id]


def cleanup_session(session_id: str) -> None:
    """Clean up in-memory session data (queues only).
    Character images, descriptions, and unlocked states are kept
    so sessions survive page refreshes and restarts."""
    _state_queues.pop(session_id, None)
    # Do NOT clear _unlocked_states — they represent permanent growth


async def pre_generate_basic_states(character_id: str) -> None:
    """Generate initial states via LLM, register them, then trigger animation generation."""
    ctx = get_context(character_id)

    # Ensure the state queue exists so background tasks can push to it
    get_state_queue(character_id)

    description = _character_descriptions.get(character_id, "a friendly AI companion")

    # Generate states dynamically via LLM
    states = await generate_initial_states(description)

    # Clear existing states and register the new ones (only for this character)
    ctx.registry.clear_all()
    # Also reset the character's animations.json
    ctx.store._metadata.clear()
    ctx.store._save_metadata()

    for state_def in states:
        try:
            ctx.registry.register(
                name=state_def["name"],
                label=state_def["label"],
                prompt=state_def["prompt"],
                color=state_def["color"],
                role=state_def["role"],
                pre_generate=True,
            )
        except ValueError:
            logger.warning(f"[PreGen] State {state_def['name']} already exists, skipping")

    # Notify frontend about the new states
    if character_id in _state_queues:
        await _state_queues[character_id].put({
            "type": "states_init",
            "states": ctx.registry.get_all(),
        })

    # Pre-generate animations for all states
    ref_image = _character_images.get(character_id)
    for state_def in states:
        state_name = state_def["name"]
        if ctx.library.has_animation_for_state(state_name):
            asyncio.create_task(_notify_existing_animation(state_name, character_id))
        else:
            prompt = ctx.registry.get_prompt(state_name)
            if prompt:
                logger.info(f"[PreGen] Queuing {state_name} for character {character_id}")
                asyncio.create_task(_generate_bg(prompt, state_name, ref_image, character_id))


async def _notify_existing_animation(state: str, character_id: str) -> None:
    """Send animation_ready for a state that already has a cached animation."""
    try:
        ctx = get_context(character_id)
        url = await ctx.library.get_animation_url(state)
        if url and character_id in _state_queues:
            logger.info(f"[PreGen] Already have animation for {state}, notifying {character_id}")
            await _state_queues[character_id].put({
                "type": "animation_ready",
                "state": state,
                "animation_url": url,
            })
    except Exception as e:
        logger.error(f"[PreGen] Failed to notify existing animation for {state}: {e}")


def _maybe_trigger_generation(state: str, session_id: str | None = None, character_id: str | None = None) -> None:
    """If no animation exists for this state, trigger async generation."""
    cid = character_id or session_id
    if not cid:
        return
    ctx = get_context(cid)
    if not ctx.library.has_animation_for_state(state):
        prompt = ctx.registry.get_prompt(state)
        if prompt:
            ref_image = _character_images.get(cid)
            asyncio.create_task(_generate_bg(prompt, state, ref_image, cid))


async def _generate_bg(
    prompt: str, state: str,
    reference_image_path: str | None = None,
    character_id: str | None = None,
) -> None:
    """Background task to generate animation. Notifies session when done."""
    try:
        ctx = get_context(character_id) if character_id else None
        store = ctx.store if ctx else None
        result = await generate_animation(prompt, state, reference_image_path=reference_image_path, store=store)
        if result:
            logger.info(f"Background animation generated for {state}: {result}")
            # Push notification to the session so frontend can update
            if character_id and character_id in _state_queues and ctx:
                url = await ctx.library.get_animation_url(state)
                if url:
                    await _state_queues[character_id].put({
                        "type": "animation_ready",
                        "state": state,
                        "animation_url": url,
                    })
    except Exception as e:
        logger.error(f"Background animation generation failed for {state}: {e}")


async def before_tool_callback(
    tool: any, args: dict, tool_context: ToolContext
) -> None:
    """Called before each tool execution. Pushes state change to the WebSocket handler."""
    tool_name = tool.name if hasattr(tool, "name") else str(tool)

    # manage_states handles its own state transitions — skip it here
    if tool_name == "manage_states":
        return None

    character_id = tool_context.state.get("_character_id", "")
    if not character_id:
        return None

    ctx = get_context(character_id)

    # Build content description from tool name + args for semantic routing
    args_summary = ", ".join(f"{k}={v}" for k, v in list(args.items())[:3]) if args else ""
    content = f"using {tool_name}: {args_summary}" if args_summary else f"using {tool_name}"

    all_states = ctx.registry.get_all()
    new_state = await animation_router.route_async(
        content, all_states, fallback_role="processing",
        embedding_cache=ctx.state_embeddings,
    )

    queue = get_state_queue(character_id)
    msg = {
        "type": "state_change",
        "state": new_state,
        "label": ctx.registry.get_label(new_state),
    }
    # Attach animation URL with fallback
    url, is_fallback = await ctx.library.get_animation_url_with_fallback(new_state)
    if url:
        msg["animation_url"] = url
    if is_fallback:
        msg["is_fallback"] = True
    await queue.put(msg)
    logger.info(f"[{character_id}] State → {new_state} (tool: {tool_name})")

    # Track unlock (triggers generation automatically if new)
    record_state(character_id, new_state, character_id=character_id)

    return None  # Don't modify tool behavior
