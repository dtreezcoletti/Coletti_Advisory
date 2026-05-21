"""
Coletti OS — Legal Citation Engine
Queries the CourtListener API (Free Law Project) to surface Tennessee
appellate decisions relevant to marital dissipation, income concealment,
and civil procedure sanctions. No API key required for basic search.
"""

import re
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"

# Tennessee courts on CourtListener
TN_COURTS = {
    "Tennessee Supreme Court":         "tenn",
    "Tennessee Court of Appeals":      "tennctapp",
    "Tennessee Court of Criminal Appeals": "tennctcrimapp",
}

# Pre-built query topics relevant to this case
TOPIC_QUERIES = {
    "Marital Dissipation":       "marital dissipation assets divorce Tennessee",
    "Income Concealment":        "income concealment financial affidavit Tennessee divorce",
    "Rule 36 Deemed Admissions": "deemed admissions Rule 36 Tennessee discovery sanctions",
    "Rule 37 Sanctions":         "Rule 37 discovery sanctions attorney fees Tennessee",
    "Pendente Lite Support":     "pendente lite support temporary alimony Tennessee",
    "Business Valuation":        "business valuation marital asset divorce Tennessee",
    "Punitive Damages Divorce":  "punitive damages assault domestic violence divorce Tennessee",
}


def search_cases(query: str, court: str = "tennctapp", page_size: int = 8) -> list[dict]:
    """
    Search CourtListener for opinions matching query.
    Returns list of case dicts with citation fields.
    """
    if not REQUESTS_AVAILABLE:
        return [{"error": "requests not installed. Run: pip install requests"}]

    try:
        resp = requests.get(
            f"{COURTLISTENER_BASE}/search/",
            params={
                "q": query,
                "type": "o",          # opinions
                "court": court,
                "order_by": "score desc",
                "page_size": page_size,
            },
            timeout=10,
            headers={"User-Agent": "ColettiOS/2.7 (legal research tool)"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
        return [{"error": str(e)}]


def format_citation(case: dict) -> str:
    """Format a CourtListener result into a legal citation string."""
    if "error" in case:
        return f"[Error: {case['error']}]"

    name     = case.get("caseName") or case.get("case_name") or "Unknown v. Unknown"
    citation = (case.get("citation") or [{}])
    if isinstance(citation, list) and citation:
        cite_str = citation[0] if isinstance(citation[0], str) else str(citation[0])
    else:
        cite_str = ""

    court    = case.get("court_id") or case.get("court") or ""
    date_raw = case.get("dateFiled") or case.get("date_filed") or ""
    if date_raw:
        try:
            date_str = datetime.fromisoformat(date_raw[:10]).strftime("%Y")
        except ValueError:
            date_str = date_raw[:4]
    else:
        date_str = ""

    url      = case.get("absolute_url") or ""
    full_url = f"https://www.courtlistener.com{url}" if url else ""

    parts = [name]
    if cite_str:
        parts.append(cite_str)
    if court or date_str:
        parts.append(f"({court} {date_str})".strip())

    citation_line = ", ".join(p for p in parts if p)
    if full_url:
        citation_line += f"\n    {full_url}"
    return citation_line


def get_snippet(case: dict, max_chars: int = 300) -> str:
    """Extract the most relevant text snippet from a case result."""
    snippet = (case.get("snippet") or case.get("text") or
               case.get("syllabus") or "No preview available.")
    # Strip HTML tags
    snippet = re.sub(r'<[^>]+>', '', snippet)
    return snippet[:max_chars].strip() + ("…" if len(snippet) > max_chars else "")
