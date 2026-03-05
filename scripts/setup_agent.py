"""
setup_agent.py – One-time script to create and save the Policy Navigator
                 unified agent on aiXplain.

Uses the aiXplain v2 SDK pattern:
    aix.Agent(name=..., instructions=..., tools=[...])  then  .save()

Usage (from the project root):
    python scripts/setup_agent.py

Steps:
1. Loads (or creates) the aiR index from POLICY_INDEX_ID in backend/.env.
2. Builds a unified agent with all tools (Federal Register + CourtListener).
3. Saves the agent to aiXplain.
4. Prints the Agent ID – paste it into backend/.env as AGENT_ID.

Prerequisites:
    pip install -r backend/requirements.txt
    Complete setup_index.py first and set POLICY_INDEX_ID in backend/.env.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

from app.agents.policy_agent import _build_unified_agent
from app.agents.index_manager import policy_index_manager


def main():
    logger.info("─── Policy Navigator: Agent Setup (Unified Agent) ───────────────────")
    logger.info("Building unified agent (this may take a minute)…")

    # Ensure index exists first (required for agent creation)
    index = policy_index_manager.get_or_create_index()
    logger.info("Using index: %s", index.id)

    agent = _build_unified_agent(index)
    logger.info("Unified Agent created: %s (id=%s)", agent.name, agent.id)

    logger.info("")
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info("Agent setup complete!")
    logger.info("Add the following line to backend/.env:")
    logger.info("  AGENT_ID=%s", agent.id)
    logger.info("═══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
