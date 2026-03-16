"""Animation library — manages animation assets per state using local storage."""

import random
import logging

logger = logging.getLogger(__name__)


class AnimationLibrary:
    def __init__(self, store=None, registry=None):
        self._store = store
        self._registry = registry

    def _get_store(self):
        if self._store is not None:
            return self._store
        raise RuntimeError("AnimationLibrary requires an injected store")

    def _get_registry(self):
        if self._registry is not None:
            return self._registry
        raise RuntimeError("AnimationLibrary requires an injected registry")

    def _url_prefix(self) -> str:
        """Return the URL prefix for serving animations from this store."""
        import os
        from backend.config import LOCAL_CHARACTERS_DIR
        store = self._get_store()
        base = store.base_dir
        rel = os.path.relpath(base, LOCAL_CHARACTERS_DIR)
        return f"/characters/{rel}"

    async def get_animation_url(self, state: str) -> str | None:
        store = self._get_store()
        animations = store.get_animations(state)
        if animations:
            return f"{self._url_prefix()}/{random.choice(animations)}"
        return None

    async def get_animation_url_with_fallback(self, state: str) -> tuple[str | None, bool]:
        """Get animation URL for a state, falling back to rest role's video.

        Returns:
            (url, is_fallback) — url may be None if no animations exist at all.
        """
        url = await self.get_animation_url(state)
        if url:
            return url, False

        # Fall back to rest role state's animation
        registry = self._get_registry()
        rest_state = registry.get_default_state()
        if rest_state and rest_state != state:
            url = await self.get_animation_url(rest_state)
            if url:
                logger.info(f"Falling back to rest state '{rest_state}' video for '{state}'")
                return url, True

        return None, False

    async def register_animation(self, state: str, rel_path: str) -> None:
        # Already saved by the store during generation; this is for external registration
        pass

    async def get_total_count(self) -> int:
        return self._get_store().get_total_count()

    async def get_per_state_count(self) -> dict[str, int]:
        store = self._get_store()
        all_anims = store.get_all_animations()
        return {k: len(v) for k, v in all_anims.items()}

    def has_animation_for_state(self, state: str) -> bool:
        return len(self._get_store().get_animations(state)) > 0
