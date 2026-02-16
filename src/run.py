"""
CLI: run the full workflow.

  brief (.txt) → extract (claim objects + issues) → risk (deterministic) → packet (draft + critique) → outputs

Outputs: extracted.json, decision.json, review_packet.md, audit.jsonl
"""
import argparse
from pathlib import Path
from src.utils import generate_run_id, read_brief, ensure_output_dir
from src.audit import log_event
from src.extract import extract_brief
from src.risk import classify_risk
from src.packet import generate_packet
from src.llm import get_model
from src.schemas import ExtractedBrief, ClaimObject, Issue

DEMO_BRIEF = ExtractedBrief(
    product_name="Disney Junior Wooden Blocks",
    age_grade="18m+",
    markets=["US", "UK", "AU"],
    claims=[
        ClaimObject(raw_text="Non-toxic", normalized_type="CHEMICAL_SAFETY_CLAIM", risk_keywords=["non-toxic"], evidence_hint="Requires test report", severity="high"),
        ClaimObject(raw_text="BPA-free", normalized_type="CHEMICAL_SAFETY_CLAIM", risk_keywords=["bpa"], evidence_hint="Requires documentation", severity="high"),
        ClaimObject(raw_text="Safe for toddlers", normalized_type="SAFETY_CLAIM", risk_keywords=["safe"], evidence_hint="", severity="medium"),
    ],
    materials=["wood", "plastic", "cardboard"],
    licensed=True,
    notes="Licensed character imagery.",
    missing_info=[],
    clarifying_questions=[],
    issues=[Issue(type="AMBIGUOUS_AGE_GRADE", message="Age 18m+ targets under-3; quality review needed.", severity="high")],
)


def run(input_path: str, out_base: str, demo: bool = False) -> None:
    run_id = generate_run_id()
    out_dir = ensure_output_dir(out_base, run_id)
    audit_path = out_dir / "audit.jsonl"

    brief_text = read_brief(input_path)
    log_event(audit_path, run_id, "input_received", {"input_path": str(input_path), "length": len(brief_text), "demo": demo})

    if demo:
        brief = DEMO_BRIEF
        log_event(audit_path, run_id, "extraction_ok", {"product_name": brief.product_name, "demo": True})
    else:
        brief = extract_brief(brief_text, audit_path, run_id)
        if brief is None:
            print("ERROR: Extraction failed. See audit.jsonl.")
            return

    decision = classify_risk(brief)
    log_event(audit_path, run_id, "risk_classified", {"risk_level": decision.risk_level, "risk_flags": decision.risk_flags})

    model_name = "demo (no LLM)" if demo else get_model()
    packet_md = generate_packet(brief, decision, run_id, model_name, audit_path=audit_path, use_llm=not demo)
    log_event(audit_path, run_id, "packet_generated", {})

    (out_dir / "extracted.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "decision.json").write_text(decision.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "review_packet.md").write_text(packet_md, encoding="utf-8")
    log_event(audit_path, run_id, "outputs_written", {})

    if demo:
        print("(Demo mode: no LLM; used built-in brief)")
    print(f"Run ID: {run_id}")
    print(f"Risk level: {decision.risk_level}")
    print(f"Output folder: {out_dir}")


def main() -> None:
    p = argparse.ArgumentParser(description="Packaging review: brief → extract → risk → packet")
    p.add_argument("--input", required=True, help="Path to brief .txt")
    p.add_argument("--out", default="outputs", help="Output folder")
    p.add_argument("--demo", action="store_true", help="Skip LLM; use built-in brief")
    args = p.parse_args()
    run(args.input, args.out, demo=args.demo)


if __name__ == "__main__":
    main()
