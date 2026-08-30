"""Query Expansion: LLM extracts search keywords from the user question (issue #12).

Runs before hybrid search. The keywords feed the FTS retriever only — the
vector retriever keeps the original question, because extra keywords blur
its embedding. Determinism: fixed minimal English instruction template,
temperature 0, keyword limit from config. Fallback policy: an unreachable
Ollama, a timeout, or a malformed answer yield [] — plain search by the
original question, never a failure.
"""

import re
import sys
from pathlib import Path

import requests

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EXPANSION_TIMEOUT, KEYWORD_LIMIT, OLLAMA_MODEL, OLLAMA_URL

# Fixed minimal English instruction (determinism); the tiny model answers in
# the question's language. `think` is disabled: a thinking model would spend
# the token budget on reasoning and return an empty line.
KEYWORDS_PROMPT = (
    "Extract up to {limit} search keywords from the question. "
    "Answer with a single comma-separated line, keywords in the question's language. "
    "Do not explain. Question: {question}"
)

# The tiny model sometimes prefixes the answer with a label ("keywords:");
# a leading short word sequence ending in ':' is stripped before parsing.
_LABEL_RE = re.compile(r"^\s*\w[\w ]{0,29}:\s*")


def parse_keywords(raw: str | None, limit: int = KEYWORD_LIMIT) -> list[str]:
    """Parse the raw LLM answer into keywords (pure fallback policy).

    A leading short label ("keywords:") is stripped first — the tiny model
    sometimes prefixes the answer line. Then split on commas, trim
    whitespace, drop empties, deduplicate preserving the first occurrence,
    cap at `limit`. An empty or missing raw answer yields [] — the
    no-expansion fallback.
    """
    if not raw:
        return []
    raw = _LABEL_RE.sub("", raw, count=1)
    keywords: list[str] = []
    for part in raw.split(","):
        word = part.strip()
        if word and word not in keywords:
            keywords.append(word)
    return keywords[:limit]


def expand_query(question: str) -> list[str]:
    """Extract search keywords from the question; [] on any failure.

    Calls Ollama with the fixed template, temperature 0 and a hard
    EXPANSION_TIMEOUT. An unreachable Ollama, a timeout, an HTTP error, or
    a malformed body degrade to [] — search by the original question.
    """
    prompt = KEYWORDS_PROMPT.format(limit=KEYWORD_LIMIT, question=question)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0},
            },
            timeout=EXPANSION_TIMEOUT,
        )
        response.raise_for_status()
        raw = response.json().get("response") or ""
        return parse_keywords(raw)
    # Intentionally broad: any expansion failure must degrade to an empty
    # keyword list, not break the search.
    except Exception as e:  # noqa: BLE001
        print(
            f"⚠️  Query expansion failed ({type(e).__name__}: {e}); searching by the question only"
        )
        return []
