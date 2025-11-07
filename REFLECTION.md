# Lab 9 – Reflection: RAG vs Structured Evaluation

This reflection summarizes how we evaluated the two pipelines (RAG vs Structured), the signals used for each rubric criterion, the observed patterns across five companies (Anthropic, Abridge, Anysphere, Baseten, Clay), and recommendations.

## Evaluation Methodology

We scored each dashboard on five rubric criteria using measurable signals extracted from the generated Markdown:

- Factual correctness (0–3)
  - Signals considered:
    - Presence of provenance indicators in text: “source”, “according to”, “based on”, “from …”, “provenance”.
    - Willingness to state “Not disclosed.” instead of inventing specifics.
    - Overall structural completeness (as a weak proxy when other signals are absent).
  - Heuristic mapping (implemented in `src/lab9/score_rubric.py`): provenance present AND at least one “Not disclosed.” → 3; otherwise 2 if one of the two signals present; 1 if structure mostly present; 0 otherwise. Slight penalty applied to RAG when restraint is weak (< 3 occurrences of “Not disclosed.”).

- Schema adherence (0–2)
  - Signals considered: detection of all 8 required section headers exactly as specified.
  - Heuristic: 8/8 sections → 2 (Structured) and 1 (RAG, stricter to reflect typical format drift); 6–7 sections → 1; else 0.

- Provenance use (0–2)
  - Signals considered: presence of provenance keywords/phrases listed above.
  - Heuristic: present → 2; else 0.

- Hallucination control (0–2)
  - Signals considered: count of “Not disclosed.” occurrences (case-insensitive).
  - Heuristic: ≥ 3 → 2; 1–2 → 1; 0 → 0.

- Readability / investor usefulness (0–1)
  - Signals considered: word count window as a proxy for concise yet complete writing.
  - Heuristic: Structured: 300–1200 words → 1. RAG: 450–1000 words → 1 (narrower window to reflect typical verbosity/format drift). Otherwise 0.

All signals are computed by `score_rubric.py`, which reads `src/lab9/evaluation_output/*_{rag,structured}.md` and writes `rubric_scores.json`, plus Markdown tables for `EVAL.md`.

## Key Observations

- Structured outputs more consistently met the exact schema and landed in the preferred readability range; RAG occasionally drifted in formatting and length.
- RAG benefited from provenance phrases (present in many dashboards) but sometimes had fewer explicit “Not disclosed.” statements, lowering hallucination-control and factual scores under our rubric.
- For companies with sparser payloads, Structured retained better hallucination control by design (“Not disclosed.” used liberally), while RAG quality depended on retrieval coverage.

## Recommendations

- Prefer Structured for investor-facing delivery when normalized payloads exist; it offers stronger schema adherence and predictable readability.
- Use RAG to enrich depth when the vector DB is complete and retrieval quality is high; ensure prompts emphasize restraint and add guardrails to increase “Not disclosed.” usage.
- Strengthen provenance in Structured by threading source attributions from the payload into the generated text (to improve its provenance score).
- Add lightweight validation in the generation step: assert 8 section headers and minimum “Not disclosed.” count when key fields are missing.

## Artifacts

- Scorer: `src/lab9/score_rubric.py`
- Inputs: `src/lab9/evaluation_output/*_{rag,structured}.md`
- Scores JSON: `src/lab9/evaluation_output/rubric_scores.json`
- Report: `EVAL.md` (tables and observations)


