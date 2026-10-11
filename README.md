# NimbleBuddy 🌐
> **Your AI Internet Buddy — speak a task, and it gets done on the live web via Nimble.**
> Built for the **AI Engineer NYC 2026** Hackathon · Competing for **Best Use of Nimble**.

**Pitch in one line:** *Other assistants guess. NimbleBuddy dispatches Nimble Web Search Agents that browse the live web and return every claim with a citation and a confidence score.*

---

## 🌟 What it does

| # | Capability | Try saying | Nimble product |
|---|---|---|---|
| 1 | 🤖 **Autonomous web agent** | "Use an agent to compare Nimble vs Bright Data for AI scraping" | **Web Search Agent** (`agents.run`): multi-step browsing, cited claims with confidence |
| 2 | 🛍️ **Live price comparison** | "Find the best noise cancelling headphones under $200" | **Search** + **Answer** restricted to retailer & review sites (~3 s) |
| 3 | 🌐 **Live answers** | "What's new in AI today?" | **Search** + **Answer** (`include_answer=True`, `focus="news"`) |
| 4 | 📄 **Read any page** | "Summarize https://docs.nimbleway.com" | **Extract** (`render=True`, Markdown) |
| 5 | 🔬 **Fast research** | "Research the history of web scraping" | Search + parallel Extract of top sources |
| 6 | ✉️ **Email it** | "Email that summary to judge@example.com" | Builds a `mailto:` draft; nothing is sent automatically |
| 7 | 🎙️ **Voice in, voice out** | Click the mic, speak, click again | Browser recording → **Groq Whisper** (`whisper-large-v3-turbo`) via `POST /api/transcribe`; reply rewritten into 1–2 casual spoken sentences (`gpt-oss-20b`) and voiced by **Orpheus TTS** on Groq (`POST /api/speak`), falling back to the browser voice. Works in Chrome, Safari, Edge, Firefox |

---

## ✅ Step-by-step: from zero to demo

### Step 1 — Get the code
```bash
git clone https://github.com/vim719/Nimble-Buddy.git
cd Nimble-Buddy
```

### Step 2 — Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Requires Python 3.10+ (tested on 3.14).

### Step 3 — Add your keys securely
```bash
cp .env.example .env
chmod 600 .env
open -e .env        # macOS; or use any editor
```
Fill in:
```bash
NIMBLE_API_KEY=...   # https://online.nimbleway.com/settings/api-keys
GROQ_API_KEY=...     # optional, free at https://console.groq.com
GROQ_MODEL=openai/gpt-oss-120b
```

**Key safety rules**
- `.env` is git-ignored (along with `.env.*`, `*.pem`, `*.key`); only `.env.example` with placeholders is committed.
- Never paste keys into chat, issues, screenshots, or the frontend. The browser never sees them; only the FastAPI backend reads `.env`.
- `GET /api/status` reports `live`/`sandbox` and never returns key values.
- Before every push, run `git status` and confirm `.env` is not listed.
- If a key is ever exposed, revoke it in the Nimble dashboard immediately and create a new one.

### Step 4 — Verify the keys work
```bash
uvicorn app.main:app --port 8000
```
In another terminal:
```bash
curl -s localhost:8000/api/status
```
Expected: `{"nimble":"live","llm":"groq"}`. If it says `sandbox`, the Nimble key is missing or still the placeholder. Without a Groq key the app still works using a keyword-based planner (`"llm":"rule-based planner"`).

### Step 5 — Smoke-test each tool once
Open **http://localhost:8000** and run, in order:
1. "What's new in AI today?" → expect real links + a short answer.
2. "Find the best noise cancelling headphones under $200" → expect real store links.
3. "Use an agent to compare Nimble vs Bright Data for AI web scraping" → wait 30–120 s → expect cited claims.

If step 3 is slow, keep effort at `low` (the default). Run it once **before** going on stage so you know the timing.

### Step 6 — Rehearse the demo (2 minutes, see script below)

