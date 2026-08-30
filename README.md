# Local RAG/MCP Knowledge Base Assistant

# 📋 The Problem

- **Growing Documentation**: Knowledge scattered across files
- **Information Retrieval**: Hard to find answers without keywords
- **Privacy Concerns**: Cloud solutions may not comply with policies

```
Users → Search → Answer = 😫
```

# ✨ The Solution

A **local, intelligent Q&A system** using:

- **RAG**: Semantic search over documentation
- **MCP**: Dynamic document access
- **Local LLM**: Privacy-preserving answers (Ollama)

# ✨ Key Benefits

- ✅ Privacy-first (runs locally)
- ✅ No API costs
- ✅ Fast semantic search
- ✅ Intelligent document access
- ✅ Complete data control

# 🏗️ Architecture - Top Level

```
┌──────────────────────┐
│   User Interface     │ (CLI)
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  [RAG]       [MCP]
   Query      Tools
     │           │
     └─────┬─────┘
           ▼
    [Ollama LLM]
```

# 🏗️ Architecture - Storage

```
┌────────────────┐
│  FAISS Index   │ Vector Database
│  + MCP Tools   │
└────────┬───────┘
         │
    ┌────▼─────┐
    │   docs/  │
    │directory │
    └──────────┘
```

# 🔍 RAG Pipeline

1. Document Loading → Read .md, .txt, .pdf, .docx
2. Chunking → Split into 700-char chunks
3. Embedding → Use SentenceTransformers
4. Indexing → Build FAISS vector index
5. Query → Retrieve top 5 similar chunks
6. Prompt Building → Create context-aware prompt
7. LLM Generation → Get answer from model

# 🔍 Why FAISS?

- Fast vector similarity search
- Lightweight and memory-efficient
- No external dependencies
- Perfect for local deployments
- Millions of vectors supported

# 📊 Search Benchmark (Recall@5 / MRR)

Бенчмарк поиска сравнивает три режима на размеченном наборе из 15 запросов
(7 лексических — точные названия процессов, ролей и документов, 8 —
семантические перефразировки без точных названий; релевантность на уровне
документа). Гибридный
режим — это финальная система: параллельные ретриверы, RRF-слияние и Query
Expansion.

| Режим | Recall@5 | MRR |
| --- | --- | --- |
| Векторный (FAISS) | 0.53 | 0.27 |
| FTS (BM25) | 0.73 | 0.55 |
| Гибрид (RRF + Query Expansion) | 0.73 | 0.46 |

Как читать:

- На лексических запросах (точные названия) гибрид и FTS обгоняют векторный
  поиск: Recall@5 0.73 против 0.53 — дословные совпадения и имена файлов в
  BM25 возвращают документы, которые семантическая близость размывает.
- Гибрид сохраняет Recall@5 чистого FTS, при этом устойчив к морфологии и
  перефразировкам за счёт векторного ретривера в том же слиянии.
- MRR гибрида (0.46) немного ниже чистого FTS (0.55): RRF с равными весами
  ставит консенсусные чанки двух ретриверов выше одиночного топа BM25 — это
  осознанная цена устойчивости к несовместимым шкалам скоров.
- Общие промахи всех режимов — русскоязычные перефразировки без дословных
  совпадений: эмбеддинг-модель англоцентрична (all-MiniLM-L6-v2), стемминга
  в FTS нет. Это известные границы текущих моделей, а не регресс слияния.

Воспроизведение (нужны построенный индекс и запущенный Ollama):

```bash
cd src && uv run python main.py benchmark
```

# 🔧 MCP - Model Context Protocol

MCP provides **standardized interface** for LLM tool access:

```python
read_document(file_path)
list_documents()
search_documents(query)
```

# 🔧 MCP Benefits

- Tool Use by LLM
- Real-time document access
- Standardized interface
- Easy to extend
- Local tool execution

# 💻 Tech Stack

```
Language:      Python 3.12 (pinned, managed by uv)
Vector DB:     FAISS
Embeddings:    SentenceTransformers
LLM:           Ollama (local)
MCP:           FastMCP
```

# 📁 Project Structure

```
src/
├── config.py           Configuration
├── main.py             CLI entry point
├── assistant.py        Main orchestrator
├── rag/
│   ├── ingest.py      Load documents
│   ├── chunk.py       Split text
│   ├── embed.py       Generate embeddings
│   ├── build_index.py Build FAISS index
│   └── query.py       Retrieve & generate
├── mcp/
│   ├── server.py      MCP tool definitions
│   └── client.py      MCP client wrapper
└── docs/              Documentation
```

# 🚀 Index Building (Setup)

