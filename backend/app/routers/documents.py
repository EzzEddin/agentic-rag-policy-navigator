import logging
import os
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from app.schemas.models import DocumentIndexRequest, DocumentIndexResponse, SearchRequest, SearchResponse, SearchResult
from app.agents.index_manager import policy_index_manager

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/index-url", response_model=DocumentIndexResponse)
async def index_url(request: DocumentIndexRequest) -> DocumentIndexResponse:
    """
    Fetch and index the content of a public URL (e.g. a government regulatory
    page or policy document hosted online).
    """
    try:
        policy_index_manager.upsert_url(
            url=request.url,
            description=request.description or "",
        )
        return DocumentIndexResponse(
            success=True,
            message=f"Successfully indexed content from: {request.url}",
            index_id=policy_index_manager.index_id,
        )
    except Exception as exc:
        logger.error("Failed to index URL %s: %s", request.url, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload", response_model=DocumentIndexResponse)
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
) -> DocumentIndexResponse:
    """
    Upload a policy document (PDF, TXT, MD, or CSV) and add it to the
    vector index.
    """
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        policy_index_manager.upsert_file(tmp_path)
        # Rename to use original filename as record ID
        import shutil
        from pathlib import Path
        final_path = Path(tmp_path).parent / (file.filename or "uploaded_doc")
        shutil.move(tmp_path, str(final_path))
        policy_index_manager.upsert_file(str(final_path))
        os.unlink(str(final_path))
    except Exception as exc:
        logger.error("Failed to index uploaded file %s: %s", file.filename, exc)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=str(exc))

    return DocumentIndexResponse(
        success=True,
        message=f"Successfully indexed '{file.filename}' into the policy index.",
        index_id=policy_index_manager.index_id,
    )


@router.post("/search", response_model=SearchResponse)
async def search_index(request: SearchRequest) -> SearchResponse:
    """
    Perform a semantic search directly against the aiR index.

    Uses the v2 search pattern:
        index.run(action="search", data={"query": "...", "top_k": N})

    Useful for verifying what the index contains and debugging RAG retrieval
    before or alongside the full agent pipeline.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        raw_results = policy_index_manager.search(
            query=request.query,
            top_k=request.top_k,
        )
    except Exception as exc:
        logger.error("Index search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    results = [
        SearchResult(
            id=r.get("id", ""),
            text=r.get("text", ""),
            score=float(r.get("score", 0.0)),
            metadata=r.get("metadata", {}),
        )
        for r in raw_results
    ]

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
    )


@router.get("/index-info")
async def index_info() -> dict:
    """Return current index ID and basic metadata."""
    return {
        "index_id": policy_index_manager.index_id,
        "ready": policy_index_manager.index_id is not None,
        "total_documents": policy_index_manager.count() if policy_index_manager.index_id else 0,
    }
