AKHIL AI - PHASE 1

1. Open backend/.env
2. Add your LLM API key.
3. Set the exact API base URL and model name for your provider.

Install:
    python -m venv venv
    venv\Scripts\activate
    pip install -r backend/requirements.txt

Run backend:
    cd backend
    uvicorn main:app --reload

Backend:
    http://127.0.0.1:8000

Frontend:
    Open frontend/index.html with VS Code Live Server.

Phase 1 includes:
- Basic ChatGPT-style UI
- FastAPI backend
- LLM API connection
- User/bot messages
- Typing indicator
- New Chat button
- Auto-scroll
- Responsive UI

Next phases:
- Better conversation history
- PDF upload + RAG
- Akhil personal knowledge base
- Memory
- Advanced file support
