"""
setup_index.py – One-time script to create the Policy Navigator aiR index
and seed it with two real data sources:

  Data Source 1 – GDPR Articles (JSONL)
  ─────────────────────────────────────────────────
  File    : backend/data/gdpr_articles.jsonl
  Keys    : article_number  – e.g. "Article 1 Subject-matter and objectives"
            article_text    – full legal text of the article
  (Alternative: articles.jsonl with input-text / output-text is also supported.)

  Data Source 2 – Website scrape (unstructured)
  ─────────────────────────────────────────────────
  Source  : WHO International Health Regulations (IHR)
  URL     : https://www.who.int/news-room/questions-and-answers/item/
            what-are-the-international-health-regulations-and-emergency-committee
  Why     : Covers international public health compliance policy —
            a distinct regulatory domain complementary to the GDPR dataset
            and the US-focused Federal Register API tool.

Uses the aiXplain v2 SDK patterns:
    aix.Tool(integration=...).save()           – create aiR index
    index.run(action="upsert", data={...})     – ingest documents
    index.run(action="search", data={...})     – verify retrieval
    index.run(action="count")                  – check total docs

Usage (from the project root):
    python scripts/setup_index.py

Prerequisites:
    pip install -r backend/requirements.txt
    Set AIXPLAIN_API_KEY in backend/.env
    Place gdpr_articles.jsonl (or articles.jsonl) in backend/data/
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

from app.agents.index_manager import policy_index_manager

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")

# ─── Data Source 2: Websites to scrape ───────────────────────────────────────
SCRAPE_URLS = [
    {
        "url": "https://www.who.int/health-topics/international-health-regulations",
        "description": "WHO IHR topic overview",
        "metadata": {"source": "WHO", "domain": "public_health", "type": "website"},
    },
    {
        "url": "https://www.epa.gov/laws-regulations/summary-clean-air-act",
        "description": "EPA summary of the Clean Air Act",
        "metadata": {"source": "EPA", "domain": "environment", "type": "website"},
    },
]

# ─── Sentence-based chunking config for website content ────────────────────────
WEBSITE_CHUNKING = {
    "split_by": "sentence",
    "split_length": 10,    # 10 sentences per chunk
    "split_overlap": 2     # 2 sentences overlap for continuity
}


# ─── Data Source 1: GDPR Articles JSONL ───────────────────────────────────────

def _sanitize_id(s: str, max_len: int = 120) -> str:
    """Build a safe document ID from article number/title."""
    return s.lower().replace(" ", "_").replace("/", "_").replace(".", "_")[:max_len]


def load_gdpr_jsonl(jsonl_path: str) -> list[dict]:
    """
    Load backend/data/gdpr_articles.jsonl (one JSON object per line).

    Expected keys in gdpr_articles.jsonl:
      article_number  – e.g. "Article 1 Subject-matter and objectives"
      article_text    – full legal text of the article

    Also supports articles.jsonl with different keys:
      input-text   – article title/number
      output-text  – full legal text

    Returns a list of aiR-ready records:
        {"id": "...", "text": "...", "metadata": {...}}
    """
    records = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Skipping invalid JSON at line %d: %s", line_num, e)
                continue

            # gdpr_articles.jsonl: article_number, article_text
            if "article_number" in obj and "article_text" in obj:
                article_number = str(obj["article_number"]).strip()
                article_text = str(obj["article_text"]).strip()
            # articles.jsonl: input-text, output-text
            elif "input-text" in obj and "output-text" in obj:
                article_number = str(obj["input-text"]).strip()
                article_text = str(obj["output-text"]).strip()
            else:
                logger.warning(
                    "Line %d: expected 'article_number'/'article_text' or 'input-text'/'output-text', got keys: %s",
                    line_num, list(obj.keys()),
                )
                continue

            if not article_text:
                continue

            # Combined text for embeddings (title + body)
            combined = f"{article_number}\n\n{article_text}" if article_number else article_text
            doc_id = f"gdpr_{_sanitize_id(article_number, max_len=100)}"

            records.append({
                "id": doc_id[:120],
                "text": combined[:8000],
                "metadata": {
                    "source": "gdpr_articles.jsonl",
                    "article": article_number,
                    "domain": "data_privacy",
                    "regulation": "GDPR",
                    "type": "dataset",
                },
            })

    return records


def main():
    logger.info("─── Policy Navigator: Index Setup ───────────────────────────")

    # Create or load the aiR index
    index = policy_index_manager.get_or_create_index(name="PolicyNavigatorIndex by Ezz")
    logger.info("Index ID: %s", index.id)
    logger.info("")

    # ── Data Source 1: GDPR Articles JSONL ───────────────────────────────────
    logger.info("━━━ Data Source 1: GDPR Articles JSONL ━━━━━━━━━━━━━━━━━━━━━")
    jsonl_path = os.path.join(DATA_DIR, "gdpr_articles.jsonl")
    if not os.path.exists(jsonl_path):
        jsonl_path = os.path.join(DATA_DIR, "articles.jsonl")

    if not os.path.exists(jsonl_path):
        logger.warning(
            "gdpr_articles.jsonl not found at %s\n"
            "  → Place gdpr_articles.jsonl (or articles.jsonl) in backend/data/\n"
            "  → Keys: article_number, article_text (or input-text, output-text)\n"
            "  Skipping JSONL ingestion for now.",
            os.path.join(DATA_DIR, "gdpr_articles.jsonl"),
        )
    else:
        try:
            gdpr_records = load_gdpr_jsonl(jsonl_path)
            logger.info("Loaded %d GDPR article records from %s.", len(gdpr_records), os.path.basename(jsonl_path))

            for record in gdpr_records:
                policy_index_manager.upsert_batch([record])

            # Upsert in batches of 50
            # batch_size = 50
            # for i in range(0, len(gdpr_records), batch_size):
            #     batch = gdpr_records[i : i + batch_size]
            #     policy_index_manager.run(action="upsert", data={"records": batch})
            #     logger.info(
            #         "  Upserted records %d–%d of %d",
            #         i + 1, min(i + batch_size, len(gdpr_records)), len(gdpr_records),
            #     )
            logger.info("✓ GDPR dataset fully indexed.")
        except Exception as exc:
            logger.error("Failed to index GDPR CSV: %s", exc)

    logger.info("")

    # ── Data Source 2: Website Scraping with Advanced Chunking ───────────────
    logger.info("━━━ Data Source 2: Website Scraping (Agentic RAG with Chunking) ━━━")
    logger.info("Using sentence-based chunking: 10 sentences/chunk, 2 overlap")
    for entry in SCRAPE_URLS:
        logger.info("Scraping: %s", entry["url"])
        try:
            policy_index_manager.upsert_url_with_chunking(
                url=entry["url"],
                description=entry["description"],
                chunking=WEBSITE_CHUNKING,
                metadata=entry.get("metadata", {}),
            )
            logger.info("  ✓ Indexed with chunking")
        except Exception as exc:
            logger.warning("  ✗ Failed: %s", exc)

    logger.info("")

    # ── Totals ───────────────────────────────────────────────────────────────
    total = policy_index_manager.count()
    logger.info("Total documents in index: %d", total)
    logger.info("")

    # ── Verification searches ────────────────────────────────────────────────
    logger.info("━━━ Verification Searches (index.run action='search') ━━━━━━━")
    test_queries = [
        "What are the rights of data subjects under GDPR?",
        "WHO International Health Regulations emergency committee",
        "Clean Air Act emission standards for major sources",
        "right to erasure personal data",
        "where are the Pyramids of Giza?",
    ]
    for query in test_queries:
        # results = policy_index_manager.search(query, top_k=3)
        # Get top 3 results
        results = policy_index_manager.search(query, top_k=1)
        logger.info("Query: '%s'", query)
        if results:
            for i, r in enumerate(results, 1):
                score = r.get("score", 0)
                snippet = r.get("text", "")[:90].replace("\n", " ")
                src = r.get("metadata", {}).get("source", "")
                logger.info(
                    "  %d. [%.3f] (%s) %s…", i, float(score), src, snippet
                )
        else:
            logger.info("  (no results met the relevance threshold of 0.7)")
        logger.info("")

    logger.info("═══════════════════════════════════════════════════════════")
    logger.info("Index setup complete!")
    logger.info("Add the following line to backend/.env:")
    logger.info("  POLICY_INDEX_ID=%s", index.id)
    logger.info("═══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
