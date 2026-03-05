"""
Policy Navigator – Unified Agent with Federal Register + CourtListener APIs.

Architecture
------------
A single aiXplain Agent with all tools:

• aiR vector index (index_tool) – searches uploaded policy documents
• Federal Register search (search_federal_register) – finds policy documents
• Federal Register document detail (get_federal_register_document) – retrieves full docs
• CourtListener case law search (search_case_law) – finds court rulings
This unified approach provides reliable responses for both policy and
case law questions.

SDK v2 patterns used:
    aix.Agent(name=..., instructions=..., tools=[...])  then  .save()
    aix.Agent.get(id)        – reload a saved agent
    agent.run(question)  →  response.data.output
"""

import json
import logging
from typing import Optional

from app.aix_client import aix
from app.config import (
    AGENT_ID,
    MAX_ITERATIONS,
    MAX_TOKENS,
    PYTHON_SANDBOX_INTEGRATION_ID,
)
from app.agents.index_manager import policy_index_manager
from app.agents.tools import (
    search_federal_register,
    get_federal_register_document,
    search_case_law,
)

logger = logging.getLogger(__name__)

_unified_agent = None  # module-level cache for unified agent


def _create_custom_python_tool(func, tool_name: str = "", tool_description: str = ""):
    """Create a Python Sandbox tool from a function using aiXplain v2 SDK.

    Extracts source code via inspect.getsource() and creates a Tool with
    the Python Sandbox integration.

    Args:
        func: The Python function to register as a tool.
        tool_name: Descriptive name for the tool (helps agent routing).
        tool_description: Description of when to use this tool.
    """
    import inspect
    import time

    source = inspect.getsource(func)
    name = tool_name or f"{func.__name__} {int(time.time())}"
    tool_kwargs = {
        "name": f"{name} {int(time.time())}",
        "integration": PYTHON_SANDBOX_INTEGRATION_ID,
        "config": {"code": source, "function_name": func.__name__},
    }
    if tool_description:
        tool_kwargs["description"] = tool_description
    tool = aix.Tool(**tool_kwargs)
    tool.save()
    return tool


def _build_unified_agent(index_tool: object):
    """
    Build a single unified agent with all tools (Federal Register + CourtListener).
    This eliminates Team Agent delegation issues.
    """
    import time

    timestamp = int(time.time())

    # Create all 4 tools with clear names and descriptions for agent routing
    federal_register_search_tool = _create_custom_python_tool(
        search_federal_register,
        tool_name="Federal Register Policy Search",
        tool_description="Search the Federal Register for policy documents, executive orders, and federal regulations. Use for questions about policy status, executive orders, or regulatory documents.",
    )
    federal_register_doc_tool = _create_custom_python_tool(
        get_federal_register_document,
        tool_name="Federal Register Document Detail",
        tool_description="Retrieve full details of a specific Federal Register document by its document number.",
    )
    case_law_tool = _create_custom_python_tool(
        search_case_law,
        tool_name="CourtListener Case Law Search",
        tool_description="Search CourtListener for court cases, lawsuits, legal challenges, and judicial rulings. Use for ANY question about courts, legal challenges, litigation, or case law.",
    )

    # Single unified agent with all tools
    unified_agent = aix.Agent(
        name=f"Policy Navigator {timestamp}",
        description=(
            "Answers government policy questions using Federal Register API "
            "and CourtListener API. Returns concise, factual responses."
        ),
        instructions="""You are a Policy Navigator agent with access to multiple knowledge sources.

You have access to these tools:
1. Policy Documents Index - Internal policy documents, compliance guidelines, and general policy knowledge
2. Federal Register Policy Search - For searching federal regulations, executive orders, and checking policy status
3. Federal Register Document Detail - For retrieving a specific document by number
4. CourtListener Case Law Search - For court cases, lawsuits, legal challenges, judicial rulings

ROUTING RULES (follow strictly):
- General compliance questions (e.g. "HIPAA requirements", "data privacy guidelines", "what policies apply to X") -> Policy Documents Index FIRST. Only use Federal Register if the index has no relevant results.
- Court cases, lawsuits, legal challenges, rulings -> CourtListener Case Law Search
- Specific executive orders, federal regulations, policy status, "still in effect?" -> Federal Register Policy Search
- Specific document by number -> Federal Register Document Detail

IMPORTANT for policy status questions ("still in effect?", "revoked?"):
- Always review ALL returned results, not just the original document.
- A newer document on the same topic may REVOKE or SUPERSEDE the one being asked about.
- Look for titles containing "Revok", "Rescind", "Replac", "Amend", or newer executive orders on the same subject.
- If a newer Presidential Document exists on the same topic, use Federal Register Document Detail to check if it revokes the older one.

You MUST always call at least one tool before answering. Never answer from memory alone.
Use ONLY the retrieved information to answer. NEVER fabricate case names, dates, or details.
If a tool returns an error or empty results, say "I was unable to retrieve results due to [reason]." Do NOT invent data to fill the gap.
Keep answers concise (1-3 sentences).
Cite which source you used (Policy Documents, Federal Register, or CourtListener).
If no relevant information is found, say so honestly.
""",
        tools=[
            index_tool,
            federal_register_search_tool,
            federal_register_doc_tool,
            case_law_tool,
        ],
    )
    unified_agent.save()
    logger.info("Saved Unified Agent (id=%s)", unified_agent.id)
    return unified_agent


