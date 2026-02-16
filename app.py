"""
Streamlit UI: paste a brief (or pick an example), run the workflow, see claims, issues, decision, and packet.

Run: streamlit run app.py
"""
from pathlib import Path
import streamlit as st
from src.utils import generate_run_id, read_brief, ensure_output_dir
from src.audit import log_event
from src.extract import extract_brief
from src.risk import classify_risk
from src.packet import generate_packet
from src.llm import get_model
from src.schemas import ExtractedBrief

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUTS = PROJECT_ROOT / "outputs"


st.set_page_config(page_title="Packaging Review", layout="wide")
st.title("Packaging Review")
st.caption("Paste a brief → Extract (claim objects + issues) → Risk (deterministic) → Packet (draft + critique)")

example_dir = PROJECT_ROOT / "examples"
examples = sorted(example_dir.glob("brief_*.txt")) if example_dir.exists() else []
brief_text = ""
if examples:
    choice = st.radio("Example brief", [p.name for p in examples], horizontal=True)
    if choice:
        brief_text = read_brief(example_dir / choice)
custom = st.text_area("Or paste your own brief", height=120, placeholder="Product: ...\nAge: ...\nMarkets: ...\nClaims: ...")
run_text = (custom.strip() if custom else brief_text).strip()

if st.button("Run", type="primary") and run_text:
    run_id = generate_run_id()
    out_dir = ensure_output_dir(OUTPUTS, run_id)
    audit_path = out_dir / "audit.jsonl"
    log_event(audit_path, run_id, "input_received", {"length": len(run_text)})

    with st.spinner("Extracting (claim objects + issues)…"):
        brief = extract_brief(run_text, audit_path, run_id)
    if not brief:
        st.error("Extraction failed. Check audit in the run folder.")
        st.stop()

    decision = classify_risk(brief)
    log_event(audit_path, run_id, "risk_classified", {"risk_level": decision.risk_level})

    model_name = get_model()
    with st.spinner("Drafting packet + critique…"):
        packet_md = generate_packet(brief, decision, run_id, model_name, audit_path=audit_path, use_llm=True)
    log_event(audit_path, run_id, "packet_generated", {})

    (out_dir / "extracted.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "decision.json").write_text(decision.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "review_packet.md").write_text(packet_md, encoding="utf-8")
    log_event(audit_path, run_id, "outputs_written", {})

    st.success(f"Run ID: `{run_id}`")
    st.metric("Risk level", decision.risk_level)
    revs = []
    if decision.requires_quality_review: revs.append("Quality")
    if decision.requires_legal_review: revs.append("Legal")
    if decision.requires_licensing_review: revs.append("Licensing")
    if decision.requires_sustainability_review: revs.append("Sustainability")
    st.write("**Required reviews:**", ", ".join(revs) if revs else "None")

    st.subheader("Claims (normalized)")
    if brief.claims:
        st.dataframe([{"Raw text": c.raw_text, "Type": c.normalized_type, "Severity": c.severity} for c in brief.claims], use_container_width=True)
    else:
        st.info("No claims")

    st.subheader("Issues discovered")
    if brief.issues:
        st.dataframe([{"Type": i.type, "Message": i.message, "Severity": i.severity} for i in brief.issues], use_container_width=True)
    else:
        st.info("No issues")

    st.subheader("Review packet")
    st.markdown(packet_md[:4000] + ("…" if len(packet_md) > 4000 else ""))
    st.caption(f"Outputs in `outputs/{run_id}/`")
