"""Research Agent (PIS-11).

Model: ``claude-haiku-4-5`` — fast, cost-efficient web search + structured
extraction (PIS-29). Uses the single ``web_search`` tool (PIS-19).

Confidence policy (PIS-27): defaults to ``estimated``; ``confirmed`` requires
an official vendor pricing page or datasheet; ``unavailable`` when web search
returns nothing usable. Results are capped at 3 per query (PIS-14, PIS-26).
"""

from __future__ import annotations

from app.schemas.research import ResearchResult


async def research(query: str) -> ResearchResult:
    """Search the web for current vendor pricing and product details.

    Args:
        query: A vendor / product / pricing-tier query string.

    Returns:
        ResearchResult: ``{query, results: [ResearchItem, ...]}`` — at most 3
        results, each carrying a ``confidence`` indicator (PIS-15).

    Raises:
        NotImplementedError: Always — implemented in Phase 2.
    """
    raise NotImplementedError("Research Agent — implemented in Phase 2")
