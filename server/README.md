# Chimp Server - Agentic Language Simulation

Real-time speech-controlled medieval bazaar using **Gemini 3 API** and **LangGraph**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent System                    │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│  Planner    │ Interpreter │   Verifier  │    Executor      │
│  (Mission)  │ (Audio→JSON)│ (Validate)  │ (World Logic)    │
└─────────────┴─────────────┴─────────────┴──────────────────┘
                           ↑
                    WebSocket API
                           ↑
                      FastAPI Server
```

## Quick Start

1. **Install dependencies:**
   ```bash
   cd server
   uv sync
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. **Run server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

4. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:8000/

   # Create session
   curl -X POST http://localhost:8000/api/session
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/session` | POST | Create new session |
| `/api/session/{id}` | GET | Get session state |
| `/api/session/{id}` | DELETE | Delete session |
| `/ws/{session_id}` | WS | Real-time communication |

## WebSocket Messages

### Incoming (Client → Server)
```json
{"type": "transcript", "text": "I would like to buy apples", "is_final": true}
{"type": "ping"}
```

### Outgoing (Server → Client)
```json
{"type": "world_state", "state": {...}}
{"type": "action_result", "parsed_action": {...}, "feedback": [...]}
{"type": "reasoning", "agent": "interpreter", "step": "speech_to_action", ...}
{"type": "error", "message": "...", "recoverable": true}
```

## Project Structure

```
server/
├── app/
│   ├── main.py          # FastAPI + WebSocket
│   ├── config.py        # Environment config
│   ├── models.py        # Pydantic schemas
│   ├── agents/
│   │   ├── graph.py     # LangGraph orchestration
│   │   ├── interpreter.py  # Gemini speech→action
│   │   ├── planner.py   # Mission generation
│   │   ├── verifier.py  # Validation
│   │   └── executor.py  # World logic
│   └── memory/
│       └── __init__.py  # Session store
└── pyproject.toml
```

## Debug Endpoint

In development mode, test transcript processing without WebSocket:

```bash
curl -X POST "http://localhost:8000/api/debug/process?session_id=test&transcript=Hello"
```
