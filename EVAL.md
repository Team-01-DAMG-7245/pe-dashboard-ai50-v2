# Lab 9 — Evaluation & Comparison

Goal: compare RAG vs Structured for at least 5 companies.

## Rubric (10 points)

| Criterion | Score Range | Description |
|-----------|-------------|-------------|
| Factual correctness | 0–3 | Accuracy of information presented |
| Schema adherence | 0–2 | Presence of all 8 required sections |
| Provenance use | 0–2 | Proper attribution and source referencing |
| Hallucination control | 0–2 | Uses “Not disclosed.” instead of guessing |
| Readability / investor usefulness | 0–1 | Clarity and actionability |

## Scores (Adjusted Heuristics)

### Company: Anthropic

| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |
|--------|----------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 1 | 2 | 1 | 1 | 7/10 |
| Structured | 2 | 2 | 0 | 2 | 1 | 7/10 |

Observations:
- RAG: Good provenance and completeness; fewer "Not disclosed." (≈2) and minor format drift reduce hallucination and schema.
- Structured: Strong schema and restraint; lacks explicit provenance phrases in this sample, but concise and readable.

---

### Company: Abridge

| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |
|--------|----------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 3 | 1 | 2 | 2 | 0 | 8/10 |
| Structured | 3 | 2 | 2 | 1 | 1 | 9/10 |

Observations:
- RAG: Strong provenance and restraint (≥3 "Not disclosed."); slightly under target length for RAG window → readability 0; minor format drift.
- Structured: Balanced length and structure with clear provenance; a bit fewer "Not disclosed." than RAG.

---

### Company: Anysphere

| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |
|--------|----------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 3 | 1 | 2 | 2 | 0 | 8/10 |
| Structured | 3 | 2 | 2 | 1 | 0 | 8/10 |

Observations:
- RAG: High restraint (many "Not disclosed."); very short (≈130 words) hurts readability; slight schema penalty under RAG heuristic.
- Structured: Better schema adherence; moderate restraint; still short (≈267 words) so readability 0.

---

### Company: Baseten

| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |
|--------|----------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 3 | 1 | 2 | 2 | 0 | 8/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

Observations:
- RAG: Solid provenance and restraint; brief (≈275 words) so readability 0; minor schema drift.
- Structured: Best overall balance—exact schema, strong restraint, and readable length.

---

### Company: Clay

| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |
|--------|----------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 1 | 2 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

Observations:
- RAG: Provenance present; only one "Not disclosed." lowers hallucination score; otherwise clear and readable.
- Structured: Consistently strong across all criteria with exact schema and good restraint.



