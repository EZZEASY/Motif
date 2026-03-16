/**
 * Character creation UI — generates candidate images and lets user pick one.
 */
export class CharacterCreator {
  constructor(characterId, userId) {
    this.characterId = characterId;
    this.userId = userId || "";
    this.selectedIndex = null;

    this.creatorEl = document.getElementById("character-creator");
    this.inputEl = document.getElementById("character-input");
    this.generateBtn = document.getElementById("generate-character-btn");
    this.loadingEl = document.getElementById("character-loading");
    this.candidatesEl = document.getElementById("character-candidates");
    this.confirmBtn = document.getElementById("confirm-character-btn");
    this.themeSyncToggle = document.getElementById("theme-sync-toggle");
    this.themeSyncCheckbox = document.getElementById("theme-sync-checkbox");
    this.uploadInput = document.getElementById("character-upload-input");
    this.uploadWrapper = document.getElementById("character-upload-wrapper");
    this.divider = document.getElementById("character-divider");
    this.backBtn = document.getElementById("creator-back-btn");

    this._onConfirmed = null; // callback when character is confirmed
    this._onBack = null;

    this.generateBtn.addEventListener("click", () => this._onGenerate());
    this.inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") this._onGenerate();
    });
    this.confirmBtn.addEventListener("click", () => this._onConfirm());
    this.uploadInput.addEventListener("change", (e) => this._onUpload(e));
    this.themeSyncCheckbox.addEventListener("change", () => {
      if (this.themeSyncCheckbox.checked && this.selectedIndex !== null) {
        const imgs = this.candidatesEl.querySelectorAll(".character-candidate");
        this._applyThemeFromImage(imgs[this.selectedIndex]);
      } else {
        this._resetTheme();
      }
    });

    if (this.backBtn) {
      this.backBtn.addEventListener("click", () => {
        if (this._onBack) this._onBack();
      });
    }
  }

  setCharacterId(id) {
    this.characterId = id;
  }

  setUserId(id) {
    this.userId = id;
  }

  /** Register a callback for when character selection is confirmed.
   *  callback receives { characterId, characterImageUrl, description } */
  onConfirmed(callback) {
    this._onConfirmed = callback;
  }

  onBack(callback) {
    this._onBack = callback;
  }

  /** Show/hide the back button */
  showBackButton(show) {
    if (this.backBtn) {
      this.backBtn.style.display = show ? "block" : "none";
    }
  }

  /** Reset the creator UI for a fresh creation */
  resetUI() {
    this.selectedIndex = null;
    this.candidatesEl.innerHTML = "";
    this.confirmBtn.style.display = "none";
    this.themeSyncToggle.style.display = "none";
    this.inputEl.value = "";
    this.loadingEl.style.display = "none";
    if (this.divider) this.divider.style.display = "";
    if (this.uploadWrapper) this.uploadWrapper.style.display = "";
  }

  async _onGenerate() {
    const description = this.inputEl.value.trim();
    if (!description) return;

    this.generateBtn.disabled = true;
    this.loadingEl.style.display = "block";
    this.candidatesEl.innerHTML = "";
    this.confirmBtn.style.display = "none";
    this.themeSyncToggle.style.display = "none";
    if (this.divider) this.divider.style.display = "none";
    if (this.uploadWrapper) this.uploadWrapper.style.display = "none";
    this.selectedIndex = null;

    try {
      const resp = await fetch("/api/generate-character", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character_id: this.characterId,
          description,
          user_id: this.userId,
        }),
      });
      const data = await resp.json();

      if (!data.images || data.images.length === 0) {
        this.candidatesEl.innerHTML =
          '<p class="character-error">Generation failed. Please try again.</p>';
        return;
      }

      this._description = description;
      this._renderCandidates(data.images);
    } catch (err) {
      console.error("Character generation error:", err);
      this.candidatesEl.innerHTML =
        '<p class="character-error">Network error. Please try again.</p>';
    } finally {
      this.generateBtn.disabled = false;
      this.loadingEl.style.display = "none";
    }
  }

  async _onUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    this.loadingEl.textContent = "Uploading image...";
    this.loadingEl.style.display = "block";
    this.candidatesEl.innerHTML = "";
    this.confirmBtn.style.display = "none";
    this.selectedIndex = null;

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("character_id", this.characterId);
      formData.append("user_id", this.userId);

      const description = this.inputEl.value.trim();
      if (description) {
        formData.append("description", description);
      }

      const resp = await fetch("/api/upload-character", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();

      if (!data.ok) {
        this.candidatesEl.innerHTML =
          `<p class="character-error">${data.error || "Upload failed. Please try again."}</p>`;
        return;
      }

      // Directly confirm — skip candidate selection for uploads
      if (this._onConfirmed) {
        this._onConfirmed({
          characterId: this.characterId,
          characterImageUrl: data.character_image,
          description: description || "Uploaded character",
        });
      }
    } catch (err) {
      console.error("Upload error:", err);
      this.candidatesEl.innerHTML =
        '<p class="character-error">Network error. Please try again.</p>';
    } finally {
      this.loadingEl.style.display = "none";
      this.loadingEl.textContent = "Generating images...";
      this.uploadInput.value = "";
    }
  }

  _renderCandidates(imagePaths) {
    this.candidatesEl.innerHTML = "";
    imagePaths.forEach((path, index) => {
      const img = document.createElement("img");
      img.src = `${path}?t=${Date.now()}`;
      img.alt = `Candidate ${index + 1}`;
      img.className = "character-candidate";
      img.addEventListener("click", () => this._selectCandidate(index));
      this.candidatesEl.appendChild(img);
    });
    this.themeSyncToggle.style.display = "flex";
    if (this.divider) this.divider.style.display = "none";
    if (this.uploadWrapper) this.uploadWrapper.style.display = "none";
  }

  _selectCandidate(index) {
    this.selectedIndex = index;
    // Update visual selection
    const imgs = this.candidatesEl.querySelectorAll(".character-candidate");
    imgs.forEach((img, i) => {
      img.classList.toggle("selected", i === index);
    });
    this.confirmBtn.style.display = "block";

    // Extract dominant color from selected image and apply as theme
    if (this.themeSyncCheckbox.checked) {
      this._applyThemeFromImage(imgs[index]);
    }
  }

  _applyThemeFromImage(img) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const size = 64;
    canvas.width = size;
    canvas.height = size;
    ctx.drawImage(img, 0, 0, size, size);

    const data = ctx.getImageData(0, 0, size, size).data;

    // Sample edge pixels (top/bottom/left/right rows) to get background color
    const edgePixels = [];
    for (let x = 0; x < size; x++) {
      // top row
      const tIdx = (0 * size + x) * 4;
      edgePixels.push([data[tIdx], data[tIdx + 1], data[tIdx + 2]]);
      // bottom row
      const bIdx = ((size - 1) * size + x) * 4;
      edgePixels.push([data[bIdx], data[bIdx + 1], data[bIdx + 2]]);
    }
    for (let y = 0; y < size; y++) {
      // left column
      const lIdx = (y * size + 0) * 4;
      edgePixels.push([data[lIdx], data[lIdx + 1], data[lIdx + 2]]);
      // right column
      const rIdx = (y * size + (size - 1)) * 4;
      edgePixels.push([data[rIdx], data[rIdx + 1], data[rIdx + 2]]);
    }

    // Average edge pixels to get background color
    let r = 0, g = 0, b = 0;
    for (const [pr, pg, pb] of edgePixels) {
      r += pr; g += pg; b += pb;
    }
    const n = edgePixels.length;
    r = Math.round(r / n);
    g = Math.round(g / n);
    b = Math.round(b / n);

    // Derive theme colors from the dominant background color
    const root = document.documentElement.style;
    // Dark version for page background
    const darkR = Math.round(r * 0.08);
    const darkG = Math.round(g * 0.08);
    const darkB = Math.round(b * 0.08);
    root.setProperty("--bg-dark", `rgb(${darkR}, ${darkG}, ${darkB})`);

    // Slightly lighter for cards
    const cardR = Math.round(r * 0.14);
    const cardG = Math.round(g * 0.14);
    const cardB = Math.round(b * 0.14);
    root.setProperty("--bg-card", `rgb(${cardR}, ${cardG}, ${cardB})`);

    // Input background
    const inputR = Math.round(r * 0.20);
    const inputG = Math.round(g * 0.20);
    const inputB = Math.round(b * 0.20);
    root.setProperty("--bg-input", `rgb(${inputR}, ${inputG}, ${inputB})`);

    // Accent color — a brighter, saturated version
    const max = Math.max(r, g, b, 1);
    const accentR = Math.min(255, Math.round((r / max) * 200 + 55));
    const accentG = Math.min(255, Math.round((g / max) * 200 + 55));
    const accentB = Math.min(255, Math.round((b / max) * 200 + 55));
    root.setProperty("--accent", `rgb(${accentR}, ${accentG}, ${accentB})`);
    root.setProperty("--accent-glow", `rgba(${accentR}, ${accentG}, ${accentB}, 0.3)`);

    // Auto text color based on accent luminance
    const accentLum = (accentR * 299 + accentG * 587 + accentB * 114) / 1000;
    root.setProperty("--accent-text", accentLum > 160 ? "#000" : "#fff");
  }

  _resetTheme() {
    const root = document.documentElement.style;
    root.removeProperty("--bg-dark");
    root.removeProperty("--bg-card");
    root.removeProperty("--bg-input");
    root.removeProperty("--accent");
    root.removeProperty("--accent-glow");
    root.removeProperty("--accent-text");
  }

  async _onConfirm() {
    if (this.selectedIndex === null) return;

    this.confirmBtn.disabled = true;
    try {
      const resp = await fetch("/api/select-character", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character_id: this.characterId,
          image_index: this.selectedIndex,
        }),
      });
      const data = await resp.json();

      if (data.ok) {
        if (this._onConfirmed) {
          this._onConfirmed({
            characterId: this.characterId,
            characterImageUrl: data.character_image,
            description: this._description || "",
          });
        }
      }
    } catch (err) {
      console.error("Character selection error:", err);
    } finally {
      this.confirmBtn.disabled = false;
    }
  }
}
