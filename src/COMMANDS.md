# Setup and Run Commands

Run these commands in order to set up and use the Company Knowledge Base Assistant.

## Prerequisites

1. **Install uv** — it manages Python, the virtual environment and
   dependencies (nothing is installed manually):
   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # or: brew install uv
   ```
2. **Install Ollama** and pull the model:
   ```bash
   # macOS
   brew install ollama
   # Or download from https://ollama.ai

   # Pull the model used by config.py
   ollama pull qwen3:0.6b
   ```

## Setup Steps

### 1. Sync the environment (from the repository root)
```bash
uv sync
```
One command replaces the whole old routine: downloads Python 3.12 if
missing (pinned in `.python-version`), creates `.venv/` and installs the
exact versions from `uv.lock` — runtime dependencies plus the dev group
(pytest, ruff, ty, pre-commit). There is no virtual environment to
activate: `uv run` picks up the project environment automatically.

### 2. Add company documentation
Put your documents (`.txt`, `.md`, `.pdf`, `.docx`) into `src/docs/`
(subfolders are allowed). The directory is tracked as an empty placeholder
(`src/docs/.gitkeep`) — the documents themselves are local data.

### 3. Update configuration (optional)
Edit `src/config.py` if needed:
- Set `DOCUMENTS_DIR` to your documents path (default: `./docs`, resolved
  against `src/`; absolute paths are used as-is)
- Change `OLLAMA_MODEL` if using a different model (default: `qwen3:0.6b`)
- Adjust `CHUNK_SIZE`, `CHUNK_OVERLAP`, or `TOP_K` as needed

### 4. Build the FAISS index (Optional)

The index will be built automatically on first use. To manually build it:

```bash
cd src
uv run python main.py build-index
```

Or directly:
```bash
cd src
uv run python -m rag.build_index
```

`uv run` finds the manifest in the repository root even when launched from
`src/`; Python itself must run from `src/` because module imports resolve
from there (config paths in `config.py` are anchored to `src/` themselves).

This will:
- Load all documents from the `src/docs/` directory
- Chunk them into smaller pieces
- Generate embeddings
- Build the FAISS index
- Save `index.faiss` and `chunks.pkl`

## Usage

### Interactive CLI Mode

Run the assistant interactively:
```bash
cd src
uv run python main.py
```

Then ask questions like:
- "What is our vacation policy?"
- "How do I request time off?"
- "What are the company values?"

Type `exit` or `quit` to stop.

### Search Benchmark (Optional)

```bash
cd src
uv run python main.py benchmark
```

Runs the marked query set from `src/rag/benchmark.py` (15 queries,
relevance at document level) through three modes — vector, FTS (BM25),
hybrid — and prints a markdown table with Recall@5 and MRR. Requires a
built index; the hybrid mode additionally queries Ollama for query
expansion. The current table and its interpretation live in the README.

## Updating the Knowledge Base

When you add new documents or update existing ones:

1. Add/update files in `src/docs/`
2. Rebuild the index:
   ```bash
   cd src
   uv run python main.py build-index
   ```

## Troubleshooting

### "Index not found" error
- The index will be built automatically on first use
- Or manually run `uv run python main.py build-index`

### "No documents found"
- Check that `src/docs/` contains files
- Verify `DOCUMENTS_DIR` in `src/config.py` is correct
- Ensure files have supported extensions (`.txt`, `.md`, `.pdf`, `.docx`)

### Ollama connection errors
- Make sure Ollama is running: `ollama list`
- Verify the model is installed: `ollama pull qwen3:0.6b`
- Check `OLLAMA_URL` in `src/config.py` (default: `http://localhost:11434/api/generate`)

### MCP client errors
- MCP tools are optional - the assistant will work without them
- If MCP fails, RAG will still function

### Import errors
- Make sure you run Python from the `src/` directory: `cd src && uv run python main.py`
- Do not create or activate environments manually — `uv run` resolves the
  project environment from the root manifest
- If the environment looks broken, re-run `uv sync` from the repository root

## Development Checks

Unit tests cover only the pure seams — hybrid search (the RRF merge
`src/rag/merge.py`, the in-memory FTS `src/rag/fts.py`, keyword parsing
`src/rag/expansion.py`) and the document sandbox (`src/sandbox.py`). They
run on hand-made chunks and answer strings: no mocks of FAISS/Ollama/HTTP,
no reading generated artifacts (`index.faiss`, `chunks.pkl`):

```bash
cd src
uv run pytest
# Expected: all tests pass (exit code 0)
```

Everything those tests do not reach — ingest, embedding, the FAISS index,
MCP, LLM answers — is verified by real runs: rebuild the index and run one
smoke query, stating what exactly passed. Retrieval quality itself (vector
vs FTS vs hybrid) is measured by the Search Benchmark above, not by unit
tests.

Type checking runs in ratchet mode: the baseline is "0 diagnostics", so any
new output from `ty` is a real regression, not known noise. The initial
baseline was reached with cheap fixes only (no ignores were needed). New
diagnostics must be fixed (prefer signature annotations) or muted with a
narrowly scoped, justified ignore — no global rule disables.

```bash
# From the repository root
uv run ty check src
# Expected: "All checks passed!" (exit code 0)
# Baseline recorded: 2026-08-30, ty version pinned in uv.lock
```

Lint and format (also part of the baseline):

```bash
uv run ruff check .
uv run ruff format --check .
# Expected: no findings (exit code 0)
```

Lint and format also run as pre-commit hooks on every commit (official
ruff-check and ruff-format). `ty` is deliberately not a hook — it runs as
the local command above, keeping commits fast:

```bash
uv run pre-commit install        # once per clone
uv run pre-commit run --all-files
# Expected: Passed (exit code 0)

ruff-check runs with --fix: on failure the hook edits the staged files
in place — re-add them (`git add`) and commit again. When ruff is bumped
in uv.lock, update `rev` in .pre-commit-config.yaml to the same version
so the hook and the local commands above agree.
```

## Quick Start Summary

```bash
# 1. One-time setup (from the repository root)
uv sync
ollama pull qwen3:0.6b

# 2. Prepare documents
# Add your company documentation files to src/docs/

# 3. Build index
cd src
uv run python main.py build-index

# 4. Run
uv run python main.py

# Checks (from the repository root unless stated otherwise)
uv run pytest          # run from src/: cd src && uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src
```
