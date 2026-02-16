# Packaging Review Automation

Takes a **toy packaging brief** (plain text), extracts claims and issues with an LLM, runs **deterministic risk rules**, and produces a **review packet**. Includes a Streamlit UI and a CLI.

---

## What it does

1. **Extract** – LLM turns the brief into structured data: **claim objects** (e.g. "non-toxic" → CHEMICAL_SAFETY_CLAIM) and an **issues** list (missing info, ambiguous age, risky wording).
2. **Risk** – Python rules (no LLM) decide who must review (Quality, Legal, Licensing, Sustainability) and risk level (low/medium/high). Same input → same result.
3. **Packet** – LLM drafts the review document, then a **critique** step checks it (required sections, no invented facts). One revision if needed.

Outputs: `extracted.json`, `decision.json`, `review_packet.md`, `audit.jsonl`.

---

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Set your API key (copy .env.example to .env)
# Use Groq (free): LLM_PROVIDER=groq, GROQ_API_KEY=your-key
# Or OpenAI: LLM_PROVIDER=openai, OPENAI_API_KEY=your-key

# 3. Run the app
streamlit run app.py
```

Or run from the command line (no UI):

```bash
python -m src.run --input examples/brief_01.txt --out outputs
```

Use `--demo` to skip the LLM (built-in data only):

```bash
python -m src.run --input examples/brief_01.txt --out outputs --demo
```

---

## Flow

```
Brief (text)  →  Extract (LLM: claims + issues)  →  Risk (Python rules)  →  Packet (LLM draft + critique)  →  Outputs
```

- **LLM:** extraction, packet draft, critique/revise.
- **Code:** risk rules, validation, audit log.

---

## Project structure

| Path | Purpose |
|------|--------|
| `app.py` | Streamlit UI – paste brief, run, see claims/issues/risk/packet |
| `src/run.py` | CLI – same workflow from the command line |
| `src/schemas.py` | Data shapes: ClaimObject, Issue, ExtractedBrief, ReviewDecision |
| `src/extract.py` | Brief → ExtractedBrief (claim objects + issues); one repair if invalid |
| `src/risk.py` | ExtractedBrief → ReviewDecision (deterministic rules) |
| `src/packet.py` | Draft review packet (LLM + critique loop) or template (demo) |
| `src/llm.py` | LLM client (OpenAI / Groq / Ollama via .env) |
| `src/audit.py` | Append-only JSONL log per run |
| `src/utils.py` | run_id, read_brief, ensure_output_dir |
| `examples/` | Sample briefs |
| `tests/` | Risk tests (no LLM) |

---

## Run commands

| Goal | Command |
|------|--------|
| Web UI | `streamlit run app.py` |
| CLI (real LLM) | `python -m src.run --input examples/brief_01.txt --out outputs` |
| CLI (demo, no API) | `python -m src.run --input examples/brief_01.txt --out outputs --demo` |
| Tests | `pytest tests/ -v` |

---

## Push to GitHub

1. **Create a new repo on GitHub**  
   Go to [github.com/new](https://github.com/new). Name it (e.g. `packaging-review-automation`). Do **not** add a README or .gitignore (you already have them).

2. **Init and push from your machine** (run from the project folder):

   ```bash
   git init
   git add .
   git commit -m "Initial commit: packaging review automation"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

   Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your GitHub username and repo name.

3. **Keep secrets out of the repo**  
   `.env` is in `.gitignore`; only commit `.env.example` (with placeholder keys).
