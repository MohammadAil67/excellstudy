"""
Content MCP Server
──────────────────
FastMCP server exposing pgvector semantic search and Django ORM course/module
retrieval to agent containers for RAG context injection.

Agents call this using the standard FastMCP client:

    from fastmcp import Client

    async with Client("http://content-mcp:8003") as mcp:
        chunks = await mcp.call_tool("search_content", {
            "query": "visual explanation of fractions",
            "limit": 3
        })

No agent_key required — content data is not learner-sensitive.

Run:
    python services/mcp_servers/content_server.py

Port: 8003
"""

import os
import sys
import django

# Ensure project root is in sys.path for standalone microservice execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ── Bootstrap Django ORM ──────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ExcellStudy.settings")
django.setup()

from django.conf import settings
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import asyncpg
import asyncio
from fastembed import TextEmbedding

# Initialize lightweight local embedding model (all-MiniLM-L6-v2, 384 dims)
embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="content-server",
    instructions=(
        "Provides course content retrieval and semantic search for RAG. "
        "Use search_content to find relevant content chunks to inject into "
        "your LLM context before generating a response."
    ),
)

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_content(query: str, limit: int = 5) -> list:
    """
    Semantic search over course content chunks using pgvector and MiniLM embeddings.

    Steps:
      1. Embeds the query via all-MiniLM-L6-v2 (384 dimensions).
      2. Runs cosine-similarity search against content_chunks in Supabase.
      3. Returns the top `limit` chunks ranked by similarity.

    Use this to build RAG context before calling your LLM.

    Args:
        query: Natural language search query.
        limit: Max number of results to return (default 5, max 20).

    Returns:
        List of {"title", "content", "subject", "similarity"} dicts,
        ordered by descending similarity.

    Raises:
        ToolError: On embedding failure or database connection error.
    """
    if not query or not query.strip():
        return []

    limit = min(max(1, limit), 20)  # hard cap between 1 and 20

    try:
        # Run local CPU embedding inference asynchronously
        def _embed():
            return list(embedding_model.embed([query.strip()]))[0].tolist()

        query_embedding = await asyncio.to_thread(_embed)
    except Exception as exc:
        raise ToolError(f"Embedding generation failed: {exc}")

    try:
        conn = await asyncpg.connect(settings.SUPABASE_DB_URL, statement_cache_size=0)
        try:
            rows = await conn.fetch(
                """
                SELECT title, content, subject,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM content_chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                str(query_embedding),
                limit,
            )
        finally:
            await conn.close()
    except Exception as exc:
        raise ToolError(f"Content search failed: {exc}")

    return [
        {
            "title": row["title"],
            "content": row["content"],
            "subject": row["subject"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]


@mcp.tool()
async def get_course(course_id: str) -> dict:
    """
    Get a full course record with all its modules in display order.

    Args:
        course_id: UUID of the course.

    Returns:
        {"id", "title", "subject", "modules": [{"id", "title", "order"}]}

    Raises:
        ToolError: If course is not found.
    """
    from apps.core.models import Course

    try:
        course = await Course.objects.prefetch_related("modules").aget(id=course_id)
    except Course.DoesNotExist:
        raise ToolError(f"Course '{course_id}' not found")

    return {
        "id": str(course.id),
        "title": course.title,
        "subject": course.subject,
        "modules": [
            {"id": str(m.id), "title": m.title, "order": m.order}
            async for m in course.modules.all().order_by("order")
        ],
    }


@mcp.tool()
async def get_module(module_id: str) -> dict:
    """
    Get a single module with its concept key and parent course title.

    Args:
        module_id: UUID of the module.

    Returns:
        {"id", "title", "concept_key", "course"}

    Raises:
        ToolError: If module is not found.
    """
    from apps.core.models import Module

    try:
        module = await Module.objects.select_related("course").aget(id=module_id)
    except Module.DoesNotExist:
        raise ToolError(f"Module '{module_id}' not found")

    return {
        "id": str(module.id),
        "title": module.title,
        "concept_key": module.concept_key,
        "course": module.course.title,
    }


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("MCP_SERVER_PORT", 8003))
    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
    mcp.run(transport="streamable-http", host=host, port=port)


