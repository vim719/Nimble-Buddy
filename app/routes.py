import asyncio
import logging
import random
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from app.agent import Agent
from app.config import settings

logger = logging.getLogger(__name__)

# Vary delivery so consecutive spoken replies don't sound templated
SPOKEN_TONES = [
    "relaxed and matter-of-fact", "upbeat and curious", "warm and concise",
    "like telling a friend something you just found out", "calm and confident", "lightly enthusiastic"
]
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
                    "Never start with filler like 'Sure', 'Sure thing', 'Certainly', 'Absolutely', 'Of course', 'Great question', "
                    "'So', 'Okay', 'Here's', or 'I'll help you'. "
                    f"Tone for this reply: {random.choice(SPOKEN_TONES)}."
                )},
                {"role": "user", "content": clipped}
            ],
            temperature=0.9,
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
    try:
        audio = await asyncio.to_thread(
            agent.client.audio.speech.create,
            model=settings.TTS_MODEL,
            voice=settings.TTS_VOICE,
            input=spoken,
            response_format="wav"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS failed: {e}")
    return Response(content=audio.read(), media_type="audio/wav", headers={"X-Spoken-Text": spoken.encode("ascii", "ignore").decode()})


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
