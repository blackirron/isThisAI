# IsThisAI

A "document examiner" style AI-content detector. Paste a passage or upload an
image, get a stamped verdict — AI-Generated or Human-Made — with a confidence
score and a plain-language rationale.

## What it does

**Text.** Sends the pasted text to an LLM (Groq by default, Claude as a
swap-in) with a prompt asking it to weigh linguistic signals of machine vs.
human writing, and parses a strict JSON verdict back into the stamp UI.

**Image.** Combines two independent evidence sources into one verdict:
1. **Deterministic forensics** — scans the file's own metadata for AI-tool
   fingerprints (embedded Stable Diffusion generation parameters, named
   generators like Midjourney/DALL-E/Firefly in EXIF/PNG text chunks, C2PA
   Content Credentials markers) and checks camera EXIF completeness.
2. **Vision-LLM judgment** — the same provider-swappable LLM looks at the
   image itself for visual tells (hands, text, lighting, texture) *with* the
   forensic findings given as context, so it isn't reasoning blind.

A strong metadata fingerprint overrides a contradicting visual read; the two
sources agreeing boosts confidence; if the LLM call fails, the app falls back
to a forensics-only verdict instead of erroring out.

## How it works

- `app/main.py` — wires routers + serves the static frontend
- `app/core/config.py` — env-based settings (provider, models, auth token)
- `app/core/security.py` — shared-secret gate via `X-Auth-Token`, enforced in production
- `app/routers/detect.py` — `/api/detect` — text verdict endpoint
- `app/routers/detect_image.py` — `/api/detect-image` — image verdict endpoint, fuses forensics + vision LLM
- `app/services/llm_client.py` — provider-switchable LLM calls, text and vision (`LLM_PROVIDER=groq|anthropic`)
- `app/services/image_forensics.py` — deterministic, non-LLM image metadata analysis
- `app/static/index.html` — the frontend (no build step, plain HTML/CSS/JS), Text and Image tabs

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
   (optionally `GROQ_VISION_MODEL` if Groq rotates their vision model id)
4. Deploy — health check is `/health`

**Before flipping to production:** neither frontend tab currently sends the
`X-Auth-Token` header that `verify_token` requires once `ENVIRONMENT` isn't
`development`. Decide how you want to handle that — have the frontend send
the token, swap the auth mechanism for browser traffic, or leave the UI open
and reserve the token for programmatic callers — before you deploy, or both
endpoints will 401 from the browser.

## Honest limitation

LLM-based AI-detection is inherently probabilistic and not forensically
reliable — treat the verdict as a second opinion, not proof. This applies to
both modes, but differently:

- **Text**: purely a model opinion. No ground truth to check it against.
- **Image**: the forensic layer is genuinely deterministic *when metadata is
  present and unstripped* — a Stable Diffusion parameters block or a named
  AI-tool signature is close to conclusive. But *absence* of that metadata
  proves nothing: screenshots, re-saves, and social-media exports strip EXIF
  from real photos just as readily as from AI images. The vision-LLM layer
  covering that gap is still a probabilistic opinion, same caveats as text.

Worth saying so explicitly in the UI (already done in the footer note) and in
any README you show a recruiter, since overclaiming accuracy here would
undercut the portfolio value more than the imperfect detector itself.

# IsThisAI

A "document examiner" style AI-content detector. Paste a passage or upload an
image, get a stamped verdict — AI-Generated or Human-Made — with a confidence
score and a plain-language rationale.

## What it does

**Text.** Sends the pasted text to an LLM (Groq by default, Claude as a
swap-in) with a prompt asking it to weigh linguistic signals of machine vs.
human writing, and parses a strict JSON verdict back into the stamp UI.

**Image.** Combines two independent evidence sources into one verdict:
1. **Deterministic forensics** — scans the file's own metadata for AI-tool
   fingerprints (embedded Stable Diffusion generation parameters, named
   generators like Midjourney/DALL-E/Firefly in EXIF/PNG text chunks, C2PA
   Content Credentials markers) and checks camera EXIF completeness.
2. **Vision-LLM judgment** — the same provider-swappable LLM looks at the
   image itself for visual tells (hands, text, lighting, texture) *with* the
   forensic findings given as context, so it isn't reasoning blind.

A strong metadata fingerprint overrides a contradicting visual read; the two
sources agreeing boosts confidence; if the LLM call fails, the app falls back
to a forensics-only verdict instead of erroring out.

## How it works

- `app/main.py` — wires routers + serves the static frontend
- `app/core/config.py` — env-based settings (provider, models, auth token)
- `app/core/security.py` — shared-secret gate via `X-Auth-Token`, enforced in production
- `app/routers/detect.py` — `/api/detect` — text verdict endpoint
- `app/routers/detect_image.py` — `/api/detect-image` — image verdict endpoint, fuses forensics + vision LLM
- `app/services/llm_client.py` — provider-switchable LLM calls, text and vision (`LLM_PROVIDER=groq|anthropic`)
- `app/services/image_forensics.py` — deterministic, non-LLM image metadata analysis
- `app/static/index.html` — the frontend (no build step, plain HTML/CSS/JS), Text and Image tabs

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
   (optionally `GROQ_VISION_MODEL` if Groq rotates their vision model id)
4. Deploy — health check is `/health`

**Before flipping to production:** neither frontend tab currently sends the
`X-Auth-Token` header that `verify_token` requires once `ENVIRONMENT` isn't
`development`. Decide how you want to handle that — have the frontend send
the token, swap the auth mechanism for browser traffic, or leave the UI open
and reserve the token for programmatic callers — before you deploy, or both
endpoints will 401 from the browser.

## Honest limitation

LLM-based AI-detection is inherently probabilistic and not forensically
reliable — treat the verdict as a second opinion, not proof. This applies to
both modes, but differently:

- **Text**: purely a model opinion. No ground truth to check it against.
- **Image**: the forensic layer is genuinely deterministic *when metadata is
  present and unstripped* — a Stable Diffusion parameters block or a named
  AI-tool signature is close to conclusive. But *absence* of that metadata
  proves nothing: screenshots, re-saves, and social-media exports strip EXIF
  from real photos just as readily as from AI images. The vision-LLM layer
  covering that gap is still a probabilistic opinion, same caveats as text.

Worth saying so explicitly in the UI (already done in the footer note) and in
any README you show a recruiter, since overclaiming accuracy here would

<img width="400" height="auto" alt="Screenshot from 2026-07-16 10-07-30" src="https://github.com/user-attachments/assets/779557ff-13b0-46ca-9088-8e9bf1305a81" />

<img width="400" height="auto" alt="Screenshot from 2026-07-16 10-06-37" src="https://github.com/user-attachments/assets/bda0a946-6b7b-45a3-85e4-549b685b90a4" />


