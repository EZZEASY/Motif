/**
 * Home page — character grid with create/delete functionality.
 */

export class Home {
  constructor() {
    this.el = document.getElementById("home");
    this.grid = document.getElementById("character-grid");
    this.createBtn = document.getElementById("create-character-btn");
    this.subtitle = document.getElementById("home-subtitle");

    this._onSelectCb = null;
    this._onCreateCb = null;
    this._onDeleteCb = null;

    this.createBtn.addEventListener("click", () => {
      if (this._onCreateCb) this._onCreateCb();
    });
  }

  onSelect(callback) {
    this._onSelectCb = callback;
  }

  onCreate(callback) {
    this._onCreateCb = callback;
  }

  onDelete(callback) {
    this._onDeleteCb = callback;
  }

  render(characters) {
    this.grid.innerHTML = "";

    if (!characters || characters.length === 0) {
      this.subtitle.textContent = "Create your first AI companion";
      this.createBtn.textContent = "Create Your First Character";
      return;
    }

    this.subtitle.textContent = "Your AI Companions";
    this.createBtn.textContent = "+ Create New Character";

    for (const char of characters) {
      const card = document.createElement("div");
      card.className = "character-card";
      card.innerHTML = `
        <div class="character-card-image-wrapper">
          <img src="${char.imageUrl}?t=${Date.now()}" alt="Character" class="character-card-image" />
          <button class="character-card-delete" title="Delete character">&times;</button>
        </div>
        <div class="character-card-info">
          <span class="character-card-desc">${this._truncate(char.description, 40)}</span>
        </div>
      `;

      // Click card → select
      card.querySelector(".character-card-image-wrapper").addEventListener("click", (e) => {
        // Don't trigger select when clicking delete
        if (e.target.closest(".character-card-delete")) return;
        if (this._onSelectCb) {
          this._onSelectCb(char.characterId, char.imageUrl);
        }
      });

      // Delete button
      card.querySelector(".character-card-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        if (confirm("Delete this character? This cannot be undone.")) {
          if (this._onDeleteCb) this._onDeleteCb(char.characterId);
        }
      });

      this.grid.appendChild(card);
    }
  }

  show() {
    this.el.style.display = "flex";
  }

  hide() {
    this.el.style.display = "none";
  }

  _truncate(str, len) {
    if (!str) return "Unnamed character";
    return str.length > len ? str.slice(0, len) + "..." : str;
  }
}
