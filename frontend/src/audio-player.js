/**
 * Audio player for TTS playback.
 * Day 3: Will handle base64 audio chunks from Chirp 3 HD.
 */

export class AudioPlayer {
  constructor() {
    this.queue = [];
    this.playing = false;
  }

  async play(base64Data, format = "mp3") {
    const blob = this.base64ToBlob(base64Data, `audio/${format}`);
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    return new Promise((resolve) => {
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.play().catch(() => resolve());
    });
  }

  base64ToBlob(base64, mimeType) {
    const bytes = atob(base64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    return new Blob([arr], { type: mimeType });
  }
}
