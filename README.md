# Chimp - Medieval Bazaar Language Learning

Voice-controlled 3D medieval bazaar for English language learning, powered by **Gemini 3 API** and **LangGraph**.

![Medieval Bazaar](https://via.placeholder.com/800x400?text=Medieval+Bazaar+3D+World)

## 🎮 Features

- **Voice-Controlled**: Speak to NPCs using natural English
- **3D World**: Immersive Three.js medieval bazaar scene
- **AI Agents**: LangGraph multi-agent system for intelligent responses
- **Grammar Learning**: Real-time feedback on grammar usage
- **Mission System**: Progressive challenges teaching grammar concepts

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Frontend                              │
│   React + Three.js + WebSocket + Web Speech API              │
└───────────────────────────┬──────────────────────────────────┘
                            │ WebSocket
┌───────────────────────────┴──────────────────────────────────┐
│                          Backend                              │
│   FastAPI + LangGraph + Gemini 3 API                         │
│                                                               │
│   ┌─────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐ │
│   │ Planner │→ │ Interpreter│→ │ Verifier │→ │  Executor  │ │
│   │ (Long   │  │ (Gemini    │  │ (Grammar │  │ (World     │ │
│   │ Context)│  │  Live API) │  │  Check)  │  │  Logic)    │ │
│   └─────────┘  └────────────┘  └──────────┘  └────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ or Bun
- Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### Backend

```bash
cd server
uv sync
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd client
bun install
bun run dev
```

Open http://localhost:5173 in your browser.

## 🎯 Missions

1. **Greet the Merchant**: Practice polite greetings
2. **Buy Apples**: Use quantity + politeness ("I would like to buy 3 apples, please")
3. **Negotiate**: Use conditionals ("If you lower the price, I will buy more")
4. **Explain Need**: Use causal reasoning ("I need bread because...")

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, Three.js, React Three Fiber |
| State | Zustand |
| Backend | Python 3.11+, FastAPI, WebSocket |
| AI | Gemini 3 API, LangGraph |
| Runtime | Bun, uv |

## 📜 License

MIT
