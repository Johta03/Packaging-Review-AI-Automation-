"""Golden-case tests: no LLM. Use ExtractedBrief (claim objects + issues) and assert risk + schema."""
from src.schemas import ExtractedBrief, ReviewDecision, ClaimObject, Issue
from src.risk import classify_risk


def test_high_risk_under3_licensed_claims() -> None:
    brief = ExtractedBrief(
        product_name="Disney Junior Wooden Blocks",
        age_grade="18m+",
        markets=["US", "UK", "AU"],
        claims=[
            ClaimObject(raw_text="Non-toxic", normalized_type="CHEMICAL_SAFETY_CLAIM", risk_keywords=["non-toxic"], evidence_hint="", severity="high"),
            ClaimObject(raw_text="BPA-free", normalized_type="CHEMICAL_SAFETY_CLAIM", risk_keywords=["bpa"], evidence_hint="", severity="high"),
        ],
        materials=["wood", "plastic", "cardboard"],
        licensed=True,
        notes="",
        missing_info=[],
        clarifying_questions=[],
        issues=[],
    )
    decision = classify_risk(brief)
    assert decision.risk_level == "high"
    assert decision.requires_quality_review is True
    assert decision.requires_legal_review is True
    assert decision.requires_licensing_review is True
    assert decision.requires_sustainability_review is True
    assert decision.human_approval_required is True
    assert "under_3" in decision.risk_flags
    assert "licensed_brand" in decision.risk_flags
    assert "claims_need_evidence" in decision.risk_flags
    assert "plastic_present" in decision.risk_flags
    ReviewDecision.model_validate(decision.model_dump())


def test_low_risk_5plus_minimal() -> None:
    brief = ExtractedBrief(
        product_name="Classic Building Bricks Set",
        age_grade="5+",
        markets=["US", "CA"],
        claims=[ClaimObject(raw_text="Compatible with major brands", normalized_type="OTHER_CLAIM", risk_keywords=[], evidence_hint="", severity="low")],
        materials=["cardboard"],
        licensed=False,
        notes="",
        missing_info=[],
        clarifying_questions=[],
        issues=[],
    )
    decision = classify_risk(brief)
    assert decision.risk_level == "low"
    assert decision.requires_quality_review is False
    assert decision.requires_legal_review is False
    assert decision.requires_licensing_review is False
    assert decision.requires_sustainability_review is False
    assert decision.human_approval_required is False
    assert len(decision.risk_flags) == 0
    ReviewDecision.model_validate(decision.model_dump())


def test_medium_risk_3plus_plastic_recyclable_claim() -> None:
    brief = ExtractedBrief(
        product_name="Eco Stacking Cups",
        age_grade="3+",
        markets=["EU", "UK"],
        claims=[
            ClaimObject(raw_text="Recyclable", normalized_type="SUSTAINABILITY_CLAIM", risk_keywords=["recyclable"], evidence_hint="", severity="medium"),
            ClaimObject(raw_text="Eco-friendly packaging", normalized_type="SUSTAINABILITY_CLAIM", risk_keywords=["eco-friendly"], evidence_hint="", severity="medium"),
        ],
        materials=["plastic", "cardboard", "blister"],
        licensed=False,
        notes="",
        missing_info=[],
        clarifying_questions=[],
        issues=[],
    )
    decision = classify_risk(brief)
    assert decision.risk_level == "medium"
    assert decision.requires_legal_review is True
    assert decision.requires_sustainability_review is True
    assert decision.requires_quality_review is False
    assert decision.requires_licensing_review is False
    assert decision.human_approval_required is True
    assert "claims_need_evidence" in decision.risk_flags
    assert "plastic_present" in decision.risk_flags
    ReviewDecision.model_validate(decision.model_dump())
