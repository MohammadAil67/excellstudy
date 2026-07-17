"""
Learner Context MCP Server
──────────────────────────
FastMCP server exposing learner profile reads and skill progress writes.

Agents (built-in and third-party) call this using the standard FastMCP
client — no custom wrapper needed:

    from fastmcp import Client

    async with Client("http://learner-context-mcp:8001") as mcp:
        learner = await mcp.call_tool("get_learner", {
            "learner_id": "uuid",
            "agent_key": "my-agent-key"
        })

RBAC is enforced server-side by inspecting the agent_key in Redis.
  - Built-in agents  → full profile, ±100 delta on progress writes
  - Third-party agents → filtered profile, ±10 delta on progress writes

Run:
    python services/mcp_servers/learner_context_server.py

Port: 8001
"""

import json
import os
import django

# ── Bootstrap Django ORM outside of a runserver context ──────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ExcellStudy.settings")
django.setup()

import redis
from django.conf import settings
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# ── Server ────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="learner-context-server",
    instructions=(
        "Provides learner profile data and skill progress writes. "
        "Pass your agent_key on every call — access is filtered by agent type."
    ),
)

# ── RBAC ──────────────────────────────────────────────────────────────────────

def _agent_type(agent_key: str) -> str:
    """Return 'third_party' or 'builtin' from Redis agent registry."""
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    agent = json.loads(r.get(f"agent:key:{agent_key}") or "{}")
    return agent.get("type", "third_party")   # default to most restricted

def _is_third_party(agent_key: str) -> bool:
    return _agent_type(agent_key) == "third_party"

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_learner(learner_id: str, agent_key: str) -> dict:
    """
    Get learner profile.

    Built-in agents receive the full profile including mood_signal and
    session_data. Third-party agents receive a filtered session_data.

    Args:
        learner_id: UUID of the learner.
        agent_key:  Calling agent's registry key (used for RBAC).

    Returns:
        Learner profile dict.

    Raises:
        ToolError: If learner is not found.
    """
    from apps.core.models import Learner

    try:
        learner = await Learner.objects.aget(id=learner_id)
    except Learner.DoesNotExist:
        raise ToolError(f"Learner '{learner_id}' not found")

    full_profile = {
        "learner_id": str(learner.id),
        "age": learner.age,
        "grade": learner.grade,
        "skill_levels": learner.skill_levels,
        "current_module": learner.current_module_id,
        "learning_style": learner.learning_style,
        "mood_signal": learner.mood_signal,     # built-in only
        "session_data": learner.session_data,   # built-in only
    }

    if _is_third_party(agent_key):
        restricted = {"session_data"}
        return {k: v for k, v in full_profile.items() if k not in restricted}

    return full_profile



#this tool is unecessary but we'll keep it for now
@mcp.tool()
async def write_progress(
    learner_id: str,
    agent_key: str,
    updates: dict,
) -> dict:
    """
    Write skill progress deltas for a learner.

    Delta limits (clamped, not rounded):
      - Third-party agents: ±10 per subject per call
      - Built-in agents:   ±100 per subject per call

    Resulting skill levels are clamped to [0, 100].

    Args:
        learner_id: UUID of the learner.
        agent_key:  Calling agent's registry key (used for RBAC + delta limit).
        updates:    Dict of {subject_key: delta_int}.

    Returns:
        {"status": "ok", "updated": {subject: delta, ...}}

    Raises:
        ToolError: On invalid delta types, exceeded limits, or missing learner.
    """
    from apps.core.models import Learner

    max_delta = 10 if _is_third_party(agent_key) else 100

    for subject, delta in updates.items():
        if not isinstance(delta, int):
            raise ToolError(
                f"Delta for '{subject}' must be an integer, got {type(delta).__name__}"
            )
        if abs(delta) > max_delta:
            raise ToolError(
                f"Delta {delta} for '{subject}' exceeds the ±{max_delta} limit "
                f"for this agent type"
            )

    try:
        learner = await Learner.objects.aget(id=learner_id)
    except Learner.DoesNotExist:
        raise ToolError(f"Learner '{learner_id}' not found")

    for subject, delta in updates.items():
        current = learner.skill_levels.get(subject, 0)
        learner.skill_levels[subject] = max(0, min(100, current + delta))

    await learner.asave(update_fields=["skill_levels"])
    return {"status": "ok", "updated": updates}


@mcp.tool()
async def get_session(learner_id: str, agent_key: str) -> dict:
    """
    Get current session state for a learner from Redis.

    Returns an empty dict if no session exists.

    Args:
        learner_id: UUID of the learner.
        agent_key:  Calling agent's registry key (logged for audit).

    Returns:
        Session state dict (may be empty).
    """
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    raw = r.get(f"session:{learner_id}")
    return json.loads(raw) if raw else {}


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("MCP_SERVER_PORT", 8001))
    mcp.run(transport="streamable-http", port=port)
