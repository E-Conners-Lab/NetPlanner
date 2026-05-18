"""Pydantic schemas — request/response models and agent handoff contracts.

All handoff contracts (PIS-15) are validated here before crossing an agent
boundary. `Confidence` is the canonical pricing-confidence type.
"""

from app.schemas.comparison import (
    ComparisonCell,
    ComparisonRequest,
    ComparisonResult,
    VendorComparisonRead,
)
from app.schemas.conversation import (
    AdvisorRequest,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.schemas.project import (
    ProjectContext,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.report import ReportArtifact, ReportRead, ReportRequest
from app.schemas.research import Confidence, ResearchItem, ResearchResult
from app.schemas.tco import (
    TCOFormInputs,
    TCOResult,
    TCOScenarioCreate,
    TCOScenarioRead,
    YearCost,
)

__all__ = [
    # research
    "Confidence",
    "ResearchItem",
    "ResearchResult",
    # project
    "ProjectContext",
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
    # conversation
    "AdvisorRequest",
    "ConversationRead",
    "MessageCreate",
    "MessageRead",
    # tco
    "TCOFormInputs",
    "TCOResult",
    "TCOScenarioCreate",
    "TCOScenarioRead",
    "YearCost",
    # comparison
    "ComparisonCell",
    "ComparisonRequest",
    "ComparisonResult",
    "VendorComparisonRead",
    # report
    "ReportArtifact",
    "ReportRead",
    "ReportRequest",
]
