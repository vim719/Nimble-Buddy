from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.agent import Agent

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
