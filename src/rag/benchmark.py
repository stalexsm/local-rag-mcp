"""Search benchmark: Recall@5 and MRR per retrieval mode (issue #13).

A marked query set (relevance at document level, by chunk source) runs
through three modes:

- vector — the vector-only retriever: the HYBRID_SEARCH kill-switch is
  forced off for the run, restoring the pre-hybrid behavior;
- fts — the BM25 retriever alone on the bare question (the pure lexical
  baseline; in the final system FTS also receives expansion keywords);
- hybrid — both kill-switches forced on: the final system with query
  expansion.

Modes are forced through the config kill-switches instead of a
re-implementation, so the hybrid column measures the shipped pipeline.
Metrics are document-level: a retrieved chunk hits when its source
document is in the query's relevant set. Output is a markdown table on
stdout for pasting into README.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from config import DOCUMENTS_DIR, TOP_K
from rag.fts import fts_search


# Paths are relative to src/docs, posix form, matching chunk sources.
@dataclass(frozen=True)
class BenchmarkCase:
    """One marked query with its relevant documents."""

    query: str
    relevant: tuple[str, ...]


# Seven lexical cases (exact role, process and document names) and seven
# semantic paraphrases (same documents, no exact names in the query).
BENCHMARK_CASES: list[BenchmarkCase] = [
    # Lexical: exact process names
    BenchmarkCase("Sprint Planning", ("Процессы/Sprint Planning.md",)),
    BenchmarkCase("Sprint Retrospective", ("Процессы/Sprint Retrospective.md",)),
    BenchmarkCase("Mid-Sprint Sync", ("Процессы/Mid-Sprint Sync.md",)),
    BenchmarkCase("Code Review Checkpoint", ("Процессы/Code Review Checkpoint.md",)),
    # Lexical: exact role names
    BenchmarkCase("Product Owner", ("Роли/Product Owner (PO).md",)),
    BenchmarkCase("Tech Lead", ("Роли/Tech Lead.md",)),
    # Lexical: exact document terms
    BenchmarkCase(
        "Rate Limiting",
        ("Документация/Бэкенд/Ограничение частоты запросов (Rate Limiting).md",),
    ),
    # Semantic paraphrases (the target words do not occur in the documents)
    BenchmarkCase("как проходит планирование спринта", ("Процессы/Sprint Planning.md",)),
    BenchmarkCase("кто отвечает за приоритеты продукта", ("Роли/Product Owner (PO).md",)),
    BenchmarkCase(
        "кто устраняет блокеры и ведёт дейли митинги", ("Роли/Team Lead | Scrum Master.md",)
    ),
    BenchmarkCase(
        "почему api начал отклонять запросы, если слать их слишком часто",
        ("Документация/Бэкенд/Ограничение частоты запросов (Rate Limiting).md",),
    ),
    BenchmarkCase(
        "как поднять фронтенд локально с нуля",
        ("Документация/Фронтенд/02-Настройка и конфигурация/Установка и запуск.md",),
    ),
    BenchmarkCase("как называть ветки в git", ("Документация/Работа с Git.md",)),
    BenchmarkCase(
        "чем покрыть компоненты интерфейса автотестами и сквозными сценариями",
        ("Документация/Фронтенд/05-Разработка/Тестирование.md",),
    ),
    BenchmarkCase(
        "как обновлять схему базы данных",
        ("Документация/Бэкенд/База данных/Миграции.md",),
    ),
]


def doc_id(source: str) -> str:
    """Doc-level id of a chunk: its path relative to the documents dir."""
    path = Path(source)
    try:
        return path.resolve().relative_to(Path(DOCUMENTS_DIR).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def unique_documents(chunks: list) -> list[str]:
    """Ranking at document level: sources deduplicated, first occurrence order."""
    docs: list[str] = []
    for chunk in chunks:
        doc = doc_id(chunk["source"])
        if doc not in docs:
            docs.append(doc)
    return docs


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Share of relevant documents found within the first k retrieved."""
    if not relevant:
        return 0.0
    hits = len(set(retrieved[:k]) & relevant)
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant document (0 if none in top-TOP_K)."""
    for rank, doc in enumerate(retrieved, start=1):
        if doc in relevant:
            return 1.0 / rank
    return 0.0


@contextmanager
def _forced_switches(**overrides: bool) -> Iterator[None]:
    """Temporarily force kill-switch flags in the loaded rag.query module.

    retrieve() reads its flags from module globals at call time, so this
    switches the live pipeline, not a copy of it; the saved values are
    always restored.
    """
    from rag import query as rq

    saved = {name: getattr(rq, name) for name in overrides}
    for name, value in overrides.items():
        setattr(rq, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(rq, name, value)


def _retrieve_vector(question: str) -> list:
    """Vector-only mode: hybrid kill-switch off (expansion is skipped too)."""
    from rag import query as rq

    with _forced_switches(HYBRID_SEARCH=False):
        return rq.retrieve(question)


def _retrieve_fts(question: str) -> list:
    """FTS-only mode: pure BM25 on the bare question, top TOP_K."""
    from rag import query as rq

    if rq.bm25_index is None or not rq.chunks:
        return []
    return [rq.chunks[pos] for pos in fts_search(rq.bm25_index, question, TOP_K)]


def _retrieve_hybrid(question: str) -> list:
    """Hybrid mode: the final system with query expansion."""
    from rag import query as rq

    with _forced_switches(HYBRID_SEARCH=True, QUERY_EXPANSION=True):
        return rq.retrieve(question)


MODES: list[tuple[str, Callable[[str], list]]] = [
    ("Векторный (FAISS)", _retrieve_vector),
    ("FTS (BM25)", _retrieve_fts),
    ("Гибрид (RRF + расширение запроса)", _retrieve_hybrid),
]


def format_table(rows: list[tuple[str, float, float]]) -> str:
    """Render mode x metric averages as a markdown table."""
    lines = ["| Режим | Recall@5 | MRR |", "| --- | --- | --- |"]
    lines.extend(f"| {label} | {recall:.2f} | {rr:.2f} |" for label, recall, rr in rows)
    return "\n".join(lines)


def run_benchmark() -> None:
    """Run every marked query through every mode and print the summary table."""
    from rag import query as rq

    if rq.index is None or not rq.chunks:
        print("❌ Индекс не построен. Сначала: cd src && uv run python main.py build-index")
        return

    total = len(BENCHMARK_CASES)
    print(f"🔍 Бенчмарк поиска: {total} запросов, TOP_K={TOP_K}")

    rows: list[tuple[str, float, float]] = []
    for label, runner in MODES:
        print(f"\n— {label}")
        recall_sum = 0.0
        mrr_sum = 0.0
        for i, case in enumerate(BENCHMARK_CASES, start=1):
            docs = unique_documents(runner(case.query))
            relevant = set(case.relevant)
            recall_sum += recall_at_k(docs, relevant, TOP_K)
            mrr_sum += mrr(docs, relevant)
            print(f"  {i:>2}/{total}  {case.query}")
        rows.append((label, recall_sum / total, mrr_sum / total))

    print("\nРезультаты (среднее по запросам, релевантность на уровне документа):\n")
    print(format_table(rows))
