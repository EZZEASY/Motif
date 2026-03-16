/**
 * Animation player — game-style state machine for character animation.
 *
 * Priority: state video > character static image > CSS orb animation.
 * Videos loop continuously. State changes swap which video is playing.
 *
 * Dynamic CSS generation: state definitions received from the server are used
 * to create per-state CSS rules (glow color, orb gradient, animations) on the
 * fly so that newly created states get visual feedback immediately.
 */

export class AnimationPlayer {
  constructor() {
    this.body = document.getElementById("motif-body");
    this.label = document.getElementById("state-label");
    this.video = document.getElementById("motif-video");
    this.characterImg = document.getElementById("motif-character");
    this.currentState = "idle";
    this.characterImageUrl = null;

    // Cache of animation URLs per state: { "idle": "/animations/idle/xxx.webm", ... }
    this.animationCache = {};

    // Playback queue: wait for current animation to finish one loop before switching
    this._queue = [];       // pending state entries [{state, label, animationUrl}]
    this._playing = false;  // true while a non-looping video is playing through
    this._cssTimer = null;  // timer for CSS-only states minimum display time

    // Dynamic <style> element for generated state rules
    this._dynamicStyle = document.createElement("style");
    this._dynamicStyle.id = "dynamic-state-styles";
    document.head.appendChild(this._dynamicStyle);

    // Track which states already have CSS generated
    this._generatedStates = new Set();
  }

  // -----------------------------------------------------------------
  // Dynamic CSS generation from state definitions
  // -----------------------------------------------------------------

  /**
   * Receive state definitions from the server and generate CSS rules.
   * Called on both `states_init` and `states_updated`.
   */
  initStates(stateDefinitions) {
    if (!stateDefinitions) return;

    // Save definitions for label/color lookups
    this.stateDefinitions = stateDefinitions;

    let css = "";
    for (const [name, defn] of Object.entries(stateDefinitions)) {
      css += this._generateStateCSS(name, defn.color || "#7c5cff");
      this._generatedStates.add(name);
    }
    // Replace all dynamic rules at once
    this._dynamicStyle.textContent = css;
  }

  getStateLabel(state) {
    return this.stateDefinitions?.[state]?.label || null;
  }

  getStateColor(state) {
    return this.stateDefinitions?.[state]?.color || null;
  }

  /**
   * Generate CSS rules for a single state based on its color.
   */
  _generateStateCSS(name, hexColor) {
    const glow = this._hexToRgba(hexColor, 0.3);
    const glowStrong = this._hexToRgba(hexColor, 0.4);
    const glowWeak = this._hexToRgba(hexColor, 0.2);
    const darker = this._darkenHex(hexColor, 0.3);

    // Pick an animation style based on a simple hash of the name
    const animStyle = this._pickAnimation(name);

    return `
/* State: ${name} */
.state-${name} .motif-orb {
  animation: ${animStyle.orb} infinite;
  background: radial-gradient(circle at 30% 30%, ${hexColor}, ${darker});
  box-shadow: 0 0 40px ${glow};
}
.state-${name} .motif-ring {
  animation: ${animStyle.ring} infinite;
  border-color: ${hexColor};
  opacity: ${animStyle.ringOpacity};
}
.state-${name} .motif-particles {
  animation: ${animStyle.particles} infinite;
  border-color: ${glowWeak};
}
`;
  }

  /**
   * Pick a pre-defined animation combo based on state name.
   * Uses the built-in @keyframes from main.css as a library.
   */
  _pickAnimation(name) {
    // Predefined mappings for the 8 original states
    const presets = {
      idle:        { orb: "idle-pulse 3s ease-in-out",        ring: "idle-ring 4s linear",             particles: "idle-ring 6s linear reverse",        ringOpacity: 0.3 },
      thinking:    { orb: "thinking-pulse 1s ease-in-out",    ring: "thinking-spin 1.5s linear",       particles: "thinking-spin 3s linear reverse",    ringOpacity: 0.5 },
      searching:   { orb: "searching-bounce 0.6s ease-in-out", ring: "searching-scan 1s linear",      particles: "idle-ring 3s linear",                ringOpacity: 0.6 },
      drawing:     { orb: "drawing-wobble 1.2s ease-in-out",  ring: "drawing-expand 2s ease-in-out",   particles: "idle-ring 4s linear reverse",        ringOpacity: 0.4 },
      teaching:    { orb: "teaching-glow 2s ease-in-out",     ring: "idle-ring 3s linear",             particles: "idle-ring 5s linear reverse",        ringOpacity: 0.5 },
      performing:  { orb: "performing-bounce 0.4s ease-in-out", ring: "thinking-spin 0.8s linear",     particles: "thinking-spin 1.5s linear reverse",  ringOpacity: 0.7 },
      talking:     { orb: "talking-pulse 0.8s ease-in-out",   ring: "idle-ring 2s linear",             particles: "idle-ring 4s linear",                ringOpacity: 0.5 },
      celebrating: { orb: "celebrating-spin 0.5s linear",     ring: "celebrating-expand 1s ease-out",  particles: "thinking-spin 1s linear reverse",    ringOpacity: 0.8 },
    };

    if (presets[name]) return presets[name];

    // For dynamically created states, cycle through animation combos
    const orbAnims = [
      "idle-pulse 2.5s ease-in-out",
      "thinking-pulse 1.2s ease-in-out",
      "searching-bounce 0.8s ease-in-out",
      "drawing-wobble 1.5s ease-in-out",
      "teaching-glow 2s ease-in-out",
      "talking-pulse 1s ease-in-out",
      "performing-bounce 0.5s ease-in-out",
    ];
    const ringAnims = [
      "idle-ring 3s linear",
      "thinking-spin 2s linear",
      "searching-scan 1.5s linear",
      "drawing-expand 2.5s ease-in-out",
    ];

    const hash = this._simpleHash(name);
    return {
      orb: orbAnims[hash % orbAnims.length],
      ring: ringAnims[hash % ringAnims.length],
      particles: "idle-ring " + (3 + (hash % 4)) + "s linear reverse",
      ringOpacity: 0.3 + (hash % 5) * 0.1,
    };
  }

