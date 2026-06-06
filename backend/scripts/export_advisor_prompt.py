#!/usr/bin/env python
"""Phase 3 — export the Advisor's real system prompt for garak red-teaming.

garak must attack the *production* guardrails, not a bare model (runbook 03). The
Advisor's system message is assembled in ``app.agents.advisor`` from the PIS-17
role anchor, the PIS-24 hard-stop guardrails, the budget-justification guidance,
and an untrusted-data fence around the project context. This script renders that
exact prompt — pulled live from the module so it can never drift from the code —
and writes it where the garak config picks it up.

Run from the backend/ directory:

    uv run python scripts/export_advisor_prompt.py

Writes docs/evals/redteam/advisor_system_prompt.txt. No network, no secrets.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the `app` package importable when run as a plain script (mirrors the
# other eval scripts; pytest sets this via pythonpath, `python scripts/...`
# does not).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "docs" / "evals" / "redteam" / "advisor_system_prompt.txt"

# A benign, representative project context so the rendered prompt includes the
# untrusted-data fence the way production does. Nothing here is a secret.
_SAMPLE_CONTEXT = {
    "name": "Campus Wi-Fi Refresh",
    "company": "Northwind University",
    "description": "Replace 220 aging Wi-Fi 5 APs with cloud-managed Wi-Fi 6E.",
    "existing_infra": "220 legacy 802.11ac APs on an on-prem wireless controller.",
    "budget_ceiling": 400000.0,
}


def main() -> None:
    from app.agents.advisor import _build_system
    from app.schemas.project import ProjectContext

    system_prompt = _build_system(ProjectContext(**_SAMPLE_CONTEXT))
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(system_prompt)
    print(f"  wrote Advisor system prompt ({len(system_prompt)} chars)")
    print(f"  → {_OUT.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
