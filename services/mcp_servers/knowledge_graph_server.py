"""
Knowledge Graph MCP Server
──────────────────────────
FastMCP server exposing Neo4j curriculum concept graph queries.

Agents call this using the standard FastMCP client:

    from fastmcp import Client

    async with Client("http://knowledge-graph-mcp:8002") as mcp:
        prereqs = await mcp.call_tool("get_prerequisites", {
            "concept": "fractions-addition"
        })

No agent_key is required here — concept graph data is not learner-sensitive.

Run:
    python services/mcp_servers/knowledge_graph_server.py

Port: 8002
"""

import os
import django

# ── Bootstrap Django ORM ──────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ExcellStudy.settings")
django.setup()

from django.conf import settings
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="knowledge-graph-server",
    instructions=(
        "Provides curriculum concept graph queries backed by Neo4j. "
        "Use get_prerequisites to find what a learner needs to know first. "
        "Use get_next_concepts to find what a learner is ready for next."
    ),
)

# ── Neo4j driver helper ───────────────────────────────────────────────────────

def _driver():
    from neo4j import AsyncGraphDatabase
    return AsyncGraphDatabase.driver(
        settings.NEO4J_URL,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_prerequisites(concept: str) -> list:
    """
    Get all prerequisite concepts for a given concept key.

    Returns nodes connected via PREREQUISITE_FOR → target concept.

    Args:
        concept: The concept key to look up (e.g. "fractions-addition").

    Returns:
        List of {"key": str, "name": str} dicts. Empty list if none found.
    """
    async with _driver().session() as session:
        result = await session.run(
            """
            MATCH (prereq)-[:PREREQUISITE_FOR]->(c:Concept {key: $concept})
            RETURN prereq.key AS key, prereq.name AS name
            ORDER BY prereq.name
            """,
            concept=concept,
        )
        return [
            {"key": record["key"], "name": record["name"]}
            async for record in result
        ]


@mcp.tool()
async def get_next_concepts(learner_id: str) -> list:
    """
    Get concepts the learner is ready to learn next.

    A concept is eligible when:
      - All its prerequisites have been mastered (skill_level >= 70).
      - The concept itself has not yet been mastered.

    Returns up to 5 candidates ordered by the graph traversal.

    Args:
        learner_id: UUID of the learner.

    Returns:
        List of {"key": str, "name": str} dicts.

    Raises:
        ToolError: If learner is not found.
    """
    from apps.core.models import Learner

    try:
        learner = await Learner.objects.aget(id=learner_id)
    except Learner.DoesNotExist:
        raise ToolError(f"Learner '{learner_id}' not found")

    mastered = [key for key, level in learner.skill_levels.items() if level >= 70]

    async with _driver().session() as session:
        result = await session.run(
            """
            MATCH (mastered:Concept)-[:PREREQUISITE_FOR]->(next:Concept)
            WHERE mastered.key IN $mastered
              AND NOT next.key IN $mastered
            RETURN DISTINCT next.key AS key, next.name AS name
            LIMIT 5
            """,
            mastered=mastered,
        )
        return [
            {"key": record["key"], "name": record["name"]}
            async for record in result
        ]


@mcp.tool()
async def get_concept(concept_key: str) -> dict:
    """
    Get full details of a single concept node from the knowledge graph.

    Args:
        concept_key: The concept's unique key (e.g. "fractions-basics").

    Returns:
        Dict of all node properties. Empty dict if concept not found.
    """
    async with _driver().session() as session:
        result = await session.run(
            "MATCH (c:Concept {key: $key}) RETURN c",
            key=concept_key,
        )
        record = await result.single()
        return dict(record["c"]) if record else {}


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("MCP_SERVER_PORT", 8002))
    mcp.run(transport="streamable-http", port=port)
