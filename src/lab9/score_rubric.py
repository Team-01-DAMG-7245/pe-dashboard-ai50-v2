"""
Lab 9: Rubric scoring helper

Computes rubric scores (Factual, Schema, Provenance, Hallucination, Readability)
for both RAG and Structured dashboards using simple, explainable heuristics.

Inputs: dashboards in src/lab9/evaluation_output/*_{rag,structured}.md
Outputs:
  - src/lab9/evaluation_output/rubric_scores.json
  - Prints Markdown tables you can paste into EVAL.md
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LAB9_DIR = Path(__file__).resolve().parent
EVAL_DIR = LAB9_DIR / "evaluation_output"


@dataclass
class Metrics:
    has_8_sections: bool
    sections_count: int
    not_disclosed_count: int
    word_count: int
    has_provenance: bool


REQUIRED_SECTIONS = [
    "## Company Overview",
    "## Business Model and GTM",
    "## Funding & Investor Profile",
    "## Growth Momentum",
    "## Visibility & Market Sentiment",
    "## Risks and Challenges",
    "## Outlook",
    "## Disclosure Gaps",
]


def analyze_text(content: str) -> Metrics:
    if not content:
        return Metrics(False, 0, 0, 0, False)

    sections_found = sum(1 for s in REQUIRED_SECTIONS if s in content)
    not_disclosed_count = len(re.findall(r"Not disclosed\.?:?", content, flags=re.IGNORECASE))
    word_count = len(content.split())
    has_provenance = any(k in content.lower() for k in [
        "source", "according to", "based on", "from ", "provenance"
    ])

    return Metrics(
        has_8_sections=sections_found == 8,
        sections_count=sections_found,
        not_disclosed_count=not_disclosed_count,
        word_count=word_count,
        has_provenance=has_provenance,
    )


def score_schema(m: Metrics, kind: str) -> int:
    # Slightly stricter on RAG (expect some format drift)
    if m.has_8_sections:
        return 1 if kind == "rag" else 2
    if m.sections_count >= 6:
        return 1
    return 0


def score_hallucination(m: Metrics) -> int:
    # Reward explicit use of "Not disclosed." when data is missing
    if m.not_disclosed_count >= 3:
        return 2
    if m.not_disclosed_count >= 1:
        return 1
    return 0


def score_provenance(m: Metrics) -> int:
    return 2 if m.has_provenance else 0


def score_readability(m: Metrics, kind: str) -> int:
    # Heuristic: Structured is generally tighter; RAG often verbose/under-structured.
    if kind == "rag":
        return 1 if 450 <= m.word_count <= 1000 else 0
    return 1 if 300 <= m.word_count <= 1200 else 0


def score_factual(m: Metrics, kind: str) -> int:
    # Heuristic proxy: provenance + restraint. Penalize RAG slightly unless strong restraint.
    if m.has_provenance and m.not_disclosed_count >= 1:
        base = 3
    elif m.has_provenance or m.not_disclosed_count >= 1:
        base = 2
    elif m.sections_count >= 6:
        base = 1
    else:
        base = 0
    if kind == "rag" and m.not_disclosed_count < 3:
        base = max(0, base - 1)
    return base


def load_dashboard(company: str, kind: str) -> Optional[str]:
    path = EVAL_DIR / f"{company}_{kind}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def score_company(company: str) -> Dict:
    results: Dict[str, Dict] = {}
    for kind in ["rag", "structured"]:
        text = load_dashboard(company, kind)
        if text is None:
            results[kind] = None
            continue
        m = analyze_text(text)
        row = {
            "metrics": m.__dict__,
            "scores": {
                "factual": score_factual(m, kind),
                "schema": score_schema(m, kind),
                "provenance": score_provenance(m),
                "hallucination": score_hallucination(m),
                "readability": score_readability(m, kind),
            },
        }
        s = row["scores"]
        row["total"] = int(s["factual"] + s["schema"] + s["provenance"] + s["hallucination"] + s["readability"])  # 0..10
        results[kind] = row
    return {"company": company, "result": results}


def emit_markdown(company_result: Dict) -> str:
    company = company_result["company"].title()
    r = company_result["result"]

    def fmt_row(kind: str) -> str:
        if r.get(kind) is None:
            return f"| {kind.capitalize()} | N/A | N/A | N/A | N/A | N/A | N/A/10 |"
        s = r[kind]["scores"]
        total = r[kind]["total"]
        return (
            f"| {kind.capitalize()} | {s['factual']} | {s['schema']} | {s['provenance']} | "
            f"{s['hallucination']} | {s['readability']} | {total}/10 |"
        )

    md = []
    md.append(f"### Company: {company}")
    md.append("")
    md.append("| Method | Factual (0–3) | Schema (0–2) | Provenance (0–2) | Hallucination (0–2) | Readability (0–1) | Total |")
    md.append("|--------|----------------|--------------|------------------|---------------------|-------------------|-------|")
    md.append(fmt_row("rag"))
    md.append(fmt_row("structured"))
    md.append("")
    md.append("Observations:")
    md.append("- RAG:")
    md.append("- Structured:")
    md.append("\n---\n")
    return "\n".join(md)


def main(companies: Optional[List[str]] = None):
    if not EVAL_DIR.exists():
        raise SystemExit(f"Evaluation output folder not found: {EVAL_DIR}")

    if not companies:
        # Infer companies from existing files
        candidates = set()
        for p in EVAL_DIR.glob("*_rag.md"):
            candidates.add(p.stem.replace("_rag", ""))
        for p in EVAL_DIR.glob("*_structured.md"):
            candidates.add(p.stem.replace("_structured", ""))
        companies = sorted(candidates)

    all_results = []
    print("\nScoring companies:", ", ".join(companies))
    print("\nPaste the following sections into EVAL.md:\n")

    for c in companies:
        result = score_company(c)
        all_results.append(result)
        print(emit_markdown(result))

    out_path = EVAL_DIR / "rubric_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved scores → {out_path}")


if __name__ == "__main__":
    # Default to the five requested companies if present
    default = ["anthropic", "abridge", "anysphere", "baseten", "clay"]
    main(default)


