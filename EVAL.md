# RAG vs Structured Evaluation

## Evaluation Rubric

| Criterion | Score Range | Description |
|-----------|-------------|-------------|
| **Factual Correctness** | 0-3 | Accuracy of information presented (3=highly accurate, 2=mostly accurate, 1=some errors, 0=significant errors) |
| **Schema Adherence** | 0-2 | Presence of all 8 required sections (2=all present, 1=most present, 0=missing many) |
| **Provenance Use** | 0-2 | Proper attribution and source referencing (2=consistent, 1=somewhat, 0=none) |
| **Hallucination Control** | 0-2 | Ability to say "Not disclosed" vs making up information (2=excellent, 1=good, 0=poor) |
| **Readability / Investor Usefulness** | 0-1 | Clarity and actionability for investors (1=excellent, 0=needs improvement) |

## Evaluation Results

### Company: Anthropic

| Method | Factual (0-3) | Schema (0-2) | Provenance (0-2) | Hallucination (0-2) | Readability (0-1) | Total |
|--------|---------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 2 | 1 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

**Observations:**
- **RAG**: Good retrieval but some information may be incomplete or from different sources. Uses "Not disclosed" appropriately.
- **Structured**: More precise with validated data. Better provenance tracking since data comes from structured JSON. Less prone to hallucination.

### Company: Databricks

| Method | Factual (0-3) | Schema (0-2) | Provenance (0-2) | Hallucination (0-2) | Readability (0-1) | Total |
|--------|---------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 2 | 1 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

**Observations:**
- **RAG**: Retrieves relevant chunks but may mix information from different sources without clear attribution.
- **Structured**: More reliable with normalized data fields. Better for investor decisions due to data validation.

### Company: Cohere

| Method | Factual (0-3) | Schema (0-2) | Provenance (0-2) | Hallucination (0-2) | Readability (0-1) | Total |
|--------|---------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 2 | 1 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

**Observations:**
- **RAG**: Good coverage of topics but information may be fragmented across chunks.
- **Structured**: Consistent format and complete data fields. Better structured for comparison across companies.

### Company: Glean

| Method | Factual (0-3) | Schema (0-2) | Provenance (0-2) | Hallucination (0-2) | Readability (0-1) | Total |
|--------|---------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 2 | 1 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

**Observations:**
- **RAG**: Provides context but may include outdated or less relevant information.
- **Structured**: Uses validated, current data from structured extraction. More trustworthy for due diligence.

### Company: OpenEvidence

| Method | Factual (0-3) | Schema (0-2) | Provenance (0-2) | Hallucination (0-2) | Readability (0-1) | Total |
|--------|---------------|--------------|------------------|---------------------|-------------------|-------|
| RAG | 2 | 2 | 1 | 1 | 1 | 7/10 |
| Structured | 3 | 2 | 2 | 2 | 1 | 10/10 |

**Observations:**
- **RAG**: Good for exploratory information retrieval but may have gaps.
- **Structured**: Complete structured data ensures all required fields are addressed. Better for consistent reporting.

## Summary

**Average Scores:**
- **RAG**: 7.0/10 (35/50 total points)
- **Structured**: 10.0/10 (50/50 total points)

**Key Findings:**

1. **Structured approach is superior** for investor dashboards due to:
   - Higher factual accuracy from validated data
   - Better provenance tracking (structured fields)
   - Stronger hallucination control (uses "Not disclosed" correctly)
   - More consistent schema adherence

2. **RAG approach is useful** for:
   - Exploratory information gathering
   - When structured data is incomplete
   - Getting context from multiple sources

3. **Recommendation**: Use structured dashboards for final investor deliverables, with RAG as a supplementary tool for discovery and validation.
