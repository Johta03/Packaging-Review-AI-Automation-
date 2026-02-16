"""
Review packet step: ExtractedBrief + ReviewDecision → Markdown packet.

Two modes:
1. Demo: template-only (no LLM), for runs without API.
2. Normal: LLM drafts the packet from extracted + decision; then a critique loop checks
   the draft against a rubric (required sections? invented facts? warnings as suggestions?)
   and revises once if needed.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from src.schemas import ExtractedBrief, ReviewDecision
from src.llm import complete, get_model
from src.audit import log_event

PROMPT_VERSION = os.getenv("PROMPT_VERSION", "packet-draft-001")

DRAFT_SYSTEM = """You write a Packaging Review Packet in Markdown. You will receive structured data (extracted brief + risk decision). Your draft must:
- Include: Summary (product, markets, age grade, licensed), Claims (as a table or list with type and severity), Issues discovered (if any), Materials, Risk (level and flags), Required Approvals, Checklist (Markdown checkboxes), Clarifying questions (if any).
- Be grounded ONLY in the provided data. Do not invent facts.
- State any warnings or recommendations as suggestions, not as definitive conclusions.
- Use clear headings and bullets. Output only the Markdown document, no preamble."""

CRITIQUE_SYSTEM = """You are a reviewer of a Packaging Review Packet (Markdown). Check the draft against this rubric:
1. Required sections present: Summary, Claims, Issues (or "None"), Materials, Risk, Required Approvals, Checklist, (optional) Clarifying questions.
2. No invented facts: everything must come from the provided context.
3. Warnings/recommendations are stated as suggestions (e.g. "Legal review recommended") not as conclusions.

If the draft fails any point, reply with a short list of fixes (e.g. "Add Issues section", "Remove invented claim X", "Rephrase as suggestion"). If the draft is fine, reply with exactly: OK"""


def _template_packet(brief: ExtractedBrief, decision: ReviewDecision, run_id: str, model_name: str) -> str:
    """Build packet from template (no LLM). Used in demo mode."""
    lines = [
        "# Packaging Review Packet",
        "",
        "## Summary",
        f"- **Product:** {brief.product_name}",
        f"- **Markets:** {', '.join(brief.markets) or 'Not specified'}",
        f"- **Age grade:** {brief.age_grade}",
        f"- **Licensed:** {'Yes' if brief.licensed else 'No'}",
        "",
        "## Claims",
    ]
    if brief.claims:
        lines.append("| Raw text | Type | Severity |")
        lines.append("| --- | --- | --- |")
        for c in brief.claims:
            lines.append(f"| {c.raw_text} | {c.normalized_type} | {c.severity} |")
        if decision.requires_legal_review:
            lines.append("\n*Evidence needed – legal review required.*")
    else:
        lines.append("- (None)")
    lines.append("")
    lines.append("## Issues")
    if brief.issues:
        for i in brief.issues:
            lines.append(f"- [{i.type}] {i.message} ({i.severity})")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Materials")
    lines.append(", ".join(brief.materials) if brief.materials else "(None)")
    if decision.requires_sustainability_review:
        lines.append("\n*Sustainability review flagged.*")
    lines.append("")
    lines.append("## Risk")
    lines.append(f"- **Risk level:** {decision.risk_level}")
    lines.append(f"- **Flags:** {', '.join(decision.risk_flags) or 'None'}")
    lines.append("")
    lines.append("## Required Approvals")
    revs = []
    if decision.requires_quality_review: revs.append("Quality")
    if decision.requires_legal_review: revs.append("Legal")
    if decision.requires_licensing_review: revs.append("Licensing")
    if decision.requires_sustainability_review: revs.append("Sustainability")
    lines.append("\n".join(f"- {r}" for r in revs) if revs else "- None")
    lines.append("")
    lines.append("## Checklist")
    lines.append("- [ ] Quality review (if required)")
    lines.append("- [ ] Legal review (if required)")
    lines.append("- [ ] Licensing review (if required)")
    lines.append("- [ ] Sustainability review (if required)")
    lines.append("- [ ] Human approval (if required)")
    if brief.clarifying_questions:
        lines.append("")
        lines.append("## Clarifying Questions")
        for q in brief.clarifying_questions:
            lines.append(f"- {q}")
    lines.append("")
    lines.append("---")
    lines.append(f"*Run ID:* `{run_id}` | *Model:* {model_name} | *Prompt:* {PROMPT_VERSION}")
    return "\n".join(lines)


def _required_approvals(decision: ReviewDecision) -> list[str]:
    """List of approval types required (Quality, Legal, Licensing, Sustainability)."""
    out = []
    if decision.requires_quality_review: out.append("Quality")
    if decision.requires_legal_review: out.append("Legal")
    if decision.requires_licensing_review: out.append("Licensing")
    if decision.requires_sustainability_review: out.append("Sustainability")
    return out


def _build_context(brief: ExtractedBrief, decision: ReviewDecision) -> str:
    """JSON summary for the LLM."""
    return json.dumps({
        "product_name": brief.product_name,
        "age_grade": brief.age_grade,
        "markets": brief.markets,
        "licensed": brief.licensed,
        "claims": [{"raw_text": c.raw_text, "normalized_type": c.normalized_type, "severity": c.severity} for c in brief.claims],
        "issues": [{"type": i.type, "message": i.message, "severity": i.severity} for i in brief.issues],
        "materials": brief.materials,
        "risk_level": decision.risk_level,
        "risk_flags": decision.risk_flags,
        "required_approvals": _required_approvals(decision),
        "clarifying_questions": brief.clarifying_questions,
    }, indent=2)


def generate_packet(
    brief: ExtractedBrief,
    decision: ReviewDecision,
    run_id: str,
    model_name: str,
    audit_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    """
    Produce the review packet Markdown.
    If use_llm is False (demo), use template. Otherwise: LLM draft → critique → revise once if needed.
    """
    if not use_llm:
        return _template_packet(brief, decision, run_id, model_name)

    context = _build_context(brief, decision)
    user_draft = f"Context (extracted brief + decision):\n{context}\n\nWrite the Packaging Review Packet in Markdown."
    draft = complete(DRAFT_SYSTEM, user_draft, model=model_name)
    draft = draft.strip()
    if draft.startswith("```"):
        for start in ["```markdown", "```md", "```"]:
            if draft.startswith(start):
                draft = draft[len(start):].strip()
                break
        if draft.endswith("```"):
            draft = draft[:-3].strip()

    critique_user = f"Context:\n{context}\n\nDraft packet:\n{draft}\n\nCheck the draft against the rubric and reply with fixes or OK."
    critique = complete(CRITIQUE_SYSTEM, critique_user, model=model_name).strip().upper()
    if "OK" in critique and "ADD " not in critique and "REMOVE " not in critique and "REPHRASE " not in critique:
        if audit_path:
            log_event(audit_path, run_id, "packet_generated", {"critique": "ok"}, model_name=model_name)
        return draft

    revise_user = f"Context:\n{context}\n\nDraft:\n{draft}\n\nRequested fixes:\n{critique}\n\nOutput the revised Markdown packet only."
    revised = complete(DRAFT_SYSTEM, revise_user, model=model_name).strip()
    if revised.startswith("```"):
        for start in ["```markdown", "```md", "```"]:
            if revised.startswith(start):
                revised = revised[len(start):].strip()
                break
        if revised.endswith("```"):
            revised = revised[:-3].strip()
    if audit_path:
        log_event(audit_path, run_id, "packet_revised", {"after_critique": True}, model_name=model_name)
    return revised
