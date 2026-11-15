"""Redis-backed agent registry for fast lookups, with Postgres fallback.
This is the ONLY place agent metadata is looked up from. Nothing else
(router.py, views.py) should query AgentRegistry or Redis directly.
"""
from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)

REGISTRY_PREFIX = 'agent_registry:'
CACHE_TTL_SECONDS = 300  # bounded — was previously None (cached forever),
                          # which meant a suspended/unhealthy agent could
                          # keep being served stale until process restart


def register_agent(agent_data: dict) -> str:
    """Register an agent in the Redis cache by slug and agent_key."""
    slug = agent_data.get('slug')
    if not slug:
        raise ValueError(
            "register_agent() called without a slug. AgentRegistry.save() "
            "auto-generates this — check the caller is passing real "
            "model data, not a hand-built dict."
        )
    agent_data.setdefault('health_status', 'unknown')
    key = f"{REGISTRY_PREFIX}{slug}"
    cache.set(key, json.dumps(agent_data), timeout=CACHE_TTL_SECONDS)

    # Index by agent_key for FastMCP RBAC validation
    agent_key = agent_data.get('api_key') or agent_data.get('agent_key') or slug
    agent_type = agent_data.get('type', 'third_party')
    cache.set(f"agent:key:{agent_key}", json.dumps({"type": agent_type, "slug": slug}), timeout=CACHE_TTL_SECONDS)

    logger.info(f"Registered agent: {key}")
    return key


def get_agent(slug: str) -> dict | None:
    """Get a live agent by slug. Redis first, Postgres fallback,
    backfills cache on miss."""
    key = f"{REGISTRY_PREFIX}{slug}"
    data = cache.get(key)
    if data:
        return json.loads(data)

    from apps.core.models import AgentRegistry
    agent = AgentRegistry.objects.filter(slug=slug, status='live').values(
        'name', 'slug', 'version', 'developer__namespace',
        'input_type', 'output_types',
        'subject_areas', 'age_groups', 'health_status', 'sessions_today',
        'k8s_service_url', 'status',
    ).first()

    if not agent:
        return None

    #It might be improved further.
    agent_dict = dict(agent)
    cache.set(key, json.dumps(agent_dict), timeout=CACHE_TTL_SECONDS)
    return agent_dict


def invalidate_agent(slug: str) -> None:
    """Call whenever an agent's status/health changes so the cache
    can't serve stale data until TTL expiry."""
    cache.delete(f"{REGISTRY_PREFIX}{slug}")


def list_agents() -> list:
    """Browse/marketplace listing — reads Postgres directly, not a
    hot path, no caching needed."""
    from apps.core.models import AgentRegistry
    return list(AgentRegistry.objects.filter(status='live').values(
        'name', 'slug', 'version', 'developer__namespace',
        'subject_areas', 'age_groups', 'health_status', 'sessions_today',
    ))


def update_health(slug: str, status: str) -> bool:
    """Update health status. Invalidates cache so get_agent() doesn't
    keep serving the old status."""
    from apps.core.models import AgentRegistry
    updated = AgentRegistry.objects.filter(slug=slug).update(health_status=status)
    if not updated:
        logger.warning(f"update_health: no agent found with slug='{slug}'")
        return False
    invalidate_agent(slug)
    return True