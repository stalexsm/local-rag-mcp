# ADR-0003: Параллельный поиск — ThreadPoolExecutor, а не asyncio

## Статус

Принято (2026-08-30). Контекст — спека «Hybrid Search (FTS) и Query Expansion» (Task-RAG.txt).

## Контекст

Спека допускает `asyncio.gather` или `ThreadPoolExecutor` для параллельного запуска
векторного поиска и FTS. Текущий стек полностью синхронный: `requests` к Ollama,
блокирующие FAISS и sentence-transformers, синхронный `assistant.py`.

## Решение

Векторный и FTS-поиск выполняются параллельно в `ThreadPoolExecutor`; публичный API
(`retrieve()` и выше) остаётся синхронным. GIL не ограничивает: FAISS и numpy
освобождают его на C-уровне, BM25 чистый Python, но на корпусе из сотен чанков это
миллисекунды.

asyncio отклонён: он потребовал бы переписать вызовы Ollama на асинхронный клиент,
перевести `assistant.py` на async и всё равно завернуть CPU-bound FAISS в
`to_thread` — инвазивная миграция без выигрыша для двух конкурентных вызовов.
