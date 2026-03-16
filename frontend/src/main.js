/**
 * Motif — main entry point.
 * Supports multiple characters per user.
 */

import { MotifSocket } from "./ws.js";
import { AnimationPlayer } from "./animation-player.js";
import { ChatUI } from "./chat-ui.js";
import { AudioPlayer } from "./audio-player.js";
import { Gallery } from "./gallery.js";
import { CharacterCreator } from "./character-creator.js";
import { Home } from "./home.js";

// ---- localStorage management ----

const STORAGE_KEY = "motif_session";

function loadData() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);

    // Migrate old format: { sessionId, characterImageUrl }
    if (data.sessionId && !data.userId) {
      const migrated = {
        userId: crypto.randomUUID(),
        characters: [
          {
            characterId: data.sessionId,
            imageUrl: data.characterImageUrl || "",
            description: "",
          },
        ],
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
      return migrated;
    }

    return data;
  } catch {
    return null;
  }
}

function saveData(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function ensureData() {
  let data = loadData();
  if (!data) {
    data = { userId: crypto.randomUUID(), characters: [] };
    saveData(data);
  }
  return data;
}

function addCharacter(characterId, imageUrl, description) {
  const data = ensureData();
  // Don't add duplicates
  if (!data.characters.find((c) => c.characterId === characterId)) {
    data.characters.push({ characterId, imageUrl, description });
    saveData(data);
  }
}

function removeCharacter(characterId) {
  const data = ensureData();
  data.characters = data.characters.filter((c) => c.characterId !== characterId);
  saveData(data);
}

// ---- Screen management ----

function showScreen(name) {
  document.getElementById("home").style.display = name === "home" ? "flex" : "none";
  document.getElementById("character-creator").style.display = name === "character-creator" ? "flex" : "none";
  document.getElementById("preparing-screen").style.display = name === "preparing-screen" ? "flex" : "none";
  document.getElementById("app").style.display = name === "app" ? "flex" : "none";
}

// ---- Initialize components ----

const data = ensureData();
const animation = new AnimationPlayer();
const audio = new AudioPlayer();
const gallery = new Gallery();
const home = new Home();

let socket = null;
let characterCreator = null;
let enteredChat = false;

// Dynamic basic states — populated from server's states_init
let basicStates = [];
let defaultState = null;
const readyStates = new Set();

// Chat needs a getter for the current socket
const chat = new ChatUI(() => socket);

// Connection status
const statusEl = document.getElementById("connection-status");

function bindSocketHandlers(sock) {
  sock.on("connected", () => {
    statusEl.textContent = "connected";
    statusEl.className = "connected";
  });

  sock.on("disconnected", () => {
    statusEl.textContent = "reconnecting...";
    statusEl.className = "disconnected";
  });

  sock.on("states_init", (msg) => {
    animation.initStates(msg.states);
    basicStates = [];
    defaultState = null;
    for (const [name, defn] of Object.entries(msg.states)) {
      if (defn.pre_generate) basicStates.push(name);
      if (defn.role === "rest") defaultState = name;
    }
    if (!defaultState && basicStates.length > 0) {
      defaultState = basicStates[0];
    }
    const progressEl = document.getElementById("preparing-progress");
    if (progressEl) {
      progressEl.textContent = `${readyStates.size} / ${basicStates.length}`;
    }
  });

  sock.on("states_updated", (msg) => {
    animation.initStates(msg.states);
  });

  sock.on("state_change", (msg) => {
    animation.setState(msg.state, msg.label, msg.animation_url);
  });

  sock.on("animation_ready", (msg) => {
    animation.registerAnimation(msg.state, msg.animation_url);

    if (enteredChat) {
      const label = animation.getStateLabel(msg.state) || msg.state;
      const color = animation.getStateColor(msg.state) || "var(--accent)";
      chat.addAnimationMessage(label, color);

      // Auto-play newly unlocked (non-basic) animations
      if (!basicStates.includes(msg.state)) {
        animation.setState(msg.state, label, msg.animation_url);
      }
    }

    if (basicStates.includes(msg.state)) {
      readyStates.add(msg.state);
      const progressEl = document.getElementById("preparing-progress");
      if (progressEl) {
        progressEl.textContent = `${readyStates.size} / ${basicStates.length}`;
      }
    }

    if (!enteredChat && defaultState && readyStates.has(defaultState)) {
      enteredChat = true;
      showScreen("app");
      animation.replayCurrentState();

      // Show unlock messages for animations that arrived before entering chat
      for (const state of readyStates) {
        const label = animation.getStateLabel(state) || state;
        const color = animation.getStateColor(state) || "var(--accent)";
        chat.addAnimationMessage(label, color);
      }
    }
  });

  sock.on("chat_history", (msg) => {
    chat.loadHistory(msg.messages);
  });

  sock.on("text_chunk", (msg) => {
    chat.appendAgentText(msg.text, msg.done);
  });

  sock.on("audio", (msg) => {
    audio.play(msg.data, msg.format);
  });

  sock.on("growth", (msg) => {
    gallery.updateGrowth(msg);
  });

  sock.on("error", (msg) => {
    console.error("Server error:", msg.message);
  });
}

// ---- Connect to a character ----

function connectToCharacter(characterId, imageUrl) {
  // Disconnect previous
  if (socket) socket.disconnect();

  // Reset UI state
  animation.reset();
  chat.clearMessages();
  enteredChat = false;
  basicStates = [];
  defaultState = null;
  readyStates.clear();

  // Create new socket and bind handlers
  socket = new MotifSocket(characterId);
  bindSocketHandlers(socket);

  animation.setCharacterImage(imageUrl);
  socket.connect();
}

// ---- Home page callbacks ----

home.onSelect((characterId, imageUrl) => {
  connectToCharacter(characterId, imageUrl);
  showScreen("app");
});

home.onCreate(() => {
  const newId = crypto.randomUUID();
  initCreator(newId, true);
  showScreen("character-creator");
});

home.onDelete(async (characterId) => {
  try {
    await fetch(`/api/characters/${characterId}`, { method: "DELETE" });
  } catch (err) {
    console.error("Delete error:", err);
  }
  removeCharacter(characterId);
  home.render(ensureData().characters);
});

// ---- Back-to-home button in #app ----

const backBtn = document.getElementById("back-to-home-btn");
if (backBtn) {
  backBtn.addEventListener("click", () => {
    if (socket) socket.disconnect();
    socket = null;
    enteredChat = false;
    showScreen("home");
    home.render(ensureData().characters);
  });
}

// ---- Character creator ----

function initCreator(characterId, showBack) {
  if (!characterCreator) {
    characterCreator = new CharacterCreator(characterId, data.userId);

    characterCreator.onConfirmed(({ characterId: cid, characterImageUrl, description }) => {
      addCharacter(cid, characterImageUrl, description);

      // Show preparing screen
      showScreen("preparing-screen");
      document.getElementById("preparing-character").src = characterImageUrl;

      connectToCharacter(cid, characterImageUrl);
    });

    characterCreator.onBack(() => {
      showScreen("home");
      home.render(ensureData().characters);
    });
  } else {
    characterCreator.setCharacterId(characterId);
    characterCreator.resetUI();
  }

  characterCreator.showBackButton(showBack);
}

// ---- Session restore ----

async function tryRestoreCharacter(characterId, imageUrl) {
  try {
    const resp = await fetch(`/api/characters/${characterId}/status`);
    const result = await resp.json();
    if (!result.ok) return false;

    // Character is valid — connect directly
    connectToCharacter(characterId, imageUrl);
    enteredChat = true;
    showScreen("app");
    return true;
  } catch {
    return false;
  }
}

// ---- Boot ----

(async function boot() {
  const stored = ensureData();

  if (stored.characters.length > 0) {
    // Show home screen with character list
    showScreen("home");
    home.render(stored.characters);
  } else {
    // No characters — go straight to creator
    const newId = crypto.randomUUID();
    initCreator(newId, false);
    showScreen("character-creator");
  }
})();
