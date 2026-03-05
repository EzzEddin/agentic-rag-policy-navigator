import os
from dotenv import load_dotenv

load_dotenv()

AIXPLAIN_API_KEY: str = os.getenv("AIXPLAIN_API_KEY", "")
AGENT_ID: str = os.getenv("AGENT_ID", "")
POLICY_INDEX_ID: str = os.getenv("POLICY_INDEX_ID", "")

FEDERAL_REGISTER_API_BASE = "https://www.federalregister.gov/api/v1"
COURT_LISTENER_API_BASE = "https://www.courtlistener.com/api/rest/v4"
COURT_LISTENER_TOKEN: str = os.getenv("COURT_LISTENER_TOKEN", "")

ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "3072"))

# Default LLM – GPT-4o (swap as needed via env)
DEFAULT_LLM_ID: str = os.getenv("DEFAULT_LLM_ID", "6646261c6eb563165658bbb1")

# aiR – aiXplain Retrieval managed vector database integration ID
AIR_INTEGRATION_ID = "6904bcf672a6e36b68bb72fb"

# Python Sandbox Integration ID (for custom Python tools)
PYTHON_SANDBOX_INTEGRATION_ID = "688779d8bfb8e46c273982ca"
