import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# aix_client must be imported early so Aixplain(api_key=...) is initialised
# before any agent or index code runs.
import app.aix_client  # noqa: F401

from app.config import ALLOWED_ORIGINS
from app.routers import chat, documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure Uvicorn loggers forward to the root logger configured above.
for _logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_logger_name).propagate = True

app = FastAPI(
    title="Policy Navigator API",
    description=(
        "A Multi-Agent RAG system for querying government regulations, "
        "compliance policies, and public health guidelines."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "Policy Navigator API"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