def get_agent():
    """Return the cached unified agent. Requires AGENT_ID to be set in env.
    
    Agents must be created beforehand using scripts/setup_agent.py.
    """
    global _unified_agent

    if _unified_agent is not None:
        return _unified_agent

    if not AGENT_ID:
        raise RuntimeError(
            "AGENT_ID is not set. "
            "Please run 'python scripts/setup_agent.py' first and set AGENT_ID in backend/.env"
        )

    try:
        _unified_agent = aix.Agent.get(AGENT_ID)
        logger.info("Loaded existing Agent: %s", AGENT_ID)
        return _unified_agent
    except Exception as exc:
        raise RuntimeError(
            f"Could not load AGENT_ID={AGENT_ID}: {exc}. "
            "Please verify the ID or run 'python scripts/setup_agent.py' to create new agents."
        ) from exc


def run_query(question: str) -> dict:
    """
    Run a user question through the Policy Navigator unified agent.

    v2 run pattern (from docs):
        response = agent.run(question)
        answer   = response.data.output

    Returns:
        output             – final answer string
        intermediate_steps – tool call steps for explainability
    """
    agent = get_agent()
    try:
        response = agent.run(question, max_iterations=MAX_ITERATIONS, max_tokens=MAX_TOKENS)

        # v2 response shape: response.data.output
        data = response.data if hasattr(response, "data") else response.get("data", {})

        output = ""
        if hasattr(data, "output"):
            output = data.output
        elif isinstance(data, dict):
            output = data.get("output", "")

        # v2 SDK uses data.steps (not intermediate_steps)
        steps_raw = []
        if hasattr(data, "steps"):
            steps_raw = data.steps or []
        elif hasattr(data, "intermediate_steps"):
            steps_raw = data.intermediate_steps or []
        elif isinstance(data, dict):
            steps_raw = data.get("steps", data.get("intermediate_steps", []))

        # Map internal function names to human-readable API/tool names
        tool_display = {
            "search_federal_register": "Federal Register API",
            "get_federal_register_document": "Federal Register API",
            "search_case_law": "CourtListener API",
        }

        steps = []
        pending_tool = None  # track tool name from reasoning step
        pending_input = None
        for s in steps_raw:
            if not isinstance(s, dict):
                continue
            output_text = str(s.get("output", ""))
            input_text = str(s.get("input", ""))

            # Reasoning step: extract action name from JSON output
            try:
                parsed = json.loads(output_text)
                action = parsed.get("action", "")
                if action and action != "Final Answer":
                    pending_tool = tool_display.get(action, action)
                    action_input = parsed.get("action_input", {})
                    pending_input = (
                        json.dumps(action_input)
                        if isinstance(action_input, dict)
                        else str(action_input)
                    )
                continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            # Tool execution step: pair with pending tool name
            if pending_tool and "The output of the connection is:" in output_text:
                steps.append({
                    "tool": pending_tool,
                    "input": pending_input or input_text,
                    "output": output_text[:2000],
                })
                pending_tool = None
                pending_input = None

        return {"output": output, "intermediate_steps": steps}

    except Exception as exc:
        logger.error("Agent run failed: %s", exc, exc_info=True)
        # Return user-friendly message; technical details stay in server logs
        return {
            "output": (
                "I encountered an error while generating the response. "
                "Please try again or rephrase your question."
            ),
            "intermediate_steps": [],
        }
