/**
 * Animation gallery — shows unlocked/locked animations.
 * Day 4: Will be fully implemented.
 */

export class Gallery {
  constructor() {
    this.animations = {};
  }

  updateGrowth(data) {
    const countEl = document.getElementById("growth-count");
    if (countEl && data.total_animations !== undefined) {
      countEl.textContent = data.total_animations;
    }
  }
}
