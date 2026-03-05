"""
Custom Python tools used by the Policy Navigator agent.

Each function is self-contained (imports + constants inside the body) because
the aiXplain Python Sandbox only receives the function source via
inspect.getsource().
"""


def search_federal_register(query: str, per_page: int = 5) -> str:
    """
    Search the Federal Register API for policy documents, executive orders,
    and federal regulations.

    Args:
        query: Natural language search query (e.g. "Executive Order 14067")
        per_page: Number of results to return (default 5, minimum 3)

    Returns:
        JSON string with list of matching documents including title, date,
        document number, and abstract.
    """
    import json
    import urllib.request
    import urllib.parse

    FEDERAL_REGISTER_API_BASE = "https://www.federalregister.gov/api/v1"

    per_page = max(per_page, 3)  # Always fetch enough to see revoking docs

    params = urllib.parse.urlencode(
        {
            "conditions[term]": query,
            "per_page": per_page,
            "fields[]": ["title", "document_number", "publication_date", "abstract", "type", "agencies", "executive_order_notes"],
        },
        doseq=True,
    )
    url = f"{FEDERAL_REGISTER_API_BASE}/documents.json?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return json.dumps({"results": [], "message": "No matching documents found in Federal Register."})

        simplified = [
            {
                "title": r.get("title"),
                "document_number": r.get("document_number"),
                "publication_date": r.get("publication_date"),
                "type": r.get("type"),
                "abstract": (r.get("abstract") or "")[:500],
                "executive_order_notes": r.get("executive_order_notes"),
                "agencies": [a.get("name") for a in (r.get("agencies") or [])],
                "url": f"https://www.federalregister.gov/documents/{r.get('document_number', '')}",
            }
            for r in results
        ]
        return json.dumps({"results": simplified, "total_count": data.get("count", 0)})
    except Exception as exc:
        return json.dumps({"error": str(exc), "results": []})


def get_federal_register_document(document_number: str) -> str:
    """
    Retrieve full details of a specific Federal Register document by its
    document number.

    Args:
        document_number: The Federal Register document number
                         (e.g. "2022-02876" for EO 14067)

    Returns:
        JSON string with full document metadata and body text excerpt.
    """
    import json
    import urllib.request

    FEDERAL_REGISTER_API_BASE = "https://www.federalregister.gov/api/v1"

    url = f"{FEDERAL_REGISTER_API_BASE}/documents/{document_number}.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        return json.dumps(
            {
                "title": data.get("title"),
                "document_number": data.get("document_number"),
                "publication_date": data.get("publication_date"),
                "effective_on": data.get("effective_on"),
                "type": data.get("type"),
                "abstract": (data.get("abstract") or "")[:1000],
                "body_html_url": data.get("body_html_url"),
                "raw_text_url": data.get("raw_text_url"),
                "signing_date": data.get("signing_date"),
                "president": data.get("president", {}).get("name") if data.get("president") else None,
                "agencies": [a.get("name") for a in (data.get("agencies") or [])],
                "citation": data.get("citation"),
            }
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def search_case_law(query: str, court: str = None, per_page: int = 3) -> str:
    """
    Search CourtListener for case law referencing specific regulations,
    statutes, or legal topics.

    Args:
        query: The full user question (e.g., "Has Section 230 been challenged?")
        court: Optional court abbreviation (e.g., "scotus", "ca9")
        per_page: Number of results to return (default 3, max 5)

    Returns:
        JSON string with MINIMAL case info (name, court, date, snippet, url) to save tokens.
    """
    import json
    import os
    import urllib.request
    import urllib.parse

    COURT_LISTENER_API_BASE = "https://www.courtlistener.com/api/rest/v4"
    COURT_LISTENER_TOKEN = os.environ.get("COURT_LISTENER_TOKEN", "")

    # Use full query as-is for semantic search (no keyword extraction)
    clean_query = query.strip()[:300]

    params: dict = {
        "q": clean_query,
        "type": "o",  # Case law opinions
    }
    # "semantic": "true",  # Enable semantic search per CourtListener docs
    if court and court.lower() not in ("all", "any", "none", ""):
        params["court"] = court

    encoded = urllib.parse.urlencode(params)
    url = f"{COURT_LISTENER_API_BASE}/search/?{encoded}"

    headers = {
        "Accept": "application/json",
    }
    if COURT_LISTENER_TOKEN:
        headers["Authorization"] = f"Token {COURT_LISTENER_TOKEN}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read())

        results = data.get("results", [])
        if not results:
            return json.dumps({
                "results": [],
                "message": f"No matching case law found for '{clean_query}'."
            })

        # Extract ONLY essential fields to reduce token costs
        simplified = []
        for r in results[:min(per_page, 5)]:
            # Get first opinion's snippet (if opinions array exists)
            snippet = ""
            opinions = r.get("opinions", [])
            if opinions and len(opinions) > 0:
                snippet = opinions[0].get("snippet", "")[:300]
            
            # Clean snippet - remove HTML highlights
            snippet = snippet.replace("<mark>", "").replace("</mark>", "").strip()

            simplified.append({
                "case_name": r.get("caseName"),
                "court": r.get("court"),
                "date_filed": r.get("dateFiled"),
                "citation": r.get("citation", [])[:2],  # Limit citations
                "snippet": snippet,
                "url": f"https://www.courtlistener.com{r.get('absolute_url', '')}",
            })

        return json.dumps({
            "results": simplified,
            "total_count": data.get("count", len(results)),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc), "results": []})
