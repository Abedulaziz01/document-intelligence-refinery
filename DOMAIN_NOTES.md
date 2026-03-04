# DOMAIN_NOTES.md

## PHASE 3 — DOMAIN ONBOARDING (MANDATORY)

**Week 3 — The Document Intelligence Refinery**

---

# 1. Domain Understanding — Document Science Primer

Enterprise documents are not text files. They are **layout-encoded visual artifacts**.

A PDF can be:

- **Native Digital** → Contains a character stream (text layer)
- **Scanned Image** → Pure image, no characters
- **Mixed** → Text + embedded scanned sections
- **Form-based** → Structured fillable layout

The core mistake in document intelligence systems is assuming all PDFs behave the same.

---

# 2. Extraction Strategy Decision Tree

```mermaid
flowchart TD
    A[Document Ingested] --> B[Triage Agent: Build DocumentProfile]

    B --> C{Origin Type?}

    C -->|Native Digital| D{Layout Complexity?}
    C -->|Scanned Image| G[Strategy C: Vision Extractor]
    C -->|Mixed| E[Strategy B: Layout-Aware]
    C -->|Form Fillable| F[Strategy A with Form Parsing]

    D -->|Single Column| H[Strategy A: Fast Text]
    D -->|Multi-Column| E
    D -->|Table Heavy| E
    D -->|Figure Heavy| E

    H --> I{Confidence Score >= Threshold?}
    I -->|Yes| J[Pass to Chunking Engine]
    I -->|No| E

    E --> K{Layout Confidence >= Threshold?}
    K -->|Yes| J
    K -->|No| G

    G --> L{Budget Cap Exceeded?}
    L -->|No| J
    L -->|Yes| M[Fail Gracefully + Log]


3. Strategy Overview
    | Strategy             | Tooling                    | Cost   | Trigger Condition          | Strength            | Weakness                     |
| -------------------- | -------------------------- | ------ | -------------------------- | ------------------- | ---------------------------- |
| **A — Fast Text**    | pdfplumber / PyMuPDF       | Low    | Native + single column     | Very fast, cheap    | Breaks tables, fails scanned |
| **B — Layout Aware** | MinerU / Docling           | Medium | Multi-column / table-heavy | Preserves structure | Slower                       |
| **C — Vision (VLM)** | GPT-4o-mini / Gemini Flash | High   | Scanned / low confidence   | Best fidelity       | Expensive                    |


4. Failure Modes per Document Class
Class A — Annual Financial Report (Native, Multi-column)

Example: Commercial Bank of Ethiopia Annual Report


| Failure             | Why It Happens                                            | Consequence                                  |
| ------------------- | --------------------------------------------------------- | -------------------------------------------- |
| Column merging      | Strategy A reads left-to-right ignoring column boundaries | Sentences become scrambled                   |
| Table flattening    | No layout model                                           | Financial statements become unusable strings |
| Footnote detachment | Reading order loss                                        | Incorrect numerical interpretation           |
Why Strategy A Fails Here

Financial reports are multi-column.

pdfplumber extracts characters but does not reconstruct logical reading order.

Tables become linearized text.

Cross references break.

Conclusion: Strategy B required.
lass B — Scanned Government Audit (Image-Based)

Example: Development Bank of Ethiopia Auditor Report

Observed Failure Modes
| Failure                  | Why It Happens     | Consequence              |
| ------------------------ | ------------------ | ------------------------ |
| Zero character stream    | No text layer      | Strategy A returns empty |
| OCR hallucinated numbers | Poor image quality | Financial misstatements  |
| Skewed page text drift   | Scan misalignment  | Broken sentence order    |


Why Strategy A Fails on Scanned

Character count ≈ 0

Image area > 90%

No font metadata

Fast extraction produces empty output.

Escalation to Strategy C is mandatory.

Class C — Technical Assessment Report (Mixed Layout)

Example: Financial Transparency Assessment

Observed Failure Modes

| Failure                             | Why It Happens          | Consequence              |
| ----------------------------------- | ----------------------- | ------------------------ |
| Section hierarchy lost              | No heading detection    | PageIndex becomes flat   |
| Embedded tables partially extracted | Simple layout parsing   | Missing rows             |
| Cross-reference unresolved          | No relationship mapping | Hallucinated connections |


Class D — Structured Data Fiscal Report (Table Heavy)

Example: Ethiopia Import Tax Expenditure Report

| Failure                | Why It Happens        | Consequence        |
| ---------------------- | --------------------- | ------------------ |
| Table splitting        | Token-based chunking  | LLM hallucination  |
| Numeric precision loss | OCR misread decimals  | Financial errors   |
| Header-row separation  | Improper segmentation | Misaligned columns |


5. Why Table Splitting Causes Hallucination

When a table is chunked by token count:

Header row is stored in Chunk 1

Data rows appear in Chunk 2

LLM receives data without schema context

Example:

Chunk 1:
Year | Revenue | Expenses

Chunk 2:

2022 | 4.2B | 3.1B
If retrieved independently, model guesses column meanings.

This leads to:

Fabricated units

Wrong financial category mapping

Incorrect aggregations

Rule: A table cell must never be split from its header row.


6. Why Bounding Box (bbox) is Required for Audit

Without spatial coordinates:

You cannot prove where a fact came from.

Page number alone is insufficient.

In multi-column layouts, the same number may appear multiple times.

Bounding box provides:

{
  page: 47,
  bbox: [x0, y0, x1, y1],
  content_hash: "abc123"
}

7. VLM Cost Tradeoff Explanation

Vision Language Models (VLMs):

Examples:

GPT-4o-mini

Gemini Flash

Pixtral

Advantages

Understand layout visually

Handle handwriting

Robust table extraction

No reliance on text layer

Disadvantages

High token cost (image + output tokens)

Latency

API dependency

Cost Comparison (Estimated)
| Strategy | Avg Cost per 100-page Doc   | Latency   | Reliability    |
| -------- | --------------------------- | --------- | -------------- |
| A        | ~$0                         | <10 sec   | Low on complex |
| B        | ~$0 (local models)          | 20–40 sec | High           |
| C        | $3–$12 (depending on model) | 1–3 min   | Very High      |
```