### Step 6½ — (Optional) Share a public demo link with Cloudflare Tunnel
Give judges a live HTTPS link they can open on their own phones — **free, no Cloudflare account, no API key**. The app keeps running on your laptop, so your keys never leave `.env`.

**How it works:** a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) opens an outbound connection from your machine to Cloudflare and gives you a random `https://<words>.trycloudflare.com` URL that forwards to `localhost:8000`. No ports are opened on your router.

```
Judge's phone ──HTTPS──▶ Cloudflare edge ──tunnel──▶ cloudflared (your laptop) ──▶ localhost:8000 (NimbleBuddy)
```

1. Install `cloudflared` once:
   ```bash
   brew install cloudflared
   ```
   (Windows/Linux: [download page](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/))
2. Start the app (terminal 1):
   ```bash
   ./venv/bin/uvicorn app.main:app --port 8000
   ```
3. Start the tunnel (terminal 2):
   ```bash
   ./scripts/share.sh
   ```
   It checks the app is running, then prints a URL like `https://example-words-here.trycloudflare.com`. Equivalent raw command:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
4. Open the URL on your phone to confirm it works, then share it (submission form, QR code on screen, etc.).
5. Press **Ctrl+C** in terminal 2 when the demo ends. The URL stops working immediately.

**Things to know**
- ⚠️ Anyone with the URL can use your **Nimble credits** and **Groq quota**. Share it only during judging and stop it afterwards.
- The URL is **random and changes every run** — don't print it in slides ahead of time.
- Quick Tunnels are for testing/demos: no uptime guarantee and a cap on concurrent requests. For a permanent URL, create a named tunnel with a free Cloudflare account (`cloudflared tunnel login`).
- The microphone works over the tunnel because the link is HTTPS (browsers block mic access on plain HTTP).
- If the tunnel shows a Cloudflare `502`, the app isn't running on port 8000 — restart it in terminal 1.

### Step 7 — Record the demo video and submit
- MLH requires ≤ 2 minutes, starting with: *"Hey, I'm [Your Name], and this is my demo for AI Engineer NYC 2026."*
- Show the live product, not slides.
- Submit the public repo link and video.

---

## 🎬 2-minute demo script

| Time | Action | What to say |
|---|---|---|
| 0:00 | Title screen | "Hey, I'm ___, and this is NimbleBuddy for AI Engineer NYC 2026. It's a voice assistant that does real work on the live web using Nimble." |
| 0:10 | 🎙️ Say: *"Find the best noise cancelling headphones under $200"* | "Nimble Search in shopping mode pulls live prices from real stores — no stale training data." |
| 0:35 | Type: *"Use an agent to compare Nimble vs Bright Data for AI web scraping"* | "This dispatches a Nimble Web Search Agent. It plans, browses multiple sites, and verifies." |
| 0:50 | While waiting, open the **Execution Inspector** | "You can see exactly which Nimble tool ran with which parameters." |
| 1:20 | Agent result appears | "Every claim comes back with a citation and a confidence score. That's the difference between an assistant that guesses and one you can trust." |
| 1:40 | Say: *"Email that summary to my team"* | "And it packages the findings into an email draft, ready to send." |
| 1:55 | Close | "NimbleBuddy: the live web, on voice command, with receipts." |

**Backup plan:** if the agent is slow on stage, pre-run the agent query and keep that tab open; demo search + shopping live.

---

## 🏗️ Architecture

```
User (Voice / Text)
       │
       ▼
┌───────────────────────────────────────────────┐
│  Frontend (frontend/) — HTML + JS             │
│  - Web Speech API (local microphone)          │
│  - Execution Inspector & source citations     │
└───────────────────────┬───────────────────────┘
                        │ POST /api/chat   GET /api/status
                        ▼
┌───────────────────────────────────────────────┐
│  FastAPI backend (app/main.py, app/routes.py) │
│  - Reads secrets from .env (server-side only) │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│  Agent brain (app/agent.py)                   │
│  - Groq Llama 3.3 70B picks a tool            │
│  - Rule-based planner if no Groq key          │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│  Nimble toolkit (app/nimble_tools.py)         │
│  - search(focus=general|news|shopping,        │
│           include_answer=True)                │
│  - extract.run(render=True, markdown)         │
│  - agents.run → runs.get (poll) → runs.result │
│  - mailto: email drafts                       │
└───────────────────────────────────────────────┘
```

