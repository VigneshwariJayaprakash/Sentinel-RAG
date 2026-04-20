# SentinelRAG File Guide

This guide explains what each key file/folder in the repository does, how it is used, and where it fits in the full workflow.

## How to Read This Guide

- **Core runtime files**: required to run UI/API screening.
- **Data/index files**: generated artifacts used by retrieval.
- **Utility/evaluation files**: testing, benchmarking, and dataset maintenance.
- **Operational/docs files**: setup and project documentation.

---

## Repository Map

### `api.py`

- **Purpose**: FastAPI service exposing screening endpoints.
- **Main endpoints**:
  - `POST /screen` for single query
  - `POST /batch_screen` for list of queries
- **Important behavior**:
  - Uses `SentinelRAGEngine` from `engine.py`.
  - Writes audit logs to `audit_log.jsonl`.
  - Applies optional PII redaction before logging via `privacy.py`.

### `app_ui.py`

- **Purpose**: Streamlit frontend for interactive screening.
- **UI sections**:
  - Single entity screening (text input + result metrics)
  - Bulk CSV screening (expects `query` column)
- **Important behavior**:
  - Caches engine initialization with `@st.cache_resource`.
  - Supports optional PII redaction in bulk output/download.

### `engine.py`

- **Purpose**: Main orchestration engine for query screening.
- **Pipeline inside `screen(query)`**:
  1. Knowledge graph lookup (exact alias/ID/entity)
  2. Hybrid retrieval (vector + BM25)
  3. Quick fuzzy pre-check
  4. Optional cross-encoder rerank
  5. Deterministic decision
- **Special runtime behavior**:
  - Graceful fallback if embedding or cross-encoder model download is blocked.
  - Returns latency breakdown with decision metadata.

### `privacy.py`

- **Purpose**: Optional PII detection/anonymization wrapper using Presidio.
- **Main functions**:
  - `detect_pii(text)`
  - `anonymize_text(text)`
- **Config flags**:
  - `ENABLE_PII_REDACTION=true|false`
  - `PII_ENTITIES=PHONE_NUMBER,EMAIL_ADDRESS,...`
- **Design note**:
  - Default recognizers are lightweight and local-first.

### `ingesting.py`

- **Purpose**: Build all retrieval artifacts from raw SDN CSV.
- **What it generates**:
  - `vector_db/` (Chroma vector store)
  - `bm25_corpus.json`
  - `knowledge_graph.pkl`
- **When to run**:
  - First setup
  - After SDN dataset updates

### `update_sdn.py`

- **Purpose**: Automated SDN refresh pipeline.
- **Flow**:
  1. Download latest SDN CSV
  2. Compare MD5 hash with existing file
  3. Backup old file to `data/backups/`
  4. Rebuild indexes only if data changed
- **Operational behavior**:
  - Supports proxy bypass: `SDN_BYPASS_PROXY=1`
  - If download fails but local `data/sdn.csv` exists, safely skips rebuild

### `retriever.py`

- **Purpose**: Standalone retrieval + matching script (CLI style).
- **Use case**: direct experimentation with retrieval/rerank logic outside the engine class.
- **Note**: kept mainly for utility/legacy flow; `engine.py` is primary runtime path.

### `test_engine.py`

- **Purpose**: quick smoke test for engine behavior.
- **Use case**: validate basic screening after setup or changes.

### `evaluate.py`

- **Purpose**: run evaluation against labeled dataset.
- **Current behavior**:
  - Uses helper functions from `retriever.py` for scoring.
- **Note**:
  - README roadmap calls out aligning this fully with `engine.py` pipeline.

### `benchmark.py`

- **Purpose**: latency/performance timing across engine calls.
- **Use case**: compare runtime impact of config or dependency changes.

### `generate_auto_tests.py`

- **Purpose**: create automated evaluation cases.
- **Output**: updates/creates `evaluation_data_auto.json`.

### `generator.py`

- **Purpose**: legacy/experimental generator flow (Ollama-based).
- **Note**: not part of default screening path.

### `check_data.py`

- **Purpose**: inspect/validate raw CSV preprocessing assumptions.
- **Use case**: debugging ingestion input quality.

---

## Data and Artifact Files

### `data/sdn.csv`

- **Purpose**: raw OFAC SDN source dataset.
- **Source**: downloaded manually or via `update_sdn.py`.

### `data/backups/`

- **Purpose**: timestamped backups of prior `sdn.csv` snapshots.
- **Created by**: `update_sdn.py`.

### `vector_db/`

- **Purpose**: persisted Chroma vector index.
- **Created by**: `ingesting.py`.

### `bm25_corpus.json`

- **Purpose**: lexical corpus + metadata for BM25 retrieval.
- **Created by**: `ingesting.py`.

### `knowledge_graph.pkl`

- **Purpose**: NetworkX graph linking entities, aliases, IDs, and programs.
- **Created by**: `ingesting.py`.

### `evaluation_data.json`

- **Purpose**: manually curated evaluation set.

### `evaluation_data_auto.json`

- **Purpose**: auto-generated evaluation dataset.
- **Created by**: `generate_auto_tests.py`.

### `audit_log.jsonl` (runtime-generated)

- **Purpose**: append-only screening audit records from API usage.
- **Created by**: `api.py` at runtime.
- **Git note**: intentionally ignored in `.gitignore`.

---

## Operational and Documentation Files

### `requirements.txt`

- **Purpose**: Python dependencies for setup and runtime.
- **Install with**:
  - `pip install -r requirements.txt`

### `.gitignore`

- **Purpose**: keep local/runtime artifacts out of version control.
- **Examples ignored**:
  - `.venv/`, `__pycache__/`, `data/backups/`, `logs/`, local env files

### `README.md`

- **Purpose**: project overview, setup, run commands, and operational guidance.

### `FILE_GUIDE.md` (this file)

- **Purpose**: file-by-file architecture orientation for faster onboarding.

---

## Typical End-to-End Flow

1. Install deps from `requirements.txt`.
2. Ensure `data/sdn.csv` exists (download or update script).
3. Run `ingesting.py` to build indexes.
4. Start app via `app_ui.py` (Streamlit) or `api.py` (FastAPI/uvicorn).
5. Optionally schedule `update_sdn.py` for periodic refresh.
6. Use `evaluate.py` and `benchmark.py` for quality/performance checks.

---

## Quick "What Should I Open First?" Suggestion

If you are new to the repo, open in this order:

1. `README.md` (high-level setup and run)
2. `engine.py` (core logic)
3. `api.py` and `app_ui.py` (entry points)
4. `ingesting.py` and `update_sdn.py` (data lifecycle)
5. `privacy.py` (optional redaction layer)
