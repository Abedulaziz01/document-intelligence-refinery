# The Document Intelligence Refinery

### TRP1 Challenge Week 3 — FDE Program

Engineering Agentic Pipelines for Unstructured Document Extraction at Enterprise Scale

---

# 🚀 Overview

The **Document Intelligence Refinery** is a production-grade, multi-stage, classification-aware document processing system designed to transform heterogeneous enterprise documents into:

- Structured JSON schemas
- Spatially indexed Logical Document Units (LDUs)
- RAG-ready vector embeddings
- SQL-queryable fact tables
- Fully auditable provenance chains

This system is built following Forward Deployed Engineering (FDE) principles:

- Confidence-gated extraction
- Cost-aware escalation
- Structure-preserving chunking
- Spatial provenance tracking
- Graceful degradation on unseen layouts

---

# 🧠 The Problem

Enterprise knowledge is locked inside:

- Native PDFs (multi-column financial reports)
- Scanned legal documents
- Table-heavy fiscal reports
- Technical assessments
- Mixed-layout documents

Traditional OCR:

- Flattens structure
- Breaks tables
- Loses section hierarchy

Naive RAG pipelines:

- Split tables across chunks
- Hallucinate missing headers
- Cannot provide source verification

The Refinery solves:

1. **Structure Collapse**
2. **Context Poverty**
3. **Provenance Blindness**

---

# 🏗 Architecture

## 5-Stage Agentic Pipeline

```mermaid
flowchart LR
    A[Document Input] --> B[Triage Agent]
    B --> C[Extraction Router]
    C --> D1[Strategy A Fast Text]
    C --> D2[Strategy B Layout Aware]
    C --> D3[Strategy C Vision Model]
    D1 --> E[ExtractedDocument]
    D2 --> E
    D3 --> E
    E --> F[Semantic Chunking Engine]
    F --> G[PageIndex Builder]
    F --> H[Vector Store + FactTable]
    G --> I[Query Agent]
    H --> I
    I --> J[Answer + ProvenanceChain]



📂 Project Structure
    .
├── src/
│   ├── models/
│   │   ├── document_profile.py
│   │   ├── extracted_document.py
│   │   ├── ldu.py
│   │   ├── page_index.py
│   │   └── provenance.py
│   │
│   ├── agents/
│   │   ├── triage.py
│   │   ├── extractor.py
│   │   ├── chunker.py
│   │   ├── indexer.py
│   │   └── query_agent.py
│   │
│   ├── strategies/
│   │   ├── fast_text.py
│   │   ├── layout_extractor.py
│   │   └── vision_extractor.py
│
├── rubric/
│   └── extraction_rules.yaml
│
├── .refinery/
│   ├── profiles/
│   ├── extraction_ledger.jsonl
│   └── pageindex/
│
├── data/
├── tests/
├── pyproject.toml
└── README.md



🧩 Core Concepts
1️⃣ Triage Agent

Generates a DocumentProfile:

-origin_type (digital | scanned | mixed | form)

-layout_complexity

-language

-domain_hint

-estimated_extraction_cost

This governs strategy selection.

2️⃣ Multi-Strategy Extraction
Strategy A — Fast Text (Low Cost)

Tool: pdfplumber / PyMuPDF
Used when:

-Native digital

-Single column

-High character density
```

Strategy B — Layout-Aware (Medium Cost)

Tool: MinerU / Docling
Used when:

-Multi-column

-Table-heavy

-Mixed origin

Preserves:

-Bounding boxes

-Tables as structured JSON

-Reading order

## Strategy C — Vision-Augmented (High Cost)

**Tools:** GPT-4o-mini / Gemini Flash

**Used when:**

- Scanned documents
- Low extraction confidence
- Handwriting detected

**Includes:**

- Budget guard
- Cost logging
- Escalation logic

---

## 3️⃣ Escalation Guard

Extraction never silently fails.

If `confidence < threshold`:

Strategy A → Strategy B → Strategy C

**Confidence is computed from:**

- Character density
- Image-to-page ratio
- Table completeness
- Reading order consistency

---

## 4️⃣ Semantic Chunking Engine

Converts extracted structure into **Logical Document Units (LDUs).**

### Enforced Rules

- Table cells are never separated from their header row
- Figure captions are stored as metadata
- Lists remain intact
- Section headers propagate downward
- Cross-references are resolved

### Each LDU Includes:

- `content`
- `chunk_type`
- `page_refs`
- `bounding_box`
- `parent_section`
- `content_hash`

---

## 5️⃣ PageIndex Builder

Builds a hierarchical navigation tree containing:

- `title`
- `page_start / page_end`
- `child_sections`
- `key_entities`
- `summary`
- `data_types_present`

**Enables:**  
Section-first navigation before vector search.

---

## 6️⃣ Provenance Layer

Every answer returns a `ProvenanceChain`:

- `document_name`
- `page_number`
- `bounding_box`
- `content_hash`

This allows **pixel-level audit verification.**

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone <your-repo-url>
cd document-intelligence-refinery

2️⃣ Create Environment

python -m venv .venv
source .venv/bin/activate   # mac/linux
.venv\Scripts\activate      # windows

3️⃣ Install Dependencies
3️⃣ Install Dependenciespip install -e .

or pip install -r requirements.txt
▶️ Running the Pipeline
Step 1: Drop Document

Place your PDF into:

data/
Step 2: Run Triage

python -m src.agents.triage data/sample.pdf

Output:
.refinery/profiles/sample.json

Step 3: Run Extraction

python -m src.agents.extractor data/sample.pdf

Logs:
.refinery/extraction_ledger.jsonl
```
