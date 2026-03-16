"""Local file storage for animations — replaces GCS/Firestore for local dev."""

import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)


class LocalAnimationStore:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.metadata_path = os.path.join(base_dir, "animations.json")
        os.makedirs(base_dir, exist_ok=True)
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, list[dict]]:
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load animations.json, starting fresh")
        return {}

    def _save_metadata(self) -> None:
        with open(self.metadata_path, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def save_animation(self, state: str, video_bytes: bytes, ext: str = ".webm") -> str:
        """Save animation video to local filesystem. Returns the relative path."""
        state_dir = os.path.join(self.base_dir, state)
        os.makedirs(state_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(state_dir, filename)

        with open(file_path, "wb") as f:
            f.write(video_bytes)

        # Relative path from base_dir for URL serving
        rel_path = f"{state}/{filename}"

        if state not in self._metadata:
            self._metadata[state] = []
        self._metadata[state].append({"path": rel_path, "state": state})
        self._save_metadata()

        logger.info(f"Saved animation: {rel_path}")
        return rel_path

    def get_animations(self, state: str) -> list[str]:
        """Get list of animation paths for a given state."""
        entries = self._metadata.get(state, [])
        return [e["path"] for e in entries]

    def get_all_animations(self) -> dict[str, list[str]]:
        """Get all animations grouped by state."""
        return {
            state: [e["path"] for e in entries]
            for state, entries in self._metadata.items()
        }

    def get_total_count(self) -> int:
        return sum(len(v) for v in self._metadata.values())
