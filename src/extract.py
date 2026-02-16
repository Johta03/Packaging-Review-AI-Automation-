"""
Extraction step: brief text → structured ExtractedBrief.

The LLM does two things:
1. Claim interpretation & normalization: turns messy copy into claim objects with canonical types
   (e.g. "non-toxic" → CHEMICAL_SAFETY_CLAIM, "recyclable" → SUSTAINABILITY_CLAIM).
2. Issue discovery: finds what’s wrong or unclear (missing info, ambiguous age grade,
   risky claim wording, market-specific uncertainty).

Output is validated with Pydantic; one repair attempt if invalid.
"""
from pathlib import Path
from src.schemas import ExtractedBrief, ClaimObject, Issue
from src.llm import complete, extract_json_from_response, get_model
from src.audit import log_event

EXTRACTION_SYSTEM = """You are an expert at extracting and interpreting toy packaging briefs.
Output ONLY valid JSON matching this schema (no markdown, no explanation outside JSON):

{
  "product_name": "string",
  "age_grade": "string (e.g. 3+, 5+, 18m+)",
  "markets": ["AU", "US", "EU", "UK", "CA" or raw strings],
  "claims": [
    {
      "raw_text": "exact claim as stated",
      "normalized_type": "CHEMICAL_SAFETY_CLAIM | SUSTAINABILITY_CLAIM | PERFORMANCE_CLAIM | SAFETY_CLAIM | OTHER_CLAIM",
      "risk_keywords": ["keyword1", "keyword2"],
      "evidence_hint": "e.g. Requires supporting documentation",
      "severity": "low | medium | high"
    }
  ],
  "materials": ["plastic", "cardboard", etc. - lowercase],
  "licensed": true or false,
  "notes": "string or null",
  "missing_info": ["list of fields not found or unclear"],
  "clarifying_questions": ["questions for the client"],
  "issues": [
    {
      "type": "MISSING_INFO | AMBIGUOUS_AGE_GRADE | RISKY_CLAIM_WORDING | AMBIGUOUS_MARKET_REQUIREMENTS | OTHER",
      "message": "short description",
      "severity": "low | medium | high"
    }
  ]
}

Rules:
- Normalize each marketing claim into a claim object: raw_text, normalized_type (CHEMICAL_SAFETY for non-toxic/BPA, SUSTAINABILITY for recyclable/eco, PERFORMANCE for educational, SAFETY for safe, etc.), risk_keywords, evidence_hint, severity.
- Add issues for: missing info, ambiguous age grade, risky claim wording, market-specific uncertainty. Be specific in message.
- materials: lowercase, normalized (plastic, pvc, blister, cardboard, polyester).
- markets: use AU, US, EU, UK, CA where possible.
"""


def _normalize_claims(data: dict) -> None:
    if "claims" in data and data["claims"]:
        data["claims"] = [
            c if isinstance(c, dict) else {"raw_text": str(c), "normalized_type": "OTHER_CLAIM", "risk_keywords": [], "evidence_hint": "", "severity": "medium"}
            for c in data["claims"]
        ]
    if "issues" in data and data["issues"]:
        data["issues"] = [
            i if isinstance(i, dict) else {"type": "OTHER", "message": str(i), "severity": "medium"}
            for i in data["issues"]
        ]


def extract_brief(
    brief_text: str,
    audit_path: Path | None,
    run_id: str,
) -> ExtractedBrief | None:
    """Extract brief → ExtractedBrief (claim objects + issues). Validate; one repair on failure."""
    model_name = get_model()
    user_msg = "Extract and interpret this packaging brief (claims as objects, issues list).\n\nBrief:\n" + brief_text

    raw = complete(EXTRACTION_SYSTEM, user_msg, model=model_name)
    try:
        data = extract_json_from_response(raw)
        _normalize_claims(data)
        brief = ExtractedBrief.model_validate(data)
        if audit_path:
            log_event(audit_path, run_id, "extraction_ok", {"product_name": brief.product_name, "claims_count": len(brief.claims), "issues_count": len(brief.issues)}, model_name=model_name)
        return brief
    except Exception as e:
        if audit_path:
            log_event(audit_path, run_id, "extraction_repair_attempt", {"error": str(e)}, model_name=model_name)
        repair_user = "Previous output was invalid. Error:\n" + str(e) + "\n\nPrevious output:\n" + raw + "\n\nFix and output ONLY valid JSON for the same schema."
        raw2 = complete(EXTRACTION_SYSTEM, repair_user, model=model_name)
        try:
            data = extract_json_from_response(raw2)
            _normalize_claims(data)
            brief = ExtractedBrief.model_validate(data)
            if audit_path:
                log_event(audit_path, run_id, "extraction_repaired", {"product_name": brief.product_name}, model_name=model_name)
            return brief
        except Exception as e2:
            if audit_path:
                log_event(audit_path, run_id, "failure", {"stage": "extraction", "error": str(e2)}, model_name=model_name)
            return None
