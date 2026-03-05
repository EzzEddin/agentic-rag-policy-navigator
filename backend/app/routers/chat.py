import uuid
import logging
from fastapi import APIRouter, HTTPException

from app.schemas.models import ChatRequest, ChatResponse, IntermediateStep, AgentStatusResponse
from app.agents import policy_agent
from app.agents.index_manager import policy_index_manager

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the Policy Navigator agent and receive an answer."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())
    result = policy_agent.run_query(request.message)

    steps = [
        IntermediateStep(
            tool=s.get("tool", ""),
            input=s.get("input", ""),
            output=s.get("output", ""),
        )
        for s in result.get("intermediate_steps", [])
    ]

    return ChatResponse(
        answer=result.get("output", ""),
        session_id=session_id,
        intermediate_steps=steps,
    )


@router.get("/status", response_model=AgentStatusResponse)
async def agent_status() -> AgentStatusResponse:
    """Return the readiness status of the agent and index."""
    index_id = policy_index_manager.index_id
    agent_ready = False
    agent_id = None

    try:
        agent = policy_agent.get_agent()
        agent_ready = agent is not None
        agent_id = getattr(agent, "id", None)
    except Exception as exc:
        logger.warning("Could not load agent: %s", exc)

    return AgentStatusResponse(
        agent_ready=agent_ready,
        index_id=index_id,
        agent_id=agent_id,
        message=(
            "Policy Navigator is ready."
            if agent_ready
            else "Agent is initialising – please wait a moment."
        ),
    )
