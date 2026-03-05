"""
Manages the aiXplain aiR (aiXplain Retrieval) vector index for policy documents.

Follows the v2 SDK documentation pattern exactly:

    from aixplain import Aixplain
    aix = Aixplain(api_key="...")

    # Create
    index = aix.Tool(
        name="...",
        description="...",
        integration="6904bcf672a6e36b68bb72fb",  # aiR integration
    )
    index.save()

    # Ingest
    index.run(action="upsert", data={"records": [
        {"id": "doc1", "text": "...", "metadata": {"category": "..."}}
    ]})

    # Retrieve existing
    index = aix.Tool.get("<index_tool_id>")
"""

import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional

from app.aix_client import aix
from app.config import POLICY_INDEX_ID, AIR_INTEGRATION_ID

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent.parent.parent / "data" / "index_state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


class PolicyIndexManager:
    """
    Singleton-like manager that holds the aiR index (aix.Tool) instance.

    On first use it either loads an existing index by ID (from the env var
    POLICY_INDEX_ID or from the local state file) or creates a brand-new
    aiR-backed index using the v2 SDK pattern.
    """

    def __init__(self) -> None:
        self._index = None
        self._index_id: Optional[str] = POLICY_INDEX_ID or _load_state().get("index_id")

    @property
    def index_id(self) -> Optional[str]:
        return self._index_id

    # ---------------------------------------------------------------------- #
    # Index lifecycle                                                          #
    # ---------------------------------------------------------------------- #

    def get_index(self) -> object:
        """Return the existing aiR index. Requires POLICY_INDEX_ID to be set.

        The index must be created beforehand using scripts/setup_index.py.
        """
        if self._index is not None:
            return self._index

        index_id = POLICY_INDEX_ID or _load_state().get("index_id")
        if not index_id:
            raise RuntimeError(
                "POLICY_INDEX_ID is not set. "
                "Please run 'python scripts/setup_index.py' first and set POLICY_INDEX_ID in backend/.env"
            )

        try:
            self._index = aix.Tool.get(index_id)
            self._index_id = index_id
            logger.info("Loaded existing aiR index: %s", index_id)
            return self._index
        except Exception as exc:
            raise RuntimeError(
                f"Could not load aiR index {index_id}: {exc}. "
                "Please verify the ID or run 'python scripts/setup_index.py' to create a new index."
            ) from exc

    def get_or_create_index(self, name: str = "PolicyNavigatorIndex") -> object:
        """Return existing index or create new one. For use by setup scripts only."""
        if self._index is not None:
            return self._index

        index_id = POLICY_INDEX_ID or _load_state().get("index_id")
        if index_id:
            try:
                self._index = aix.Tool.get(index_id)
                self._index_id = index_id
                logger.info("Loaded existing aiR index: %s", index_id)
                return self._index
            except Exception as exc:
                logger.warning("Could not load aiR index %s: %s", index_id, exc)

        # Create new index
        unique_name = f"{name} {int(time.time())}"
        logger.info("Creating new aiR index '%s'…", unique_name)

        self._index = aix.Tool(
            name=unique_name,
            description=(
                "Managed vector database of government policy documents, "
                "compliance guidelines, and public health regulations for "
                "semantic retrieval via aiXplain aiR."
            ),
            integration=AIR_INTEGRATION_ID,
        )
        self._index.save()

        self._index_id = self._index.id
        state = _load_state()
        state["index_id"] = self._index_id
        _save_state(state)
        logger.info("Created aiR index: %s", self._index_id)
        return self._index

    # ---------------------------------------------------------------------- #
    # Document ingestion (v2 pattern: index.run with plain-dict records)     #
    # ---------------------------------------------------------------------- #

    def upsert_text(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Add or update a single text document in the aiR index.

        Uses the v2 ingestion pattern:
            index.run(action="upsert", data={"records": [
                {"id": "...", "text": "...", "metadata": {...}}
            ]})
        """
        index = self.get_or_create_index()
        record = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        }
        index.run(action="upsert", data={"records": [record]})
        logger.info("Upserted record '%s' into aiR index.", doc_id)

    def upsert_batch(self, records: list[dict]) -> None:
        """
        Upsert multiple records in one call for efficiency.

        Each record must follow the pattern:
            {"id": "...", "text": "...", "metadata": {...}}
        """
        index = self.get_or_create_index()
        index.run(action="upsert", data={"records": records})
        logger.info("Upserted %d records into aiR index.", len(records))

    def count(self) -> int:
        """Return the total number of documents in the index."""
        index = self.get_or_create_index()
        response = index.run(action="count")
        data = response.data
        # aiR returns a dict like {"data": N}
        if isinstance(data, dict):
            data = data.get("data", 0)
        return int(data)

    # ---------------------------------------------------------------------- #
    # Search & retrieval (v2 pattern: index.run with action="search"/"get")  #
    # ---------------------------------------------------------------------- #

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Semantic search over the aiR index.

        Uses the v2 search pattern from the documentation:
            response = index.run(
                action="search",
                data={"query": "...", "top_k": 3}
            )
            # response.data → list of {id, text, metadata, score}

        Args:
            query:  Natural language search query.
            top_k:  Maximum number of results to return (default 5).

        Returns:
            List of result dicts, each with keys: id, text, metadata, score.
            Results are ordered by similarity score (highest first).
        """
        index = self.get_or_create_index()
        response = index.run(
            action="search",
            data={"query": query, "top_k": top_k},
        )
        results = response.data if response.data else []
        # Ensure we only return top_k results (aiR may return more than requested)
        results = results[:top_k]
        # Filter by minimum relevance score threshold (0.5) - lowered from 0.7
        # to reduce "could not answer" responses while maintaining quality
        results = [r for r in results if r.get("score", 0) >= 0.5]
        logger.info(
            "Search for '%s' returned %d results.", query[:60], len(results)
        )
        return results

    def get_document(self, doc_id: str) -> dict | None:
        """
        Retrieve a specific document by its ID.

        Uses the v2 get pattern:
            response = index.run(action="get", data={"id": "..."})

        Returns:
            The document dict, or None if not found.
        """
        index = self.get_or_create_index()
        try:
            response = index.run(action="get", data={"id": doc_id})
            return response.data
        except Exception as exc:
            logger.warning("Could not retrieve document '%s': %s", doc_id, exc)
            return None

    def upsert_url(self, url: str, description: str = "") -> None:
        """
        Fetch the text content of a URL and index it in aiR.
        Only the first 8 000 characters are stored to stay within record size limits.
        """
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PolicyNavigator/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()[:8000]
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch URL '{url}': {exc}") from exc

        doc_id = url.replace("https://", "").replace("http://", "").replace("/", "_")[:120]
        self.upsert_text(
            doc_id,
            text,
            {"source_url": url, "description": description},
        )

    def upsert_url_with_chunking(
        self,
        url: str,
        description: str = "",
        chunking: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Fetch URL content and index it with sentence-based chunking.

        Uses the v2 chunking pattern:
            index.run(action="upsert", data={
                "records": [{"id": "...", "text": "...", "metadata": {...}}],
                "chunking": {"split_by": "sentence", "split_length": 10, "split_overlap": 2}
            })

        Args:
            url: URL to scrape and index.
            description: Description of the content for metadata.
            chunking: Chunking config dict with keys: split_by, split_length, split_overlap.
            metadata: Additional metadata to include with the document.
        """
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PolicyNavigator/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            # Try BeautifulSoup for better text extraction if available
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw, "html.parser")
                # Remove script, style, nav, footer, header elements
                for elem in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                    elem.decompose()
                # Get text from main content areas first, fallback to body
                main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main")) or soup.body
                if main_content:
                    text = main_content.get_text(separator=" ", strip=True)
                else:
                    text = soup.get_text(separator=" ", strip=True)
            except ImportError:
                # Fallback to regex-based extraction
                text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)

            # Clean up whitespace
            text = re.sub(r"\s+", " ", text).strip()[:8000]

            # Skip if content looks like mostly JavaScript
            js_indicators = ["function(", "var ", "const ", "let ", "window.", "document.", "gtm.start"]
            js_score = sum(1 for indicator in js_indicators if indicator in text[:1000])
            if js_score >= 3:
                logger.warning("URL '%s' appears to contain mostly JavaScript code, skipping.", url)
                return

            # Skip if too little meaningful content
            if len(text) < 200:
                logger.warning("URL '%s' returned insufficient text content (%d chars), skipping.", url, len(text))
                return

        except Exception as exc:
            raise RuntimeError(f"Failed to fetch URL '{url}': {exc}") from exc

        doc_id = url.replace("https://", "").replace("http://", "").replace("/", "_")[:120]

        merged_metadata = {"source_url": url, "description": description}
        if metadata:
            merged_metadata.update(metadata)

        record = {
            "id": doc_id,
            "text": text,
            "metadata": merged_metadata,
        }

        data = {"records": [record]}
        if chunking:
            data["chunking"] = chunking

        index = self.get_or_create_index()
        index.run(action="upsert", data=data)
        logger.info("Upserted URL '%s' with chunking into aiR index.", url)

    def upsert_file(self, file_path: str) -> None:
        """Index a local text or PDF file into the aiR index."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                import pdfminer.high_level as pdfminer  # type: ignore
                text = pdfminer.extract_text(str(path))
            except ImportError:
                raise ImportError(
                    "Install pdfminer.six to index PDF files: pip install pdfminer.six"
                )
        elif suffix in {".txt", ".md", ".csv"}:
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        doc_id = path.stem[:120]
        self.upsert_text(
            doc_id,
            text[:8000],
            {"source_file": path.name, "file_type": suffix},
        )


# Module-level singleton used by routers and agent setup
policy_index_manager = PolicyIndexManager()
