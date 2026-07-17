# Platform MCP Servers

Three [FastMCP](https://github.com/jlowin/fastmcp) servers that agents call 
**outward** to access platform data. They are never in the main 
`learner → router → agent` request path.

---

## Servers

| Server | Port | What it exposes |
|--------|------|-----------------|
| `learner-context-server` | **8001** | Learner profile, skill progress writes, session state |
| `knowledge-graph-server` | **8002** | Neo4j curriculum prerequisite + concept graph |
| `content-server`         | **8003** | pgvector semantic search (RAG), courses, modules |

---

## How any agent calls them

Every agent — built-in or third-party — uses **exactly the same pattern**:

```python
from fastmcp import Client

# Learner data
async with Client("http://learner-context-mcp:8001") as mcp:
    learner = await mcp.call_tool("get_learner", {
        "learner_id": "uuid",
        "agent_key": "my-agent-key"
    })

# Knowledge graph
async with Client("http://knowledge-graph-mcp:8002") as mcp:
    prereqs = await mcp.call_tool("get_prerequisites", {
        "concept": "fractions-addition"
    })

# Content search (RAG)
async with Client("http://content-mcp:8003") as mcp:
    chunks = await mcp.call_tool("search_content", {
        "query": "visual explanation of fractions",
        "limit": 3
    })
```

Server URLs come from environment variables injected into the agent container:

```
LEARNER_CONTEXT_MCP_URL=http://learner-context-mcp:8001
KNOWLEDGE_GRAPH_MCP_URL=http://knowledge-graph-mcp:8002
CONTENT_MCP_URL=http://content-mcp:8003
```

---

## RBAC (learner-context-server only)

Pass `agent_key` on every call to `learner-context-server`. The server
looks up the key in Redis and applies access rules automatically:

| | Built-in agents | Third-party agents |
|---|---|---|
| Profile fields | Full (incl. `mood_signal`, `session_data`) | Filtered (no mood/session) |
| Progress delta | ±100 per subject | ±10 per subject |

You do not need to implement any RBAC logic client-side. Just pass your key.

`knowledge-graph-server` and `content-server` require **no** `agent_key` —
concept and content data are not learner-sensitive.

---

## Available Tools

### learner-context-server (port 8001)

| Tool | Args | Returns |
|------|------|---------|
| `get_learner` | `learner_id`, `agent_key` | Learner profile dict |
| `write_progress` | `learner_id`, `agent_key`, `updates: {subject: delta}` | `{"status": "ok", "updated": {...}}` |
| `get_session` | `learner_id`, `agent_key` | Session state dict |

### knowledge-graph-server (port 8002)

| Tool | Args | Returns |
|------|------|---------|
| `get_prerequisites` | `concept` | `[{"key", "name"}]` |
| `get_next_concepts` | `learner_id` | `[{"key", "name"}]` (up to 5) |
| `get_concept` | `concept_key` | Concept node property dict |

### content-server (port 8003)

| Tool | Args | Returns |
|------|------|---------|
| `search_content` | `query`, `limit=5` | `[{"title", "content", "subject", "similarity"}]` |
| `get_course` | `course_id` | Course dict with modules list |
| `get_module` | `module_id` | Module dict with concept_key and course name |

---

## Running locally

```bash
python services/mcp_servers/learner_context_server.py   # port 8001
python services/mcp_servers/knowledge_graph_server.py   # port 8002
python services/mcp_servers/content_server.py           # port 8003
```

In production each server runs as its own pod in the `platform` namespace.
See `k8s/` for deployment manifests.
