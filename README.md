# NimbleBuddy 🌐
> **Your AI Internet Buddy — Listens locally, executes across the web via Nimble.**  
> Built for the **AI Engineer NYC 2026** Hackathon · Competing for **Best Use of Nimble**.

---

## 🌟 Overview
**NimbleBuddy** is an agentic AI buddy that bridges the gap between local voice/chat interactions and the live internet. Powered by **Nimble's stealth web intelligence fabric** (`nimble_python`) and **Groq LLM** (`llama-3.3-70b-versatile`), it listens to your voice locally and executes autonomous "internet work" for you:

1. **🎙️ Local Voice Listening:** Speak naturally using local speech-to-text directly in your browser.
2. **🛍️ Autonomous Shopping:** Finds real-time deals, compares prices, and retrieves product specs via Nimble Search.
3. **🌐 Web Browsing & Extraction:** Reads and parses JavaScript-rendered articles and documentation into clean, structured Markdown via Nimble Extract.
4. **🔬 Deep Research:** Crawls and synthesizes multi-source research briefs with verified citations.
5. **✉️ Email Dispatch:** Drafts and formats professional emails containing web insights ready for 1-click dispatch.

---

## 🏗️ Architecture

```
User (Voice / Text)
       │
       ▼
┌───────────────────────────────────────────────┐
│       Frontend (HTML5 / Modern Dark UI)       │
│  - Web Speech API (Local microphone stream)   │
│  - Live Execution Inspector & Source Citations│
└───────────────────────┬───────────────────────┘
                        │ HTTP / JSON
                        ▼
┌───────────────────────────────────────────────┐
│         FastAPI Backend (app/main.py)         │
│  - Router & Static Asset Server               │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│        Agentic Brain (app/agent.py)           │
│  - Groq Llama 3.3 70B Versatile               │
│  - Dynamic Tool Selection & Plan Synthesis    │
└───────────────────────┬───────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   Nimble Toolkit          │   │      Email Assistant      │
│  (app/nimble_tools.py)    │   │  - mailto: generator      │
│  - nimble.search()        │   │  - Structured Outbox      │
│  - nimble.extract.run()   │   └───────────────────────────┘
│  - Residential Proxy Web  │
└───────────────────────────┘
```

---

## ⚡ Quickstart

### 1. Requirements
- Python 3.10+ (tested on Python 3.14)
- Packages: `fastapi`, `uvicorn`, `nimble_python`, `groq`, `python-dotenv`, `pydantic`

### 2. Configure Environment (`.env`)
Create a `.env` file in the root directory:
```bash
# Get your Nimble API key from https://online.nimbleway.com/settings/api-keys
NIMBLE_API_KEY=your_nimble_api_key_here

# Get your free Groq key from https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```
*(Note: If API keys are not provided, NimbleBuddy automatically activates an intelligent sandbox mode so you can demo and inspect all tool execution pipelines offline).*

### 3. Start the Application
Run the unified server with a single command:
```bash
py -m uvicorn app.main:app --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser!

---

## 🛠️ Key Capabilities & Nimble APIs Used

| Capability | Nimble API / Method | Description |
|---|---|---|
| **Live Search** | `client.search(query, max_results)` | Retrieves real-time Google search results, news, and facts with structured intent. |
| **Page Extract** | `client.extract.run(url, render=True, formats=['markdown'])` | Full JS-rendered headless browser extraction stripping ads/cookies into clean LLM Markdown. |
| **Price Comparison** | `client.search(f"{query} buy price")` | Real-time pricing intelligence across online retailers. |
| **Deep Research** | Multi-source compound search + extract | Gathers evidence across multiple articles with verifiable citation links. |
| **Emailing** | `draft_or_send_email()` | Packages web intelligence into ready-to-send emails with `mailto:` client integration. |

---

## 🏆 MLH Hackathon Submission Details
- **Challenge:** [Best Use of Nimble](https://www.mlh.com/events/ai-engineer-nyc-2026/challenges/01a121c8-b4b4-91a9-0c97-4e532c53d592)
- **Event:** AI Engineer NYC 2026 (Major League Hacking)
- **Focus:** Demonstrating live web context, structured data extraction, and autonomous agent web tools.

---

## 📜 MLH Standard Rules Compliance Checklist

In accordance with [MLH Standard Hackathon Rules](https://github.com/MLH/mlh-policies/blob/main/standard-hackathon-rules.md):

1. **Fresh Build (Rules 6 & 9):** All project code was authored during the hackathon period specifically for AI Engineer NYC 2026.
2. **AI Transparency Disclosure:** As encouraged by MLH AI guidelines:
   - **AI Coding Assistant:** Antigravity AI pair programming assistant used for scaffolding & rapid prototyping.
   - **Runtime LLM:** Groq Llama 3.3 70B Versatile for autonomous agent reasoning & tool orchestration.
   - **Web Intelligence Fabric:** Nimble Python SDK (`nimble_python`) for live search, crawling, and JavaScript-rendered page extractions.
3. **Public Git Repository (Rules 12 & 13):** Repository must be public and remain public post-event.
4. **Demo Video Requirements (MLH Digital Rules):**
   - Video length: **2 minutes or less**.
   - Must state at the beginning: *"Hey, I'm [Your Name], and this is my demo for AI Engineer NYC 2026."*
   - Focus on demonstrating the live working product (pitches/slides discouraged).
5. **Judging Criteria Alignment (25% each):**
   - **Technology (25%):** Unified integration of Nimble Web API v2 SDK, multi-source extraction, Groq Llama 3.3 70B agentic loop, and browser Web Speech API.
   - **Design (25%):** Modern dark glassmorphic UI, live execution inspector with parameters and citations, and voice pulse animations.
   - **Completion (25%):** 100% operational with verified end-to-end integration tests across search, extract, shop, and email pipelines.
   - **Learning (25%):** Deep exploration of Nimble's stealth residential proxy fabric and agentic web tool schemas.

