"""Generate seed animations using Veo 3.
Day 2: Will be implemented with actual Veo 3 API calls.
"""

SEED_PROMPTS = {
    "idle": "A small glowing purple orb floating gently in place against a bright green screen background, subtle breathing animation, magical particle effects, 4 seconds loop",
    "thinking": "A small glowing orange orb pulsing rhythmically against a bright green screen background, with spinning rings around it, contemplative mood, 4 seconds loop",
    "searching": "A small glowing blue orb bouncing energetically against a bright green screen background, with scanning light beams emanating from it, 4 seconds loop",
    "drawing": "A small glowing pink orb wobbling creatively against a bright green screen background, with colorful paint splashes appearing around it, 4 seconds loop",
    "teaching": "A small glowing green orb with a gentle expanding aura against a bright green screen background, wise and calm energy, 4 seconds loop",
    "performing": "A small glowing yellow orb bouncing and spinning joyfully against a bright green screen background, with sparkle effects, 4 seconds loop",
    "talking": "A small glowing purple orb with mouth-like pulsing animation against a bright green screen background, expressive and friendly, 4 seconds loop",
    "celebrating": "A small rainbow-colored orb spinning and expanding with firework-like particles against a bright green screen background, triumphant energy, 4 seconds loop",
}


def main():
    print("Seed animation prompts:")
    for state, prompt in SEED_PROMPTS.items():
        print(f"\n[{state}]")
        print(f"  {prompt}")
    print("\nVeo 3 generation will be implemented in Day 2.")


if __name__ == "__main__":
    main()
