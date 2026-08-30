import sys
from pathlib import Path

from fastmcp import FastMCP

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DOCUMENTS_DIR
from discovery import iter_supported_files

mcp = FastMCP("doc-tools", version="1.0.0")


@mcp.tool
def read_document(file_path: str) -> str:
    """Reads a document from the knowledge base."""
    try:
        path = Path(file_path)
        # Security: ensure path is within documents directory
        if not str(path.resolve()).startswith(str(Path(DOCUMENTS_DIR).resolve())):
            return f"Error: Access denied. File must be in {DOCUMENTS_DIR}"

        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    # Intentionally broad: a tool must return an error string instead of
    # crashing the MCP server process (client falls back to RAG on failure).
    except Exception as e:  # noqa: BLE001
        return f"Error reading file: {str(e)}"


@mcp.tool
def list_documents() -> str:
    """Lists all available documents in the knowledge base."""
    try:
        base_dir = Path(DOCUMENTS_DIR)
        if not base_dir.exists():
            return f"Error: Documents directory {DOCUMENTS_DIR} does not exist"

        documents = sorted(
            str(path.relative_to(base_dir)) for path in iter_supported_files(base_dir)
        )

        if not documents:
            return "No documents found in the knowledge base."

        return "\n".join(f"- {doc}" for doc in documents)
    # Intentionally broad: see read_document — tools must not crash the server.
    except Exception as e:  # noqa: BLE001
        return f"Error listing documents: {str(e)}"


@mcp.tool
def search_documents(query: str) -> str:
    """Searches for documents by name (case-insensitive)."""
    try:
        base_dir = Path(DOCUMENTS_DIR)
        if not base_dir.exists():
            return f"Error: Documents directory {DOCUMENTS_DIR} does not exist"

        query_lower = query.lower()
        matches = sorted(
            str(path.relative_to(base_dir))
            for path in iter_supported_files(base_dir)
            if query_lower in path.name.lower()
        )

        if not matches:
            return f"No documents found matching '{query}'"

        return "\n".join(f"- {doc}" for doc in matches)
    # Intentionally broad: see read_document — tools must not crash the server.
    except Exception as e:  # noqa: BLE001
        return f"Error searching documents: {str(e)}"


if __name__ == "__main__":
    # Run MCP server (stdio)
    mcp.run()
