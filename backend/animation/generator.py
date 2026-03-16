"""Veo 3 animation generation pipeline."""

import asyncio
import logging
import os
import time

from google import genai
from google.genai import types

from backend.config import GOOGLE_GENAI_API_KEY, LOCAL_ANIMATIONS_DIR
from backend.storage.local import LocalAnimationStore

logger = logging.getLogger(__name__)

_client: genai.Client | None = None
_store: LocalAnimationStore | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)
    return _client


def get_store() -> LocalAnimationStore:
    """DEPRECATED: Use per-character store instead."""
    logger.warning("[DEPRECATED] get_store() called — use per-character store instead")
    global _store
    if _store is None:
        _store = LocalAnimationStore(LOCAL_ANIMATIONS_DIR)
    return _store


async def generate_animation(prompt: str, state: str, reference_image_path: str | None = None, store=None) -> str | None:
    """Generate an animation using Veo 3.

    Args:
        prompt: Text prompt describing the animation.
        state: The agent state this animation is for.
        reference_image_path: Optional path to a character reference image.
        store: Optional LocalAnimationStore to save to (defaults to global store).

    Returns the local relative path of the generated video, or None if generation fails.
    """
    if not GOOGLE_GENAI_API_KEY:
        logger.warning("[Veo3] No GOOGLE_GENAI_API_KEY configured, skipping generation")
        return None

    logger.info(f"[Veo3] Generating animation for state={state}: {prompt[:80]}...")

    try:
        client = _get_client()

        # Build character image for first/last frame control
        char_image = None
        if reference_image_path and os.path.isfile(reference_image_path):
            with open(reference_image_path, "rb") as f:
                img_bytes = f.read()
            char_image = types.Image(image_bytes=img_bytes, mime_type="image/png")
            logger.info(f"[Veo3] Using reference image as first & last frame: {reference_image_path}")

        # Call Veo 3 API
        generate_kwargs = dict(
            model="veo-3.1-fast-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=8,
                aspect_ratio="9:16",
                **({"last_frame": char_image} if char_image else {}),
            ),
        )
        if char_image:
            generate_kwargs["image"] = char_image

        operation = client.models.generate_videos(**generate_kwargs)

        # Poll until complete (run blocking poll in thread)
        result = await asyncio.to_thread(_poll_operation, client, operation)

        if not result or not result.generated_videos:
            logger.error("[Veo3] No videos in result")
            return None

        video = result.generated_videos[0]

        # Download video bytes
        video_bytes = video.video.video_bytes
        if not video_bytes:
            # Fetch via SDK download (accepts Video or GeneratedVideo)
            video_bytes = await asyncio.to_thread(
                lambda: client.files.download(file=video)
            )

        if not video_bytes:
            logger.error("[Veo3] Failed to get video bytes")
            return None

        if store is None:
            logger.warning("[DEPRECATED] generate_animation() called without store — use per-character store")
        _store = store or get_store()
        rel_path = _store.save_animation(state, video_bytes, ext=".mp4")

        logger.info(f"[Veo3] Animation saved: {rel_path}")
        return rel_path

    except Exception as e:
        logger.error(f"[Veo3] Generation failed: {e}", exc_info=True)
        return None


def _poll_operation(client: genai.Client, operation, timeout: int = 300):
    """Poll a long-running operation until completion."""
    start = time.time()
    logger.info(f"[Veo3] Polling operation: {operation.name}")
    while time.time() - start < timeout:
        try:
            op = client.operations.get(operation)
        except Exception as e:
            if "503" in str(e):
                elapsed = int(time.time() - start)
                logger.warning(f"[Veo3] 503 during poll ({elapsed}s), retrying...")
                time.sleep(10)
                continue
            raise
        if op.done:
            logger.info("[Veo3] Operation completed")
            return op.response if hasattr(op, "response") and op.response else op.result
        elapsed = int(time.time() - start)
        logger.info(f"[Veo3] Still generating... ({elapsed}s)")
        time.sleep(10)
    logger.error("[Veo3] Operation timed out")
    return None
