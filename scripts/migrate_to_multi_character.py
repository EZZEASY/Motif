#!/usr/bin/env python3
"""One-time migration: restructure data from single-character to multi-character layout.

Old layout:
  data/characters/{session_id}/0.png, 1.png, upload.png  (images in root)
  data/animations/                                        (global animations dir)
  backend/animation/states.json                           (global states)

New layout:
  data/characters/{character_id}/
    meta.json
    images/0.png, 1.png, ...
    states.json
    animations/
      animations.json
      {state_name}/{uuid}.mp4

Usage:
  python -m scripts.migrate_to_multi_character
"""

import datetime
import json
import os
import shutil
import sys

# Resolve paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(PROJECT_ROOT, "backend", "data", "characters")
ANIMATIONS_DIR = os.path.join(PROJECT_ROOT, "backend", "data", "animations")
GLOBAL_STATES = os.path.join(PROJECT_ROOT, "backend", "animation", "states.json")


def find_character_dirs():
    """Find directories that look like character sessions (contain image files)."""
    if not os.path.isdir(CHARACTERS_DIR):
        return []
    dirs = []
    for name in os.listdir(CHARACTERS_DIR):
        d = os.path.join(CHARACTERS_DIR, name)
        if not os.path.isdir(d):
            continue
        # Check if it has images directly (old format) or already migrated
        has_images_in_root = any(
            os.path.isfile(os.path.join(d, f))
            for f in ("upload.png", "0.png", "1.png", "2.png", "3.png")
        )
        has_images_subdir = os.path.isdir(os.path.join(d, "images"))
        if has_images_in_root or has_images_subdir:
            dirs.append((name, d))
    return dirs


def migrate_character(char_id, char_dir):
    """Migrate a single character directory to the new layout."""
    print(f"\n--- Migrating character: {char_id} ---")

    # 1. Move images to images/ subdirectory
    images_dir = os.path.join(char_dir, "images")
    image_files = [f for f in ("upload.png", "0.png", "1.png", "2.png", "3.png")
                   if os.path.isfile(os.path.join(char_dir, f))]

    if image_files and not os.path.isdir(images_dir):
        os.makedirs(images_dir, exist_ok=True)
        for f in image_files:
            src = os.path.join(char_dir, f)
            dst = os.path.join(images_dir, f)
            print(f"  Moving {f} -> images/{f}")
            shutil.move(src, dst)
    elif image_files and os.path.isdir(images_dir):
        # images/ already exists, move any remaining root images
        for f in image_files:
            src = os.path.join(char_dir, f)
            dst = os.path.join(images_dir, f)
            if not os.path.isfile(dst):
                print(f"  Moving {f} -> images/{f}")
                shutil.move(src, dst)

    # 2. Copy global animations to character's animations/ subdirectory
    char_anim_dir = os.path.join(char_dir, "animations")
    if os.path.isdir(ANIMATIONS_DIR) and not os.path.isdir(char_anim_dir):
        print(f"  Copying global animations -> animations/")
        shutil.copytree(ANIMATIONS_DIR, char_anim_dir)
    elif os.path.isdir(ANIMATIONS_DIR) and os.path.isdir(char_anim_dir):
        print(f"  Character already has animations/, skipping")

    # 3. Copy global states.json
    char_states = os.path.join(char_dir, "states.json")
    if os.path.isfile(GLOBAL_STATES) and not os.path.isfile(char_states):
        print(f"  Copying global states.json")
        shutil.copy2(GLOBAL_STATES, char_states)

    # 4. Generate meta.json
    meta_path = os.path.join(char_dir, "meta.json")
    if not os.path.isfile(meta_path):
        # Determine selected image
        selected = None
        for f in ("upload.png", "0.png"):
            check_dir = images_dir if os.path.isdir(images_dir) else char_dir
            if os.path.isfile(os.path.join(check_dir, f)):
                selected = f
                break

        meta = {
            "user_id": "",
            "description": "",
            "selected_image": selected or "",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"  Created meta.json (selected_image={selected})")
    else:
        print(f"  meta.json already exists, skipping")

    print(f"  Done!")


def main():
    print("=== Motif Multi-Character Migration ===")
    print(f"Characters dir: {CHARACTERS_DIR}")
    print(f"Animations dir: {ANIMATIONS_DIR}")
    print(f"Global states:  {GLOBAL_STATES}")

    chars = find_character_dirs()
    if not chars:
        print("\nNo character directories found. Nothing to migrate.")
        return

    print(f"\nFound {len(chars)} character(s) to migrate:")
    for char_id, _ in chars:
        print(f"  - {char_id}")

    for char_id, char_dir in chars:
        migrate_character(char_id, char_dir)

    print("\n=== Migration complete! ===")
    print("You can now start the server. Old global animations/ and states.json")
    print("have been preserved (not deleted). Remove them manually when ready.")


if __name__ == "__main__":
    main()
