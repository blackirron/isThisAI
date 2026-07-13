# IsThisAI

A "document examiner" style AI-text detector. Paste a passage, get a stamped
verdict — AI-Generated or Human-Written — with a confidence score and a
one-line rationale.

## What it does
Sends the pasted text to an LLM (Groq by default, Claude as a swap-in) with a
prompt asking it to weigh linguistic signals of machine vs. human writing, and
parses a strict JSON verdict back into the stamp UI.

## How it works
- `app/main.py` — wires routers + serves the static frontend
- `app/routers/detect.py` — the `/api/detect` endpoint, prompt + JSON parsing
- `app/services/llm_client.py` — provider-switchable LLM call (`LLM_PROVIDER=groq|anthropic`)
- `app/static/index.html` — the frontend (no build step, plain HTML/CSS/JS)

## Run locally
```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env   # fill in GROQ_API_KEY
uvicorn app.main:app --reload
```
Visit http://localhost:8000

## Deploy (Render, same pattern as your other apps)
1. Push this to a new GitHub repo
2. Render → New → Web Service → connect repo → Docker
3. Environment variables: `GROQ_API_KEY`, `LLM_PROVIDER=groq`, `ENVIRONMENT=production`
4. Deploy — health check is `/health`

## Honest limitation
LLM-based AI-detection is inherently probabilistic and not forensically
reliable — treat the verdict as a second opinion, not proof. Worth saying so
explicitly in the UI (already done in the footer note) and in any README you
show a recruiter, since overclaiming accuracy here would undercut the
portfolio value more than the imperfect detector itself.
