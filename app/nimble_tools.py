import asyncio
import logging
import time
import urllib.parse
from typing import Any, Dict, List
from nimble_python import Nimble
from app.config import settings

logger = logging.getLogger(__name__)

# A single, reused Web Search Agent so demo runs don't burn through trial agent slots.
AGENT_NAME = "nimble-buddy-research"
AGENT_TERMINAL_STATES = {"completed", "failed", "cancelled"}


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse_results(result: Any, default_title: str) -> List[Dict[str, Any]]:
    parsed = []
    for r in _get(result, "results", []) or []:
        snippet = _get(r, "description") or _get(r, "snippet") or ""
        if not snippet:
            snippet = (_get(r, "content") or "")[:300]
        parsed.append({
            "title": _get(r, "title") or default_title,
            "url": _get(r, "url", ""),
            "snippet": snippet
        })
    return parsed


class NimbleToolkit:
    def __init__(self, api_key: str = None):
        raw_key = api_key if api_key is not None else settings.NIMBLE_API_KEY
        self.api_key = raw_key.strip() if raw_key else ""
        if self.api_key and self.api_key != "your-nimble-api-key":
            try:
                self.client = Nimble(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Nimble client: {e}")
                self.client = None
        else:
            self.client = None

    @property
    def is_live(self) -> bool:
        return self.client is not None

    def _error(self, tool: str, e: Exception, **extra: Any) -> Dict[str, Any]:
        logger.warning(f"Live Nimble {tool} failed: {e}")
        return {"tool": tool, "error": f"Nimble {tool} failed: {e}", "results": [], **extra}

    async def web_search(self, query: str, max_results: int = 5, focus: str = "general") -> Dict[str, Any]:
        """Search the live web using Nimble Search, with a synthesized answer and citations"""
        if self.client:
            try:
                result = await asyncio.to_thread(
                    self.client.search,
                    query=query,
                    max_results=max_results,
                    focus=focus,
                    include_answer=True
                )
                return {
                    "tool": "web_search",
                    "query": query,
                    "focus": focus,
                    "answer": _get(result, "answer"),
                    "results": _parse_results(result, "Web Result")
                }
            except Exception as e:
                return self._error("web_search", e, query=query)

        # Sandbox mode (no API key): clearly labelled placeholder links, not real data
        encoded_q = urllib.parse.quote(query)
        return {
            "tool": "web_search",
            "query": query,
            "sandbox": True,
            "results": [
                {
                    "title": f"[Sandbox] Google results for '{query}'",
                    "url": f"https://www.google.com/search?q={encoded_q}",
                    "snippet": "Sandbox mode: add NIMBLE_API_KEY to .env for live Nimble Search results."
                },
                {
                    "title": f"[Sandbox] News results for '{query}'",
                    "url": f"https://news.google.com/search?q={encoded_q}",
                    "snippet": "Sandbox mode: add NIMBLE_API_KEY to .env for live Nimble Search results."
                }
            ]
        }

    async def extract_page(self, url: str) -> Dict[str, Any]:
        """Extract clean content from a webpage using Nimble Extract"""
        if self.client:
            try:
                result = await asyncio.to_thread(
                    self.client.extract.run,
                    url=url,
                    render=True,
                    formats=["markdown"]
                )
                data = _get(result, "data")
                content = _get(data, "markdown") if data is not None else None
                if not content:
                    content = str(data if data is not None else result)
                return {
                    "tool": "extract_page",
                    "url": url,
                    "content": content
                }
            except Exception as e:
                return self._error("extract_page", e, url=url, content="")

        return {
            "tool": "extract_page",
            "url": url,
            "sandbox": True,
            "content": f"# [Sandbox] {url}\n\nSandbox mode: add NIMBLE_API_KEY to .env to extract this page live with Nimble Extract (JS rendering, clean Markdown)."
        }

    async def shop_search(self, product_query: str) -> Dict[str, Any]:
        """Search for products and compare prices using Nimble's shopping focus"""
        if self.client:
            try:
                result = await asyncio.to_thread(
                    self.client.search,
                    query=product_query,
                    max_results=8,
                    focus="shopping",
                    include_answer=True
                )
                return {
                    "tool": "shop_search",
                    "query": product_query,
                    "answer": _get(result, "answer"),
                    "results": _parse_results(result, "Product Result")
                }
            except Exception as e:
                return self._error("shop_search", e, query=product_query)

        encoded_p = urllib.parse.quote(product_query)
        return {
            "tool": "shop_search",
            "query": product_query,
            "sandbox": True,
            "results": [
                {
                    "title": f"[Sandbox] Google Shopping: {product_query}",
                    "url": f"https://www.google.com/search?tbm=shop&q={encoded_p}",
                    "snippet": "Sandbox mode: add NIMBLE_API_KEY to .env for live prices via Nimble Search (shopping focus)."
                }
            ]
        }

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """Deep research a topic by searching + extracting top results"""
        try:
            search_results = await self.web_search(topic, max_results=3)
            urls = [r.get("url") for r in search_results.get("results", [])[:2] if r.get("url")]
            pages = await asyncio.gather(*(self.extract_page(u) for u in urls))
            titles = {r.get("url"): r.get("title", "") for r in search_results.get("results", [])}
            extracted = [
                {"url": p.get("url"), "title": titles.get(p.get("url"), ""), "content": (p.get("content") or "")[:2000]}
                for p in pages
            ]
            return {
                "tool": "research_topic",
                "topic": topic,
                "answer": search_results.get("answer"),
                "sources": extracted
            }
        except Exception as e:
            logger.error(f"Error during research_topic for '{topic}': {e}", exc_info=True)
            return {
                "tool": "research_topic",
                "topic": topic,
                "error": str(e),
                "sources": []
            }

    def _run_agent_blocking(self, task: str, effort: str, timeout_s: int) -> Dict[str, Any]:
        run = self.client.agents.run(input=task, agent_name=AGENT_NAME, effort=effort)
        run_id = _get(run, "id")
        agent_id = _get(run, "web_search_agent_id")
        status = _get(run, "status")

        deadline = time.time() + timeout_s
        while status not in AGENT_TERMINAL_STATES and time.time() < deadline:
            time.sleep(3)
            status = _get(self.client.agents.runs.get(run_id, agent_id=agent_id), "status")

        base = {"tool": "web_agent", "task": task, "effort": effort, "run_id": run_id, "agent_id": agent_id, "status": status}
        if status != "completed":
            msg = "still running" if status not in AGENT_TERMINAL_STATES else status
            return {**base, "error": f"Agent run {msg} after {timeout_s}s", "results": []}

        result = self.client.agents.runs.result(run_id, agent_id=agent_id)
        output = _get(result, "output")
        trust = _get(output, "trust")
        claims = [
            {
                "callout": _get(c, "callout"),
                "confidence": _get(c, "confidence"),
                "citations": [{"url": _get(ci, "url"), "title": _get(ci, "title")} for ci in (_get(c, "citations") or [])]
            }
            for c in (_get(trust, "claims") or [])
        ]
        sources = []
        seen = set()
        for c in claims:
            for ci in c["citations"]:
                if ci["url"] and ci["url"] not in seen:
                    seen.add(ci["url"])
                    sources.append({"title": ci["title"] or ci["url"], "url": ci["url"], "snippet": ""})
        return {
            **base,
            "output_type": _get(output, "type"),
            "answer": _get(output, "content") or _get(output, "text") or _get(output, "data"),
            "claims": claims,
            "results": sources
        }

    async def web_agent(self, task: str, effort: str = "low", timeout_s: int = 150) -> Dict[str, Any]:
        """Run a Nimble Web Search Agent: autonomous multi-step browsing with cited, confidence-scored claims"""
        if self.client:
            try:
                return await asyncio.to_thread(self._run_agent_blocking, task, effort, timeout_s)
            except Exception as e:
                return self._error("web_agent", e, task=task)

        return {
            "tool": "web_agent",
            "task": task,
            "sandbox": True,
            "answer": "Sandbox mode: add NIMBLE_API_KEY to .env to dispatch a live Nimble Web Search Agent.",
            "claims": [],
            "results": []
        }

    async def draft_or_send_email(self, to_email: str, subject: str, body: str, action: str = "draft") -> Dict[str, Any]:
        """Draft or dispatch an email on behalf of the user with internet findings, shopping links, or research summaries."""
        to_email = (to_email or "recipient@example.com").strip()
        subject = (subject or "Update from NimbleBuddy").strip()
        body = (body or "").strip()
        action_mode = "sent" if action.lower() == "send" else "draft"

        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        mailto_url = f"mailto:{to_email}?subject={encoded_subject}&body={encoded_body}"

        return {
            "tool": "draft_or_send_email",
            "action": action_mode,
            "to": to_email,
            "subject": subject,
            "body": body,
            "mailto_url": mailto_url,
            "status": "Email ready - open the link to send from your mail client" if action_mode == "sent" else "Email draft prepared for review",
            "results": [
                {
                    "title": f"Email {action_mode.capitalize()}: {subject}",
                    "url": mailto_url,
                    "snippet": f"To: {to_email} | Subject: {subject}"
                }
            ]
        }

    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Return tool descriptions for the LLM system prompt"""
        return [
            {
                "name": "web_search",
                "description": "Quick lookup of current information, live events, or facts using Nimble Search. Returns a synthesized answer plus source links. Use focus='news' for recent news.",
                "parameters": {"query": "search query string", "focus": "'general' (default) or 'news'"}
            },
            {
                "name": "extract_page",
                "description": "Read and extract clean markdown content from a specific webpage URL using Nimble Extract.",
                "parameters": {"url": "full URL to extract"}
            },
            {
                "name": "shop_search",
                "description": "Search for products to buy, compare real-time prices across stores, and find product specs.",
                "parameters": {"product_query": "product to search for"}
            },
            {
                "name": "research_topic",
                "description": "Fast research: Nimble search plus extraction of the top sources' full text.",
                "parameters": {"topic": "topic to research"}
            },
            {
                "name": "web_agent",
                "description": "Dispatch an autonomous Nimble Web Search Agent for multi-step work: competitor analysis, company deep dives, comparisons, building lists of entities, or any question needing many sources. Slower (30-120s) but returns verified claims with citations and confidence. Prefer this when the user says 'agent', 'deep dive', 'compare', 'find all', or 'investigate'.",
                "parameters": {"task": "full task instructions for the agent", "effort": "'low' (fast, default) or 'medium' (more thorough)"}
            },
            {
                "name": "draft_or_send_email",
                "description": "Draft or send an email on behalf of the user containing research findings, shopping deals, or updates.",
                "parameters": {
                    "to_email": "recipient email address (e.g. user@example.com)",
                    "subject": "email subject line",
                    "body": "email body content",
                    "action": "'draft' to prepare for review or 'send' to dispatch"
                }
            }
        ]
