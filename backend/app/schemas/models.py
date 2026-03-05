from pydantic import BaseModel
from typing import Any, Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class IntermediateStep(BaseModel):
    tool: str
    input: str
    output: str


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    intermediate_steps: list[IntermediateStep] = []
    error: Optional[str] = None


class DocumentIndexRequest(BaseModel):
    url: str
    description: Optional[str] = None


class DocumentIndexResponse(BaseModel):
    success: bool
    message: str
    index_id: Optional[str] = None


class AgentStatusResponse(BaseModel):
    agent_ready: bool
    index_id: Optional[str] = None
    agent_id: Optional[str] = None
    message: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict = {}


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
