"""Per-character isolation context — registry, store, library."""

import os
import logging

import numpy as np

from backend.config import LOCAL_CHARACTERS_DIR
from backend.animation.state_machine import StateRegistry
from backend.storage.local import LocalAnimationStore
from backend.animation.library import AnimationLibrary

logger = logging.getLogger(__name__)


class CharacterContext:
    """Isolated context for a single character: registry, store, library."""

    def __init__(self, character_id: str):
        self.character_id = character_id
        base = os.path.join(LOCAL_CHARACTERS_DIR, character_id)
        os.makedirs(base, exist_ok=True)

        self.registry = StateRegistry(os.path.join(base, "states.json"))
        anim_dir = os.path.join(base, "animations")
        self.store = LocalAnimationStore(anim_dir)
        self.library = AnimationLibrary(store=self.store, registry=self.registry)

        # Per-character embedding cache for semantic routing
        self.state_embeddings: dict[str, np.ndarray] = {}
        self.registry.on_change(lambda: self.state_embeddings.clear())


_contexts: dict[str, CharacterContext] = {}


def get_context(character_id: str) -> CharacterContext:
    """Get or create the isolated context for a character."""
    if character_id not in _contexts:
        _contexts[character_id] = CharacterContext(character_id)
    return _contexts[character_id]


def remove_context(character_id: str) -> None:
    """Remove a cached context (e.g. on character deletion)."""
    _contexts.pop(character_id, None)
