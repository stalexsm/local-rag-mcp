#!/usr/bin/env python3
"""
Company Knowledge Base Assistant - Main Entry Point
"""

import io
import sys

from assistant import CompanyKBAssistant
from cli_input import read_question


def _force_utf8_stdio() -> None:
    """Force UTF-8 on stdio so Cyrillic input and emoji output survive any locale.

    Undecodable bytes become U+FFFD instead of raising UnicodeDecodeError,
    and non-encodable text is replaced instead of raising UnicodeEncodeError.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    """Main entry point for the assistant."""
    _force_utf8_stdio()
    if len(sys.argv) > 1 and sys.argv[1] == "build-index":
        # Build index mode
        from rag.build_index import build_index

        build_index()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        # Search benchmark mode (Recall@5 / MRR, three retrieval modes)
        from rag.benchmark import run_benchmark

        run_benchmark()
        return

    # Interactive Q&A mode
    assistant = CompanyKBAssistant()

    print("=" * 60)
    print("🤖 Company Knowledge Base Assistant")
    print("=" * 60)
    print("\nAsk questions about company policies, procedures, and documentation.")
    print("Type 'exit' or 'quit' to stop\n")

    try:
        while True:
            query = read_question()

            if query is None:
                print("\n👋 Goodbye!")
                break

            if not query:
                continue

            if query.lower() in {"exit", "quit", "q"}:
                print("\n👋 Goodbye!")
                break

            print("\n" + "─" * 60)
            print("🤖 Answer:\n")

            try:
                result = assistant.query(query, verbose=True)
                print(result["answer"])

                if result["sources"]:
                    print("\n📚 Sources:")
                    for src in result["sources"]:
                        print(f"  • {src}")

                if result["mcp_used"]:
                    print(f"\n🔧 Used MCP tool: {result['mcp_tool']}")

            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback

                traceback.print_exc()

            print("─" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        assistant.close()


if __name__ == "__main__":
    main()
