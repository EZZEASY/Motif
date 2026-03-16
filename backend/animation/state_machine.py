"""Dynamic state registry — replaces the old hardcoded AgentState enum.

States are persisted in states.json and can be added/updated/removed at runtime
by the Gemini Agent via the manage_states tool.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)


_DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "states.json")


class StateRegistry:
    """Thread-safe, JSON-backed registry of animation states."""

    def __init__(self, config_path: str = _DEFAULT_CONFIG):
        self._path = config_path
        self._lock = threading.Lock()
        self._states: dict[str, dict] = {}
        self._change_callbacks: list = []
        self._load()

    def on_change(self, callback) -> None:
        """Register a callback to be called when states change."""
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify all registered callbacks that states have changed."""
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception:
                logger.warning("State change callback failed", exc_info=True)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._states = json.load(f)
            logger.info(f"Loaded {len(self._states)} states from {self._path}")
        else:
            logger.warning(f"States file not found at {self._path}, starting empty")

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._states, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        label: str,
        prompt: str,
        color: str = "#7c5cff",
        tool_triggers: list[str] | None = None,
        pre_generate: bool = False,
        role: str | None = None,
    ) -> dict:
        """Add a new state. Raises ValueError if it already exists."""
        name = name.lower().strip().replace(" ", "_")
        with self._lock:
            if name in self._states:
                raise ValueError(f"State '{name}' already exists")
            definition = {
                "label": label,
                "prompt": prompt,
                "color": color,
                "pre_generate": pre_generate,
                "tool_triggers": tool_triggers or [],
            }
            if role:
                definition["role"] = role
            self._states[name] = definition
            self._save()
            logger.info(f"Registered new state: {name}")
        self._notify_change()
        return {"name": name, **definition}

    def update(self, name: str, **kwargs) -> dict:
        """Update fields of an existing state. Only supplied kwargs are changed."""
        with self._lock:
            if name not in self._states:
                raise ValueError(f"State '{name}' does not exist")
            for key in ("label", "prompt", "color", "pre_generate", "tool_triggers", "role"):
                if key in kwargs:
                    self._states[name][key] = kwargs[key]
            self._save()
            logger.info(f"Updated state: {name}")
        self._notify_change()
        return {"name": name, **self._states[name]}

    def remove(self, name: str) -> dict:
        """Remove a state."""
        with self._lock:
            if name not in self._states:
                raise ValueError(f"State '{name}' does not exist")
            removed = self._states.pop(name)
            self._save()
            logger.info(f"Removed state: {name}")
        self._notify_change()
        return {"name": name, **removed}

    def clear_all(self) -> None:
        """Remove all states (used before registering dynamically generated ones)."""
        with self._lock:
            self._states.clear()
            self._save()
            logger.info("Cleared all states")
        self._notify_change()

    # ------------------------------------------------------------------
    # Role-based lookups
    # ------------------------------------------------------------------

    def get_state_by_role(self, role: str) -> str | None:
        """Find the state name that has the given role (rest/processing/speaking)."""
        for name, defn in self._states.items():
            if defn.get("role") == role:
                return name
        return None

    def get_default_state(self) -> str | None:
        """Return the 'rest' role state (idle equivalent)."""
        return self.get_state_by_role("rest")

    def get_processing_state(self) -> str | None:
        """Return the 'processing' role state (thinking equivalent)."""
        return self.get_state_by_role("processing")

    def get_speaking_state(self) -> str | None:
        """Return the 'speaking' role state (talking equivalent)."""
        return self.get_state_by_role("speaking")

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    def get(self, name: str) -> dict | None:
        """Get a single state definition, or None."""
        return self._states.get(name)

    def get_all(self) -> dict:
        """Return the full state definitions dict (safe copy)."""
        return dict(self._states)

    def get_prompt(self, name: str) -> str | None:
        """Return the animation prompt, or None."""
        defn = self._states.get(name)
        if defn:
            return defn["prompt"]
        return None

    def get_label(self, name: str) -> str:
        """Return the display label, falling back to the name."""
        defn = self._states.get(name)
        return defn["label"] if defn else name.replace("_", " ").title() + "..."

    def get_tool_state(self, tool_name: str) -> str | None:
        """Reverse-lookup: given a tool function name, find the state it triggers."""
        for state_name, defn in self._states.items():
            if tool_name in defn.get("tool_triggers", []):
                return state_name
        return None

    def get_pre_generate_states(self) -> list[str]:
        """Return list of state names that should be pre-generated."""
        return [name for name, defn in self._states.items() if defn.get("pre_generate")]

    def is_valid(self, name: str) -> bool:
        return name in self._states
