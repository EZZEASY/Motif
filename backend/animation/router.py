"""Content-driven animation routing using local semantic embeddings.

Uses sentence-transformers (BAAI/bge-small-en-v1.5, ~33MB) to match content
against state definitions and pick the best-matching animation state.
"""

import asyncio
import logging
import os
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

# Use cached model offline — skip HuggingFace Hub update checks
os.environ.setdefault("HF_HUB_OFFLINE", "1")

# Lazy-loaded model and state embeddings
_model = None
_model_ready = False
_state_embeddings: dict[str, np.ndarray] = {}

# Similarity threshold — below this we fall back to the role-based default
SIMILARITY_THRESHOLD = 0.35

# Bias added to states whose role matches the fallback_role
ROLE_BIAS = 0.1


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model (BAAI/bge-small-en-v1.5)...")
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        logger.info("Model loaded successfully.")
    return _model


async def preload_model_async():
    """Load model in background thread — non-blocking."""
    global _model_ready
    try:
        await asyncio.to_thread(_get_model)
        _model_ready = True
        logger.info("Model preloaded and ready.")
    except Exception as e:
        logger.warning(f"Model preload failed (will retry on first request): {e}")


def _build_state_text(name: str, defn: dict) -> str:
    """Build a representative text string for a state from its definition."""
    parts = [name.replace("_", " ")]
    if defn.get("label"):
        parts.append(defn["label"])
    if defn.get("prompt"):
        parts.append(defn["prompt"])
    return ". ".join(parts)


def invalidate_cache():
    """Clear pre-computed state embeddings so they're recomputed on next route()."""
    global _state_embeddings
    _state_embeddings.clear()
    logger.info("Animation router embedding cache invalidated.")


def _ensure_embeddings(states: dict, embedding_cache: dict | None = None) -> dict:
    """Compute embeddings for all states if not already cached.

    Args:
        states: State definitions dict.
        embedding_cache: External cache to use. If None, uses global _state_embeddings.

    Returns:
        The embedding cache dict (may be the global or the passed-in one).
    """
    global _state_embeddings
    cache = embedding_cache if embedding_cache is not None else _state_embeddings
    if cache:
        return cache

    model = _get_model()
    texts = []
    names = []
    for name, defn in states.items():
        names.append(name)
        texts.append(_build_state_text(name, defn))

    if not texts:
        return cache

    embeddings = model.encode(texts, normalize_embeddings=True)
    for n, emb in zip(names, embeddings):
        cache[n] = emb

    # If using global, update it
    if embedding_cache is None:
        _state_embeddings = cache

    logger.info(f"Pre-computed embeddings for {len(names)} states.")
    return cache


def route(content: str, states: dict, fallback_role: str = "rest", embedding_cache: dict | None = None) -> str:
    """Route content to the best-matching animation state.

    Args:
        content: The text content to match against states.
        states: Current state definitions dict from registry.get_all().
        fallback_role: Role to use for bias and fallback (rest/processing/speaking).
        embedding_cache: Optional external embedding cache (for per-character isolation).

    Returns:
        The name of the best-matching state.
    """
    if not states:
        return "idle"

    # Model still loading in background — use role-based fallback
    if not _model_ready:
        return _role_fallback(states, fallback_role)

    cache = _ensure_embeddings(states, embedding_cache)

    if not cache:
        # No embeddings available — fall back to role-based
        return _role_fallback(states, fallback_role)

    model = _get_model()
    content_emb = model.encode([content], normalize_embeddings=True)[0]

    best_score = -1.0
    best_raw = -1.0
    best_state = None

    for name, state_emb in cache.items():
        if name not in states:
            continue
        raw = float(np.dot(content_emb, state_emb))
        score = raw
        # Bias toward states matching the expected role
        defn = states.get(name, {})
        if defn.get("role") == fallback_role:
            score += ROLE_BIAS
        if score > best_score:
            best_score = score
            best_raw = raw
            best_state = name

    if best_score < SIMILARITY_THRESHOLD or best_state is None:
        fb = _role_fallback(states, fallback_role)
        logger.info(f"No good match (best='{best_state}', score={best_score:.3f}, raw={best_raw:.3f}), fallback to '{fb}'")
        logger.debug(f"  input: {content!r:.120}")
        return fb

    logger.info(f"Routed content to '{best_state}' (score={best_score:.3f}, raw={best_raw:.3f})")
    logger.debug(f"  input: {content!r:.120}")
    return best_state


async def route_async(content: str, states: dict, fallback_role: str = "rest", embedding_cache: dict | None = None) -> str:
    """Async wrapper around route() — runs in a thread to avoid blocking."""
    return await asyncio.to_thread(route, content, states, fallback_role, embedding_cache)


def _role_fallback(states: dict, role: str) -> str:
    """Find a state with the given role, or return the first state."""
    for name, defn in states.items():
        if defn.get("role") == role:
            return name
    # Ultimate fallback: first state with "rest" role, then any first state
    for name, defn in states.items():
        if defn.get("role") == "rest":
            return name
    return next(iter(states), "idle")
