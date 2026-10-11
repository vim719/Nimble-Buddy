import json
import logging
import re
from typing import Any, Dict, List, Optional
from groq import Groq
from app.config import settings
from app.nimble_tools import NimbleToolkit

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, toolkit: Optional[NimbleToolkit] = None):
        self.toolkit = toolkit or NimbleToolkit()
        self.client = None
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your-groq-api-key":
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

    def _build_system_prompt(self) -> str:
        tools_str = json.dumps(self.toolkit.get_tool_descriptions(), indent=2)
        return (
            "You are NimbleBuddy, a helpful AI assistant that can browse the internet, "
            "shop for products, and research topics for your user.\n\n"
            f"You have access to these tools powered by Nimble:\n{tools_str}\n\n"
            "When the user asks something that requires internet access, respond with a JSON object:\n"
            '{"tool": "tool_name", "params": {"param_name": "value"}}\n\n'
            "When you can answer directly without tools, just respond normally.\n"
            "When you receive tool results, synthesize them into a helpful, conversational response with key findings and source URLs."
        )

    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract a tool call JSON from the model output."""
        cleaned = text.strip()

        # Check if the entire response is JSON
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "tool" in data:
                return data
        except Exception:
            pass

        # Try to extract JSON code block ```json ... ```
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_block:
            try:
                data = json.loads(code_block.group(1))
                if isinstance(data, dict) and "tool" in data:
                    return data
            except Exception:
                pass

        # Try to find any JSON object substring containing "tool"
        match = re.search(r'(\{\s*"tool"\s*:\s*"[^"]+".*?\})', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "tool" in data:
                    return data
            except Exception:
                pass

        return None

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via NimbleToolkit."""
        if tool_name == "web_search":
            query = params.get("query", "")
            focus = params.get("focus", "general")
            return await self.toolkit.web_search(query=query, focus=focus if focus in ("general", "news") else "general")
        elif tool_name == "research_topic":
            topic = params.get("topic") or params.get("query", "")
            return await self.toolkit.research_topic(topic=topic)
        elif tool_name == "web_agent":
            task = params.get("task") or params.get("query", "")
            effort = params.get("effort", "low")
            return await self.toolkit.web_agent(task=task, effort=effort if effort in ("low", "medium") else "low")
        elif tool_name == "extract_page":
            url = params.get("url", "")
            return await self.toolkit.extract_page(url=url)
        elif tool_name == "shop_search":
            product_query = params.get("product_query") or params.get("query", "")
            return await self.toolkit.shop_search(product_query=product_query)
        elif tool_name == "draft_or_send_email":
            to_email = params.get("to_email") or params.get("to", "user@example.com")
            subject = params.get("subject", "Update from NimbleBuddy")
            body = params.get("body", "")
            action = params.get("action", "draft")
            return await self.toolkit.draft_or_send_email(to_email=to_email, subject=subject, body=body, action=action)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def _fallback_plan_and_run(self, message: str) -> Dict[str, Any]:
        """Intelligent planner fallback if Groq API key is not configured or offline."""
        lowered = message.lower().strip()
        tools_used = []
        sources = []

        # 1. Email detection
        if any(w in lowered for w in ["email", "mail to", "send email", "draft email", "compose email"]):
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
            recipient = email_match.group(0) if email_match else "colleague@example.com"
            tool_name = "draft_or_send_email"
            params = {
                "to_email": recipient,
                "subject": f"Summary: {message[:40]}...",
                "body": f"Hi,\n\nHere is the information you requested via NimbleBuddy:\n\n{message}\n\nBest regards,\nNimbleBuddy",
                "action": "send" if "send" in lowered else "draft"
            }
            tools_used.append({"tool": tool_name, "params": params})
            tool_result = await self.execute_tool(tool_name, params)
            sources.append({"title": f"Email to {recipient}", "url": f"mailto:{recipient}"})
            return {
                "response": f"✉️ I have prepared an email for **{recipient}** with subject *'{params['subject']}'*.\n\n```\nTo: {recipient}\nSubject: {params['subject']}\n\n{params['body']}\n```\n\nYou can open your local mail client or edit this directly.",
                "tools_used": tools_used,
                "sources": sources
            }

        # 2. Page Extraction if URL detected
        url_match = re.search(r'https?://[^\s]+', message)
        if url_match or any(w in lowered for w in ["read page", "extract", "scrape", "summarize page"]):
            target_url = url_match.group(0) if url_match else "https://example.com"
            tool_name = "extract_page"
            params = {"url": target_url}
            tools_used.append({"tool": tool_name, "params": params})
            tool_result = await self.execute_tool(tool_name, params)
            sources.append({"title": f"Extracted: {target_url}", "url": target_url})
            content_preview = (tool_result.get("content") or "")[:500]
            return {
                "response": f"🌐 Extracted clean web content from [{target_url}]({target_url}) using **Nimble Extract**:\n\n{content_preview}...\n\n*Full page processed with JavaScript rendering enabled via Nimble stealth browser engine.*",
                "tools_used": tools_used,
                "sources": sources
            }

        # 3. Web Search Agent for multi-step tasks
        if any(w in lowered for w in ["agent", "competitor", "compare", "deep dive", "investigate", "find all", "list of"]):
            tool_name = "web_agent"
            params = {"task": message, "effort": "low"}
            tools_used.append({"tool": tool_name, "params": params})
            tool_result = await self.execute_tool(tool_name, params)
            for item in tool_result.get("results", []):
                if item.get("url"):
                    sources.append({"title": item.get("title", "Source"), "url": item["url"]})
            answer = tool_result.get("answer") or tool_result.get("error") or "The agent returned no output."
            if not isinstance(answer, str):
                answer = "```json\n" + json.dumps(answer, indent=2, ensure_ascii=False) + "\n```"
            return {
                "response": f"🤖 **Nimble Web Search Agent** finished ({len(tool_result.get('claims', []))} cited claims, {len(sources)} sources):\n\n{answer}",
                "tools_used": tools_used,
                "sources": sources
            }

        # 4. Shopping detection
        if any(w in lowered for w in ["buy", "shop", "price", "deals", "cost", "store", "headphones", "laptop", "product"]):
            cleaned_query = re.sub(r'^(find|search|show|get|buy|shop for|look for)\s+', '', lowered, flags=re.IGNORECASE)
            tool_name = "shop_search"
            params = {"product_query": cleaned_query}
            tools_used.append({"tool": tool_name, "params": params})
            tool_result = await self.execute_tool(tool_name, params)

            for item in tool_result.get("results", []):
                if item.get("url"):
                    sources.append({"title": item.get("title", "Product"), "url": item["url"]})

            response_lines = [f"🛍️ Here are top shopping results for **{cleaned_query}** discovered via Nimble Search:\n"]
            for idx, r in enumerate(tool_result.get("results", [])[:4], 1):
                response_lines.append(f"{idx}. **[{r['title']}]({r['url']})**\n   {r.get('snippet', '')}\n")

            return {
                "response": "\n".join(response_lines),
                "tools_used": tools_used,
                "sources": sources
            }

        # 5. Research detection
        if any(w in lowered for w in ["research", "deep dive", "analyze", "comprehensive", "history of", "overview of"]):
            tool_name = "research_topic"
            params = {"topic": message}
            tools_used.append({"tool": tool_name, "params": params})
            tool_result = await self.execute_tool(tool_name, params)

            for item in tool_result.get("sources", []):
                if item.get("url"):
                    sources.append({"title": item.get("title", "Research Source"), "url": item["url"]})

            return {
                "response": f"🔬 Deep Research findings for **'{message}'** powered by Nimble's multi-source crawler:\n\n- Analyzed top authority sources and extracted verbatim evidence.\n- Web context gathered across current articles.\n\nExplore citations in the Tools Inspector sidebar.",
                "tools_used": tools_used,
                "sources": sources
            }

        # 6. General Web Search default
        tool_name = "web_search"
        params = {"query": message}
        tools_used.append({"tool": tool_name, "params": params})
        tool_result = await self.execute_tool(tool_name, params)

        for item in tool_result.get("results", []):
            if item.get("url"):
                sources.append({"title": item.get("title", "Web Result"), "url": item["url"]})

        results_list = tool_result.get("results", [])
        if results_list:
            res_md = "\n".join([f"- **[{r['title']}]({r['url']})**: {r.get('snippet', '')}" for r in results_list[:3]])
            answer = tool_result.get("answer")
            answer_md = f"{answer}\n\n**Sources:**\n" if answer else ""
            final_text = f"🌐 Live internet results for **'{message}'** via Nimble Web Search:\n\n{answer_md}{res_md}"
        elif tool_result.get("error"):
            final_text = f"⚠️ {tool_result['error']}"
        else:
            final_text = f"I searched the live web for **'{message}'** via Nimble. Please check the sources inspector for details."

        return {
            "response": final_text,
            "tools_used": tools_used,
            "sources": sources
        }

    async def run(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Run the agent loop on a user message."""
        if not self.client:
            return await self._fallback_plan_and_run(message)

        tools_used = []
        sources = []

        messages = [{"role": "system", "content": self._build_system_prompt()}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": message})

        try:
            # First LLM call
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            first_response = completion.choices[0].message.content or ""
            tool_call = self._extract_tool_call(first_response)

            # If no tool called, return directly
            if not tool_call or "tool" not in tool_call:
                return {
                    "response": first_response,
                    "tools_used": tools_used,
                    "sources": sources
                }

            # Execute tool
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})
            tools_used.append({"tool": tool_name, "params": params})

            tool_result = await self.execute_tool(tool_name, params)

            # Extract source URLs if present in tool results
            if "results" in tool_result and isinstance(tool_result["results"], list):
                for item in tool_result["results"]:
                    if isinstance(item, dict) and "url" in item and item["url"]:
                        sources.append({"title": item.get("title", ""), "url": item["url"]})
            elif "sources" in tool_result and isinstance(tool_result["sources"], list):
                for item in tool_result["sources"]:
                    if isinstance(item, dict) and "url" in item and item["url"]:
                        sources.append({"title": item.get("title", ""), "url": item["url"]})
            elif "url" in tool_result and tool_result["url"]:
                sources.append({"title": "Extracted Page", "url": tool_result["url"]})

            # Send tool result back to LLM for synthesis
            messages.append({"role": "assistant", "content": first_response})
            messages.append({
                "role": "user",
                "content": f"Tool execution result for {tool_name}:\n{json.dumps(tool_result, ensure_ascii=False, default=str)[:12000]}\n\nPlease synthesize this into a final response."
            })

            final_completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            final_response = final_completion.choices[0].message.content or ""

            return {
                "response": final_response,
                "tools_used": tools_used,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error in Agent execution: {e}", exc_info=True)
            # Fall back to deterministic execution if LLM fails
            return await self._fallback_plan_and_run(message)
