# Motif

**AI digital companion with generative animations**

Motif is an AI-powered digital companion platform that combines conversational AI with real-time generative animation. Create unique characters, chat with them, and watch them come alive through semantically-driven animations.

## Features

- **Character Creation** — Generate unique character images from text descriptions using Imagen 4, or upload your own
- **Conversational AI** — Natural dialogue powered by Gemini 2.5 Flash with long-term memory and persistent chat history
- **Semantic Animation** — Real-time animation generation via Veo 3, driven by conversation context and emotional states
- **Character Growth** — Characters evolve through a state system that reflects the conversation's emotional trajectory
- **Long-Term Memory** — ADK-managed sessions with persistent storage so characters remember past interactions

## Architecture

```
┌─────────────────┐         ┌─────────────────────────────────┐
│                 │  REST   │           Backend                │
│    Frontend     │◄───────►│          (FastAPI)               │
│   (Vite + JS)  │  + WS   │                                  │
│                 │         │  ┌─────────┐   ┌──────────────┐  │
└─────────────────┘         │  │  Agent   │   │  Animation   │  │
                            │  │  (ADK)   │   │   Router     │  │
                            │  └────┬─────┘   └──────┬───────┘  │
                            │       │                 │          │
                            └───────┼─────────────────┼──────────┘
                                    │                 │
                         ┌──────────▼──────────┐  ┌───▼──────────┐
                         │   Gemini 2.5 Flash  │  │    Veo 3     │
                         │   (Conversation)    │  │  (Animation) │
                         └─────────────────────┘  └──────────────┘
                                                  ┌──────────────┐
                                                  │   Imagen 4   │
                                                  │  (Character) │
                                                  └──────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vanilla JS + Vite |
| Backend | FastAPI + Uvicorn + WebSockets |
| Conversational AI | Gemini 2.5 Flash (via Google ADK) |
| Animation Generation | Veo 3 (via Gemini API) |
| Character Generation | Imagen 4 (via Gemini API) |
| Semantic Routing | Sentence-Transformers |
| Storage | Firestore + Google Cloud Storage |
| Image Processing | Pillow + rembg |

## Getting Started

### Prerequisites

- Python >= 3.13
- Node.js >= 20
- FFmpeg
- A Google Cloud project with Gemini API access

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/motif.git
   cd motif
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set at minimum:

   ```
   GOOGLE_GENAI_API_KEY=your-api-key
   ```

   See `.env.example` for the full list of configuration options (GCS bucket, Firestore database, etc.).

3. **Install dependencies**

   ```bash
   # Backend
   cd backend && pip install -e . && cd ..

   # Frontend
   cd frontend && npm install && cd ..
   ```

4. **Start the dev servers**

   ```bash
   ./start.sh
   ```

   This starts the backend on `http://localhost:8001` and the frontend on `http://localhost:5173`.

   Use `./start.sh --debug` to enable debug logging.

### Docker

```bash
docker build -t motif .
docker run -p 8080:8080 \
  -e GOOGLE_GENAI_API_KEY=your-api-key \
  motif
```

The app will be available at `http://localhost:8080`.

## Project Structure

```
motif/
├── backend/
│   ├── agent/          # ADK agent, tools, prompts, callbacks
│   ├── animation/      # Animation generation, semantic routing, state machine
│   ├── character/      # Character image generation & context
│   ├── storage/        # GCS & Firestore integration
│   ├── tts/            # Text-to-speech
│   ├── data/           # Local data storage (characters, animations)
│   ├── main.py         # FastAPI application entry point
│   └── config.py       # Configuration
├── frontend/
│   ├── src/            # JavaScript modules (chat, animation, WebSocket)
│   ├── styles/         # CSS
│   ├── public/         # Static assets
│   ├── index.html      # HTML entry point
│   └── vite.config.js  # Vite configuration
├── scripts/            # Utility scripts
├── start.sh            # One-command local development startup
├── Dockerfile          # Multi-stage production build
└── .env.example        # Environment variable template
```

## License

This project is licensed under the [MIT License](LICENSE).
