<div align="center">

# 🛡️ SentinelRAG

### Hybrid Symbolic-Neural Compliance Screening Engine

**Built for the officers who protect America's borders and financial systems.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](#quick-start)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#disclaimer)
[![OFAC/SDN](https://img.shields.io/badge/Data-OFAC%20SDN%20List-red)](#overview)
[![Local-First](https://img.shields.io/badge/Architecture-Local--First-orange)](#why-sentinelrag)

---

*A RAG-based sanctions screening system that is high-precision, sub-millisecond fast, cost-efficient, and secure enough for government agencies to actually trust.*

</div>

---

## 🇺🇸 Why SentinelRAG?

Government agencies handling OFAC/SDN sanctions screening face a critical dilemma: legacy systems rely on brittle keyword matching that misses name variations, while modern AI solutions demand sending sensitive data to external servers — creating security vulnerabilities no compliance officer can sign off on.

**SentinelRAG was built to solve this.**

We designed a system where:

- **🔒 No data ever leaves your infrastructure.** Zero external API calls. Zero cloud dependency. Every computation happens on-premise, behind your firewall.
- **📋 Every decision is fully auditable.** Human-readable justifications and confidence scores accompany every match — essential for regulatory and legal accountability.
- **⚡ Speed doesn't compromise security.** Exact matches resolve in ~0.1 ms. Complex screening averages ~84 ms. That's 900x faster than standard neural RAG.
- **💰 Taxpayer-efficient.** Smart short-circuiting ensures expensive neural reasoning only runs when absolutely necessary — slashing compute costs without sacrificing accuracy.

---

## 📊 Performance Results

<div align="center">

| Metric | Score |
|:---|:---:|
| **Accuracy** | 96% |
| **Precision** | 97% |
| **Recall** | 95% |
| **Fast-Path Latency** (graph hit) | ~0.1 ms |
| **Full-Pipeline Latency** (worst case) | ~84 ms |
| **Speed vs Standard Neural RAG** | 900x faster |

</div>

---

## 🏗️ Architecture Overview

SentinelRAG uses a **5-stage adaptive pipeline** that short-circuits at the earliest confident stage — most real-world queries never reach the expensive final stages.

```
                        ┌─────────────────┐
                        │   Entity Query   │
                        └────────┬────────┘
                                 │
                    ┌────────────▼────────────┐
          Stage 1   │   Knowledge Graph       │  ~0.04 ms
                    │   (Exact alias/ID hit)  │  ← Fast Path
                    └────────────┬────────────┘
                                 │ miss
                    ┌────────────▼────────────┐
          Stage 2   │   Hybrid Retrieval      │  ~30 ms
                    │   BM25 + Vector Search  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
          Stage 3   │   Quick Fuzzy Pre-Check │  ~1 ms
                    │   (Score ≥ 92 → done)   │  ← Short-Circuit
                    └────────────┬────────────┘
                                 │ ambiguous
                    ┌────────────▼────────────┐
          Stage 4   │   Cross-Encoder Rerank  │  ~60 ms
                    │   (Neural reasoning)    │  ← Only when needed
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
          Stage 5   │   Deterministic Decision│  ~1 ms
                    │   Confidence + Reason   │
                    └─────────────────────────┘
```

### Three Complementary Indexes

| Index | Technology | Purpose |
|:---|:---|:---|
| **Knowledge Graph** | `networkx` | O(1) exact alias and identifier lookups |
| **BM25 Lexical** | `rank-bm25` | Token overlap matching for lexical variations |
| **Vector Search** | `Chroma` + MiniLM | Semantic similarity for transliterated names and aliases |

### Graceful Degradation

When model downloads are blocked by network/proxy policy, the engine degrades gracefully:

- Vector retrieval falls back to BM25-only mode
- Cross-encoder reranking can be skipped entirely
- Screening still returns deterministic `MATCH` / `NO_MATCH` decisions

---

## 🔐 Security & Privacy

SentinelRAG was designed with a **security-first** philosophy — because the biggest barrier to AI adoption in government isn't technology, it's trust.

| Principle | Implementation |
|:---|:---|
| **Local-First Execution** | All models run locally. No data is sent to external APIs, cloud services, or third-party endpoints. |
| **Zero Data Leakage** | Sensitive query data — names, entities, screening patterns — never leaves the secure infrastructure. |
| **Full Auditability** | Every decision includes a confidence score and human-readable reason. No black boxes. |
| **PII Redaction** | Optional Microsoft Presidio integration redacts sensitive data in audit logs and exports. |
| **Minimal Attack Surface** | Smart short-circuiting means fewer model invocations = fewer potential vectors. |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- ~2 GB disk space (for models and SDN data)

### 1) Clone and Install

```bash
git clone https://github.com/VigneshwariJayaprakash/Sentinel-RAG.git
cd Sentinel-RAG
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Prepare SDN Data

If `data/sdn.csv` is missing, download it directly from the U.S. Treasury:

```bash
mkdir -p data
curl -L "https://www.treasury.gov/ofac/downloads/sdn.csv" -o data/sdn.csv
```

### 3) Build Indexes (one-time or after SDN refresh)

```bash
python ingesting.py
```

This creates:
- `vector_db/` — Chroma vector store
- `bm25_corpus.json` — BM25 lexical index
- `knowledge_graph.pkl` — NetworkX graph index

### 4) Smoke Test

```bash
python test_engine.py
```

---

## ▶️ Run the System

### Option A: Streamlit UI (Recommended)

```bash
streamlit run app_ui.py
```

Open `http://localhost:8501` in your browser.

> If file-watcher noise appears: `streamlit run app_ui.py --server.fileWatcherType none`

### Option B: FastAPI

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Single entity screening:**
```bash
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{"query":"Banco Nacional de Cuba"}'
```

**Batch screening:**
```bash
curl -X POST "http://localhost:8000/batch_screen" \
  -H "Content-Type: application/json" \
  -d '{"queries":["BNC","Random Company"]}'
```

**Example response:**
```json
{
  "decision": "MATCH",
  "entity_number": "306",
  "confidence": 1.0,
  "reason": "Graph alias/entity lookup match.",
  "latency": {
    "graph_lookup_ms": 0.04,
    "total_ms": 0.12
  }
}
```

### Option C: CLI Retriever

```bash
python retriever.py
```

---

## 🔄 Keep SDN Data Updated

```bash
python update_sdn.py
```

**What it does:**
- Downloads the latest SDN CSV from OFAC
- Compares MD5 hash with the existing file
- Backs up the previous version into `data/backups/` with a timestamp
- Rebuilds all indexes only when content has changed
- Fails safely — if download fails but a local copy exists, it skips the rebuild

**Optional proxy bypass:**
```bash
SDN_BYPASS_PROXY=1 python update_sdn.py
```

**Automate with cron (daily at 2 AM):**
```bash
0 2 * * * cd /path/to/SentinelRag && /path/to/.venv/bin/python update_sdn.py >> logs/sdn_update.log 2>&1
```

<details>
<summary><strong>GitHub Actions — Automated Daily Update</strong></summary>

Create `.github/workflows/update_sdn.yml`:

```yaml
name: Update SDN List

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python update_sdn.py
      - name: Commit if changed
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add bm25_corpus.json knowledge_graph.pkl
          git diff --staged --quiet || git commit -m "Auto-update SDN $(date +%Y-%m-%d)" && git push
```

</details>

---

## 📈 Evaluation & Benchmarking

```bash
python evaluate.py               # Accuracy evaluation against test suite
python benchmark.py              # Measure average latency
python generate_auto_tests.py    # Regenerate test dataset from current SDN data
```

**Sample evaluation output:**
```
=== Evaluation Report ===
Total Samples:    80
Accuracy:         0.96
Precision:        0.97
Recall:           0.95
False Positives:  1
False Negatives:  2
```

**Sample benchmark output:**
```
Total queries: 100
Total time:    8.43s
Average latency: 0.0843s
```

The auto test suite (`evaluation_data_auto.json`) samples 20 random SDN entities, creates three query variants per entity (exact, lowercase, one-character truncation), and adds 20 random noise strings as negatives — 80 test cases total.

> **Note:** `evaluate.py` currently uses `retriever.py` directly rather than `engine.py`, so results do not reflect the adaptive short-circuit logic. Scores are slightly conservative relative to real-world performance.

---

## 🔏 PII Handling (Presidio)

SentinelRAG includes optional PII redaction via Microsoft Presidio.

**Integration points:**
- API audit logging redacts stored queries before writing to `audit_log.jsonl`
- Streamlit bulk mode includes an optional checkbox to redact query text in displayed/exported CSV output

**Enable with environment variables:**
```bash
export ENABLE_PII_REDACTION=true
export PII_ENTITIES=PHONE_NUMBER,EMAIL_ADDRESS,PERSON
```

By default, redaction is disabled. The lightweight mode avoids downloading large NLP models, focusing on regex-based entity types (phone, email).

---

## ⚙️ Configuration

Key constants you can tune:

| Constant | Default | File | Effect |
|:---|:---:|:---|:---|
| `FUZZY_MATCH_THRESHOLD` | `85` | `engine.py`, `retriever.py` | Minimum fuzzy score (0–100) to count as a match. Lower = more matches, higher false-positive risk. |
| Quick pre-check threshold | `92` | `engine.py` | Score above which cross-encoder is skipped entirely. Raise to force more reranking; lower for speed. |
| `k` in `hybrid_retrieve()` | `5` | `engine.py` | Candidates fetched from each retrieval method. Higher = better recall, slower retrieval. |

---

## 📁 Project Structure

```
SentinelRAG/
├── api.py                      # FastAPI endpoints
├── app_ui.py                   # Streamlit UI
├── benchmark.py                # Latency benchmarking
├── bm25_corpus.json            # BM25 lexical index
├── check_data.py               # Data validation utilities
├── engine.py                   # Core screening engine (5-stage pipeline)
├── evaluate.py                 # Accuracy evaluation
├── evaluation_data.json        # Manual test cases
├── evaluation_data_auto.json   # Auto-generated test cases
├── generate_auto_tests.py      # Test data generator
├── generator.py                # Response generation
├── ingesting.py                # Index builder (graph + BM25 + vector)
├── knowledge_graph.pkl         # NetworkX graph index
├── requirements.txt            # Python dependencies
├── retriever.py                # Retrieval logic
├── test_engine.py              # Smoke tests
├── update_sdn.py               # SDN data updater
├── data/
│   ├── sdn.csv                 # OFAC SDN list
│   └── backups/                # Timestamped SDN backups
└── vector_db/                  # Chroma vector store
```

---

## 🗺️ Roadmap

- [ ] Align `evaluate.py` with full `engine.py` adaptive pipeline
- [ ] Docker packaging for single-command deployment
- [ ] Async batch screening path for API
- [ ] Separate fuzzy thresholds for person names vs company names
- [ ] Include aliases in cross-encoder scoring pairs
- [ ] Extend support to additional sanctions lists (EU, UN, HMT)

---

## 👥 Team

Built by **Team Kentucky** as a capstone project for FSE 570.

- [Vigneshwari Jayaprakash](https://www.linkedin.com/in/vigneshwari31/)
- [Nishu Kumari Singh](https://www.linkedin.com/in/)
- [Aditi Girish Thakre](https://www.linkedin.com/in/)
- [Nikita Kumari](https://www.linkedin.com/in/)
- [Aishwaryalaxmi Chavan](https://www.linkedin.com/in/)

**Faculty Advisor:** Professor Joshua Loughman

---

## ⚠️ Disclaimer

SentinelRAG is a research/development tool and not legal advice or a certified compliance platform. Always involve qualified legal and compliance teams for production regulatory decisions.

---

<div align="center">

**If this project resonates with you, give it a ⭐ on GitHub!**

</div>
