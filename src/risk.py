"""
Risk step: ExtractedBrief → ReviewDecision (deterministic, no LLM).

Uses claim types and severity, under-3 age, licensed flag, materials (plastic), and high-severity issues
to set who must review (Quality, Legal, Licensing, Sustainability) and overall risk level.
"""
from src.schemas import ExtractedBrief, ReviewDecision, ClaimObject, Issue

MATERIAL_PLASTIC = ["plastic", "pvc", "blister"]
UNDER_3_INDICATORS = ["0", "1", "2", "18m", "24m", "under 3", "under three"]
LEGAL_CLAIM_TYPES = {"CHEMICAL_SAFETY_CLAIM", "SUSTAINABILITY_CLAIM", "PERFORMANCE_CLAIM", "SAFETY_CLAIM"}


def _age_under_3(age_grade: str) -> bool:
    ag = (age_grade or "").lower().strip()
    return any(x in ag for x in UNDER_3_INDICATORS)


def _plastic_present(materials: list[str]) -> bool:
    return any((m or "").lower().strip() in MATERIAL_PLASTIC for m in materials)


def _claims_need_evidence(claims: list[ClaimObject]) -> bool:
    for c in claims:
        if c.normalized_type in LEGAL_CLAIM_TYPES or c.severity == "high":
            return True
    return False


def _high_severity_issues(issues: list[Issue]) -> bool:
    return any(i.severity == "high" for i in issues)


def classify_risk(brief: ExtractedBrief) -> ReviewDecision:
    """Compute who must review and risk level from the extracted brief."""
    requires_quality_review = False
    requires_legal_review = False
    requires_licensing_review = False
    requires_sustainability_review = False
    risk_flags: list[str] = []
    routing_notes: list[str] = []

    if _age_under_3(brief.age_grade):
        requires_quality_review = True
        risk_flags.append("under_3")
        routing_notes.append("Age grade under 3: quality review required.")

    if brief.licensed:
        requires_licensing_review = True
        risk_flags.append("licensed_brand")
        routing_notes.append("Licensed product: licensing review required.")

    if _claims_need_evidence(brief.claims):
        requires_legal_review = True
        risk_flags.append("claims_need_evidence")
        routing_notes.append("Marketing claims require legal/evidence review.")

    if _plastic_present(brief.materials):
        requires_sustainability_review = True
        risk_flags.append("plastic_present")
        routing_notes.append("Plastic/PVC/blister: sustainability review recommended.")

    if brief.issues and _high_severity_issues(brief.issues):
        risk_flags.append("high_severity_issues")
        routing_notes.append("High-severity issues from brief require attention.")

    human_approval_required = (
        "under_3" in risk_flags or "licensed_brand" in risk_flags or "claims_need_evidence" in risk_flags
    )
    n_flags = len(risk_flags)
    if "under_3" in risk_flags or "licensed_brand" in risk_flags:
        risk_level = "high"
    elif n_flags >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return ReviewDecision(
        requires_quality_review=requires_quality_review,
        requires_legal_review=requires_legal_review,
        requires_licensing_review=requires_licensing_review,
        requires_sustainability_review=requires_sustainability_review,
        risk_flags=risk_flags,
        risk_level=risk_level,
        routing_notes=routing_notes,
        human_approval_required=human_approval_required,
    )
