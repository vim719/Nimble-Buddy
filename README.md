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
| 7 | 🎙️ **Voice input** | Click the mic | Browser Web Speech API |

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
| Mic doesn't work | Use Chrome; allow microphone permission for localhost |
| `429 Rate limit reached` from Groq | Free tier allows ~8k tokens/min. Wait ~30 s between demo prompts, or upgrade to Groq Dev Tier. The app falls back to the rule-based planner automatically |
| Shopping answer has no prices | Nimble only returns what the sources list; the model is instructed not to invent prices |

---

## 🗺️ Roadmap (post-hackathon)
- Stream agent progress events (`enable_events`) into the Execution Inspector.
- Render agent claims with confidence badges in the UI.
- Structured output schemas for price tables (`output_schema`).
- Real email sending via an approved provider with explicit user confirmation.

---

## 🙏 Credits & disclosure
- Based on [MITRAKER/nimble-companion](https://github.com/MITRAKER/nimble-companion); renamed to NimbleBuddy and extended during AI Engineer NYC 2026 (Web Search Agent integration, shopping/news focus, answer synthesis, honest sandbox mode, secret-handling hardening, demo runbook).
- **AI assistance:** Antigravity AI and Claude Code were used as coding assistants.
- **Runtime LLM:** Groq `openai/gpt-oss-120b` with native function calling (Llama 3.3 70B was retired on Groq).
- **Web data:** Nimble Python SDK (`nimble_python`) — Search, Extract, Web Search Agents.

MLH rules: repo must stay public; demo video ≤ 2 minutes. Judging: Technology, Design, Completion, Learning (25% each).
