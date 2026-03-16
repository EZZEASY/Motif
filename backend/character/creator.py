"""Character image generation using Imagen."""

import asyncio
import logging
import os
import time

from google import genai
from google.genai import types

from backend.config import GOOGLE_GENAI_API_KEY, LOCAL_CHARACTERS_DIR

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)
    return _client


def _retry_on_rate_limit(fn, *args, max_retries=5, **kwargs):
    """Retry a function call on 429/503 errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "503" in err_str) and attempt < max_retries - 1:
                wait = 2 ** attempt + 1
                logger.warning(f"[Imagen] Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


def _translate_to_english(description: str) -> str:
    """Use Gemini to translate the description to an English Imagen prompt."""
    client = _get_client()
    response = _retry_on_rate_limit(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=f"""Translate the following character description into a concise English prompt for an image generation model.
Only output the English prompt, nothing else. Keep it descriptive and vivid.

Description: {description}""",
    )
    english_prompt = response.text.strip()
    logger.info(f"[Imagen] Translated prompt: {english_prompt}")
    return english_prompt


def _generate_sync(session_id: str, description: str) -> list[str]:
    """Synchronous image generation (runs in thread)."""
    session_dir = os.path.join(LOCAL_CHARACTERS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    client = _get_client()

    # Translate to English for better Imagen results
    english_prompt = _translate_to_english(description)
    full_prompt = f"Character design, full body, {english_prompt}"

    response = _retry_on_rate_limit(
        client.models.generate_images,
        model="imagen-4.0-generate-001",
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=4,
            aspect_ratio="9:16",
        ),
    )

    paths = []
    for i, image in enumerate(response.generated_images):
        filename = f"{i}.png"
        filepath = os.path.join(session_dir, filename)
        image.image.save(filepath)
        rel_path = f"{session_id}/{filename}"
        paths.append(rel_path)
        logger.info(f"[Imagen] Saved character image: {filepath}")

    return paths


async def generate_character_images(session_id: str, description: str) -> list[str]:
    """Generate 4 character candidate images using Imagen.

    Returns a list of relative paths (relative to LOCAL_CHARACTERS_DIR).
    """
    if not GOOGLE_GENAI_API_KEY:
        logger.warning("[Imagen] No GOOGLE_GENAI_API_KEY configured")
        return []

    logger.info(f"[Imagen] Generating character images for session={session_id}: {description[:80]}")

    try:
        return await asyncio.to_thread(_generate_sync, session_id, description)
    except Exception as e:
        logger.error(f"[Imagen] Character generation failed: {e}", exc_info=True)
        return []