### Nimble API usage

| Tool | SDK call | Notes |
|---|---|---|
| `web_search` | `client.search(query, focus, include_answer=True)` | Returns answer + results (`title`, `url`, `description`) |
| `shop_search` | `client.search(query, include_answer=True, include_domains=[bestbuy, amazon, walmart, target, rtings])` | ~3 s. (`focus="shopping"` works but took ~60 s in testing, too slow for a live demo) |
| `extract_page` | `client.extract.run(url, render=True, formats=["markdown"])` | JS-rendered clean Markdown |
| `research_topic` | search + concurrent `extract.run` on top 2 results | Fast multi-source research |
| `web_agent` | `client.agents.run(input, agent_name="nimble-buddy-research", effort="low")`, then `agents.runs.get` / `agents.runs.result` | Reuses **one** named agent so demo runs don't consume extra trial agent slots. Output includes `trust.claims[]` with `confidence` and `citations` |

### Credit budget (trial: 30 agents, 5,000 API credits)
- All agent runs reuse a single agent (`nimble-buddy-research`).
- Default agent effort is `low`; only raise to `medium` for the final recorded take.
- Search is limited to 5–8 results; research extracts only the top 2 pages.
- Rehearse with search/shopping (cheap) and run the agent only 2–3 times before the demo.

### Sandbox mode
With no Nimble key, tools return clearly labelled `[Sandbox]` placeholder links (never fake prices or facts). With a key, failures are shown as errors instead of being hidden.

---

## 🧯 Troubleshooting

| Symptom | Fix |
|---|---|
| `/api/status` says `sandbox` | `NIMBLE_API_KEY` missing or still `your-nimble-api-key` in `.env`; restart the server after editing |
| `Nimble web_search failed: 401` | Key invalid/revoked — create a new one in the dashboard |
| Agent says "still running after 150s" | Retry with effort `low`; the run continues server-side and can be checked in the Nimble dashboard |
| Every reply is keyword-based | No Groq key — add `GROQ_API_KEY` (optional) |
| Mic doesn't work | Allow microphone access when the browser asks (click the 🔒 icon in the address bar to re-enable). The page must be on `localhost` or HTTPS (the Cloudflare link is HTTPS). Status bar shows the exact error. Voice needs `GROQ_API_KEY` |
| Reply isn't spoken aloud | Spoken replies only follow voice questions; check the computer isn't muted |
| Reply uses the robotic browser voice | Accept the Orpheus model terms once at https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english (org admin). Change voice with `TTS_VOICE=` in `.env` |
| `429 Rate limit reached` from Groq | Free tier allows ~8k tokens/min. Wait ~30 s between demo prompts, or upgrade to Groq Dev Tier. The app falls back to the rule-based planner automatically |
| Shopping answer has no prices | Nimble only returns what the sources list; the model is instructed not to invent prices |

### Tunnel troubleshooting
| Symptom | Fix |
|---|---|
| `cloudflared: command not found` | `brew install cloudflared` |
| `share.sh` says app is not running | Start `uvicorn` first, or set `PORT=...` to match |
| Cloudflare `502 Bad Gateway` page | The app stopped; restart it in terminal 1 |
| URL stopped working | The tunnel was closed or restarted; run `./scripts/share.sh` again and share the new URL |

---

## 🗺️ Roadmap (post-hackathon)
- Stream agent progress events (`enable_events`) into the Execution Inspector.
- Render agent claims with confidence badges in the UI.
- Structured output schemas for price tables (`output_schema`).
- Real email sending via an approved provider with explicit user confirmation.

---

