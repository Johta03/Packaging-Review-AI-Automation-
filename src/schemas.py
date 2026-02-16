"""
Data shapes for the packaging review workflow.

- ExtractedBrief: what the LLM extracts from the brief (claim objects + issues).
- ReviewDecision: what the risk rules produce (who must review, risk level).
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# --- Claim interpretation: messy copy → canonical categories ---

class ClaimObject(BaseModel):
    """One marketing claim, normalized into a category and severity."""

    raw_text: str
    normalized_type: str  # CHEMICAL_SAFETY_CLAIM, SUSTAINABILITY_CLAIM, PERFORMANCE_CLAIM, SAFETY_CLAIM, OTHER_CLAIM
    risk_keywords: List[str] = Field(default_factory=list)
    evidence_hint: str = ""
    severity: Literal["low", "medium", "high"] = "medium"


# --- Issue discovery: what’s wrong or unclear in the brief ---

class Issue(BaseModel):
    """One issue the LLM found (missing info, ambiguity, risky wording, etc.)."""

    type: str  # MISSING_INFO, AMBIGUOUS_AGE_GRADE, RISKY_CLAIM_WORDING, AMBIGUOUS_MARKET_REQUIREMENTS, OTHER
    message: str
    severity: Literal["low", "medium", "high"] = "medium"


# --- Extracted brief (output of extraction step) ---

class ExtractedBrief(BaseModel):
    """Structured brief: claim objects, issues list, and core fields."""

    product_name: str
    age_grade: str
    markets: List[str] = Field(default_factory=list)
    claims: List[ClaimObject] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    licensed: bool
    notes: Optional[str] = None
    missing_info: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    issues: List[Issue] = Field(default_factory=list)


# --- Risk decision (output of risk step; deterministic) ---

class ReviewDecision(BaseModel):
    """Who must review and overall risk level. Set by Python rules, not the LLM."""

    requires_quality_review: bool = False
    requires_legal_review: bool = False
    requires_licensing_review: bool = False
    requires_sustainability_review: bool = False
    risk_flags: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    routing_notes: List[str] = Field(default_factory=list)
    human_approval_required: bool = False