  _simpleHash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) - h + str.charCodeAt(i)) | 0;
    }
    return Math.abs(h);
  }

  _hexToRgba(hex, alpha) {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  _darkenHex(hex, amount) {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const r = Math.max(0, Math.round(parseInt(hex.substring(0, 2), 16) * (1 - amount)));
    const g = Math.max(0, Math.round(parseInt(hex.substring(2, 4), 16) * (1 - amount)));
    const b = Math.max(0, Math.round(parseInt(hex.substring(4, 6), 16) * (1 - amount)));
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }

  // -----------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------

  /**
   * Reset all animation state — used when switching characters.
   */
  reset() {
    this.animationCache = {};
    this._queue = [];
    this._playing = false;
    clearTimeout(this._cssTimer);
    this._stopVideo();
    this.body.className = "state-idle";
    this.body.classList.remove("has-video", "has-character");
    this.label.textContent = "";
    this.currentState = "idle";
    this.characterImageUrl = null;
    this.characterImg.src = "";
  }

  // -----------------------------------------------------------------
  // Existing methods
  // -----------------------------------------------------------------

  /**
   * Set the character static image (shown as fallback when no video).
   */
  setCharacterImage(url) {
    this.characterImageUrl = url;
    this.characterImg.src = url;
    // Show character image, hide CSS orb
    this.body.classList.add("has-character");
  }

  /**
   * Register a ready animation for a state (pushed from server).
   * If it's the current state, play it immediately.
   */
  registerAnimation(state, url) {
    this.animationCache[state] = url;
    // If we're currently in this state, swap to video now
    if (state === this.currentState) {
      this._playVideo(url);
      this.body.classList.add("has-video");
    }
  }

  /**
   * Transition to a new state.
   * Instead of switching immediately, enqueue the state and let the current
   * animation finish one full loop before transitioning.
   */
  setState(state, labelText, animationUrl) {
    // Cache the URL if provided
    if (animationUrl) {
      this.animationCache[state] = animationUrl;
    }

    this._queue.push({ state, label: labelText, animationUrl });
    this._processQueue();
  }

  /**
   * Process the playback queue. Only starts a transition if no video is
   * currently playing through its loop. Queue entries are merged: only the
   * last pending state is played, intermediate states are skipped.
   */
  _processQueue() {
    // Still playing through a loop — `ended` will call us again
    if (this._playing) return;

    // Nothing to do
    if (this._queue.length === 0) {
      // Current video should loop indefinitely while idle
      if (this.video.src && !this.video.paused) {
        this.video.loop = true;
      }
      return;
    }

    // Take the first entry in order — play every state sequentially
    const entry = this._queue.shift();

    // Apply CSS class + label
    this._applyState(entry.state, entry.label);

    // Play video or handle CSS-only state
    const videoUrl = this.animationCache[entry.state];
    if (videoUrl) {
      this.body.classList.add("has-video");
      this._playVideo(videoUrl);
    } else {
      // No video for this state — keep current video visible if playing
      if (this.video.src && !this.video.paused) {
        this.body.classList.add("has-video");
        this.video.loop = true;
      }
      // CSS-only state: show for a minimum of 2 seconds before allowing next
      this._playing = true;
      clearTimeout(this._cssTimer);
      this._cssTimer = setTimeout(() => {
        this._playing = false;
        this._processQueue();
      }, 2000);
    }
  }

  /**
   * Apply CSS state class and label text without touching video.
   */
  _applyState(state, labelText) {
    const classes = [`state-${state}`];
    if (this.characterImageUrl) classes.push("has-character");
    // has-video will be added by the caller if needed
    this.body.className = classes.join(" ");
    this.currentState = state;
    this.label.textContent = labelText || state.replace(/_/g, " ").toUpperCase();
  }

  /**
   * Re-trigger the current state's video (e.g. after the container becomes visible).
   */
  replayCurrentState() {
    const videoUrl = this.animationCache[this.currentState];
    if (videoUrl) {
      this.body.classList.add("has-video");
      this._playVideo(videoUrl, true);
    }
  }

  _playVideo(url, force = false) {
    // Avoid restarting the same video (unless forced)
    if (!force && this.video.src.endsWith(url) && !this.video.paused) return;

    // Clear any CSS-only timer since we're now playing a video
    clearTimeout(this._cssTimer);

    this.video.src = url;
    this.video.muted = true;

    // Play one loop then let the queue decide what's next
    this.video.loop = false;
    this._playing = true;

    // Remove any previous listener to avoid stacking
    this.video.removeEventListener("ended", this._onVideoEnded);
    this._onVideoEnded = () => {
      this._playing = false;
      if (this._queue.length > 0) {
        // Next state is queued — process it
        this._processQueue();
      } else {
        // Nothing queued — loop the current video
        this.video.loop = true;
        this.video.play().catch(() => {});
      }
    };
    this.video.addEventListener("ended", this._onVideoEnded);

    const playPromise = this.video.play();
    if (playPromise) {
      playPromise.catch((e) => {
        console.warn("Video play failed, falling back:", e);
        this._playing = false;
        this.body.classList.remove("has-video");
        this._processQueue();
      });
    }
  }

  _stopVideo() {
    this.video.pause();
    this.video.src = "";
  }
}