```
$ cd src && uv run python main.py build-index

1. Load documents
  ↓
2. Split into chunks
  ↓
3. Generate embeddings
  ↓
4. Build FAISS index
  ↓
5. Save files
```

# 🚀 Query Processing (Runtime)

```
User Question
  ↓
Embed question
  ↓
Search FAISS → Top 5 chunks
  ↓
LLM decides: Use MCP tools?
  ↓
Build prompt + context
  ↓
Call Ollama
  ↓
Return answer + sources
```

# ✨ Core Features

- **Semantic Search**: Find by meaning, not keywords
- **Multi-format**: .md, .txt, .pdf, .docx files
- **Source Attribution**: Shows document sources
- **MCP Tools**: LLM can read full documents
- **No External APIs**: Runs locally only
- **Fast Retrieval**: Sub-second search

# ⚙️ Configuration Options

```python
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen3:0.6b"
TOP_K = 5
```

# 🎬 Live Demo - Starting

```bash
$ cd src && uv run python main.py
```

Output:
```
🤖 Company Knowledge Base
Ask questions about documentation
Type 'exit' to stop
```

# 🎬 Demo - Query 1

```
❓ What are company values?

🤖 Innovation, integrity, collaboration

📚 Sources:
  • Loan Rangers Team.md
  • Info Security.md
```

# 🎬 Demo - Query 2

```
❓ What documents do we have?

🤖 [Uses MCP list_documents]
  • Loan Rangers Team.md
  • Information Security.md
  • Services.md
```

# 🎬 Demo - Query 3

```
❓ Full security policy?

🤖 [Uses MCP read_document]
[Full document content...]
```

# 🔐 Security - Local vs Cloud

**Cloud**: Data → Internet → Server
- ⚠️ Network transmission
- ⚠️ External storage
- ⚠️ Subscription costs

**Local**: Data → Local System
- ✅ No transmission
- ✅ Local storage only
- ✅ No costs

# 🔐 Implementation Safeguards

- **MCP Sandbox**: Prevents path traversal
- **Local Storage**: Documents stay on device
- **No Telemetry**: No tracking
- **Offline Ready**: Works without internet

# ⚡ Tuning for Speed

```python
# Faster (smaller model):
OLLAMA_MODEL = "qwen3:0.6b"

# Faster retrieval:
TOP_K = 3
CHUNK_SIZE = 500
```

# 🚢 Deployment - Single Machine

```
1. Install uv & Ollama, then run: uv sync
2. Copy docs/ to server
3. Build index
4. Run with nohup

$ nohup uv run python main.py > log &
```

# 🚢 Scaling - Option 1: FastAPI

```
[HTTP Clients]			[HTTP Clients + Webllm]
       ↓        						 ↓
   [FastAPI]     				 [FastAPI]
       ↓         					 ↓
[Ollama + FAISS]      			  [FAISS]
```

# 🚢 Scaling - Option 2: Distributed

```
[Clients] → [Load Balancer]
             ↓
      [Multiple Retrievers]
```

# 🔮 Phase 2: Enhanced Features

- ☐ Web UI (Streamlit)
- ☐ API endpoints
- ☐ Multi-language support
- ☐ Document versioning
- ☐ Fine-tuned embeddings

# 🔮 Phase 3: Advanced

- ☐ Conversation memory
- ☐ Multi-hop reasoning
- ☐ Metadata filtering
- ☐ Feedback loop
- ☐ Analytics dashboard

# 🔮 Phase 4: Enterprise

- ☐ User authentication
- ☐ Audit logging
- ☐ Role-based access
- ☐ LLM fine-tuning
- ☐ Cost analysis

# 📊 Why This Works

| Aspect | Traditional | Our RAG |
|--------|---|---|
| **Understanding** | Keywords | Semantic |
| **Answers** | Documents | Direct |
| **Privacy** | Cloud | Local |
| **Cost** | Subscription | One-time |
| **Speed** | Slow | Sub-second |

# ✅ What You Have Now

- Local privacy-first knowledge base
- Fast semantic search (FAISS)
- Intelligent tool use (MCP)
- Maintainable Python code
- Foundation for enterprise features

# 🙋 Quick Reference

```bash
# One-time setup (repository root)
uv sync
ollama pull qwen3:0.6b

# Build index (from src/)
cd src && uv run python main.py build-index

# Run interactively
uv run python main.py

# Check config
cat src/config.py

# Full setup, checks and troubleshooting
see src/COMMANDS.md
```

# 📚 Resources

- **Code**: MobilaName/local-rag-mcp
- **FAISS**: facebook/faiss
- **Ollama**: ollama.ai
- **FastMCP**: github.com/jlowin/fastmcp
- **Transformers**: huggingface.co

**Thank You!**
