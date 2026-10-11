import asyncio
import base64
import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from app.agent import Agent
from app.config import settings
from groq import RateLimitError

logger = logging.getLogger(__name__)

# Delivery style approved in testing (voice-samples/fixed_hannah_1.wav): two short, plain sentences
SPOKEN_STYLE = "calm, plain and matter-of-fact, like a knowledgeable friend; exactly two short sentences"


def _retry_after_seconds(error: Exception) -> float:
    """Seconds to wait from Groq's 429 headers (retry-after or x-ratelimit-reset-tokens like '550ms' / '3.2s')."""
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    value = headers.get("retry-after") or headers.get("x-ratelimit-reset-tokens") or "3"
    total = 0.0
    for amount, unit in re.findall(r"([\d.]+)\s*(ms|h|m|s)?", value):
        total += float(amount) * {"ms": 0.001, "h": 3600, "m": 60, "s": 1, "": 1}[unit]
    return max(total, 0.5)


def _for_tts(text: str) -> str:
    """Normalize typography that makes Orpheus sound choppy (odd hyphens, dashes, symbols)."""
    num = r"(\d+(?:,\d{3})*(?:\.\d+)?)"
    text = re.sub(r"\$" + num + r"\s*[‐-―-]\s*\$?" + num, r"\1 to \2 dollars", text)
    text = re.sub(r"\$" + num, r"\1 dollars", text)
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"(\d)[‐-―](\d)", r"\1 to \2", text)
    text = re.sub(r"\s*[–—]\s*", ", ", text)
    text = re.sub(r"[‐‑]", "-", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("&", " and ").replace("/", " or ")
    return " ".join(text.split())
# Safety net: strip stock openers if the model uses one anyway
FILLER_OPENER = re.compile(
    r"^(sure thing|sure|certainly|absolutely|of course|great question|okay|ok|so|alright|happy to help|"
    r"i'?d be happy to( help)?|i'?ll help you( with that)?)\b[\s,!.:—-]*",
    re.IGNORECASE
)

router = APIRouter(prefix="/api")
agent = Agent()


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to NimbleBuddy")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional previous chat history")


class SourceItem(BaseModel):
    title: Optional[str] = ""
    url: str


class ToolUsage(BaseModel):
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str
    tools_used: List[ToolUsage]
    sources: List[SourceItem]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for NimbleBuddy.
    Takes user input, runs agentic loop with tool calls, and returns final synthesized response.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await agent.run(request.message, chat_history=request.history)
    return result


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Speech-to-text for the mic button via Groq Whisper.
    Works in every browser (unlike the Web Speech API, which is Chrome/Edge-only).
    """
    if not agent.client:
        raise HTTPException(status_code=503, detail="Voice input needs GROQ_API_KEY in .env")
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty recording")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Recording too long")
    try:
        result = await asyncio.to_thread(
            agent.client.audio.transcriptions.create,
            file=(audio.filename or "speech.webm", data),
            model="whisper-large-v3-turbo",
            language="en"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")
    return {"text": (getattr(result, "text", "") or "").strip()}


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Assistant reply (markdown) to speak")


def _spoken_summary(text: str) -> str:
    """Rewrite a markdown answer as one or two casual spoken sentences."""
    clipped = text[:3000]
    try:
        completion = agent.client.chat.completions.create(
            model=settings.SPEECH_STYLE_MODEL,
            messages=[
                {"role": "system", "content": (
                    "Turn the assistant's answer into what a friendly, knowledgeable person would say out loud "
                    "in one or two short sentences, under 180 characters total. Natural and conversational, "
                    "contractions welcome. No markdown, URLs, citations, emoji, or lists. Keep only facts from the answer. "
                    "Lead with the most interesting specific fact — a name, number, or finding. "
                    "Write for the ear: say prices and ranges in words ('about a hundred and twenty dollars', '9 to 5'), "
                    "expand abbreviations (ANC -> noise cancelling), no symbols like $, %, dashes or slashes, plain punctuation only. "
                    "At most one number per sentence. "
                    "Never start with filler like 'Sure', 'Sure thing', 'Certainly', 'Absolutely', 'Of course', 'Great question', "
                    "'So', 'Okay', 'Here's', or 'I'll help you'. "
                    f"Style: {SPOKEN_STYLE}."
                )},
                {"role": "user", "content": clipped}
            ],
            temperature=0.5,
            max_tokens=400,
            reasoning_effort="low"
        )
        spoken = (completion.choices[0].message.content or "").strip()
        while FILLER_OPENER.match(spoken):
            spoken = FILLER_OPENER.sub("", spoken, count=1)
        if spoken:
            spoken = spoken[0].upper() + spoken[1:]
            if len(spoken) > 220:
                # End on a full sentence rather than mid-word
                cut = max(spoken.rfind(p, 0, 220) for p in (". ", "! ", "? "))
                spoken = spoken[:cut + 1] if cut > 40 else spoken[:220]
            return spoken
    except Exception as e:
        logger.warning(f"Speech rewrite failed, using plain text: {e}")
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clipped)
    plain = re.sub(r"https?://\S+|[#*_`>|]|\[\d+\]", " ", plain)
    return " ".join(plain.split())[:200]


@router.post("/speak")
async def speak(request: SpeakRequest):
    """
    Human-sounding voice reply: rewrite the answer in spoken style, then synthesize
    it with Orpheus TTS on Groq. The frontend falls back to the browser voice on error.
    """
    if not agent.client:
        raise HTTPException(status_code=503, detail="Voice replies need GROQ_API_KEY in .env")
    spoken = await asyncio.to_thread(_spoken_summary, request.text)
    # Orpheus on Groq's free tier allows ~1,200 tokens/min, so back-to-back replies can hit 429.
    # Wait out the short per-minute window (up to ~12s total) rather than dropping to the robotic browser voice.
    audio = None
    for attempt in range(4):
        try:
            audio = await asyncio.to_thread(
                agent.client.with_options(max_retries=0).audio.speech.create,
                model=settings.TTS_MODEL,
                voice=settings.TTS_VOICE,
                input=_for_tts(spoken),
                response_format="wav"
            )
            break
        except RateLimitError as e:
            retry_after = _retry_after_seconds(e)
            if attempt == 3 or retry_after > 10:
                raise HTTPException(status_code=429, detail=f"Voice rate limit reached; retry in {retry_after:.0f}s")
            logger.info(f"TTS rate limited, retrying in {retry_after:.1f}s")
            await asyncio.sleep(retry_after)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"TTS failed: {e}")
    # Return the exact words spoken so the chat can show them alongside the audio
    return {"text": spoken, "audio": base64.b64encode(audio.read()).decode(), "mime": "audio/wav"}


@router.get("/status")
async def get_status():
    """
    Report which integrations are live. Never returns key values.
    """
    return {
        "nimble": "live" if agent.toolkit.is_live else "sandbox",
        "llm": "groq" if agent.client else "rule-based planner"
    }


@router.get("/tools")
async def get_tools():
    """
    List available Nimble-powered tools.
    """
    return {
        "tools": agent.toolkit.get_tool_descriptions()
    }
