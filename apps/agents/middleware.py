import time
import uuid
import json
import logging
import datetime
import threading
import inspect
from django.conf import settings
import redis

logger = logging.getLogger("agents.invoke_middleware")

REDIS_URL = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as ex:
    logger.exception(f"Could not connect to Redis at {REDIS_URL}: {str(ex)}")
    redis_client = None


def _write_log_to_redis(key: str, value: str):
    if redis_client is None:
        return
    try:
        redis_client.setex(key, 86400, value)
    except Exception as e:
        logger.error(f"Failed writing log entry to Redis for key {key}: {str(e)}")


class AgentInvokeLoggingMiddleware:
    """
    Logs every learner -> agent invocation for observability.
    This is NOT the MCP layer — it wraps the plain-HTTP relay path
    (views.invoke_agent). MCP servers (learner_context, knowledge_graph,
    content) have their own separate logging inside services/mcp_servers/,
    unrelated to this middleware.
    """

    # Matches /api/v1/agents/<any-slug>/invoke/
    TRACKED_PATH_PREFIX = "/api/v1/agents/"
    TRACKED_PATH_SUFFIX = "/invoke/"

    def __init__(self, get_response):
        self.get_response = get_response
        self.is_async = inspect.iscoroutinefunction(get_response)

    def _should_track(self, request) -> bool:
        return (
            request.path.startswith(self.TRACKED_PATH_PREFIX)
            and request.path.endswith(self.TRACKED_PATH_SUFFIX)
        )

    def _build_log_entry(self, request, request_id, duration_ms, status_code) -> dict:
        status = getattr(request, "invoke_status", "success")
        if status_code >= 400:
            status = "timeout" if status_code == 504 else "error"

        return {
            "request_id": request_id,
            "agent_name": getattr(request, "invoke_agent_name", "unknown-agent"),
            "learner_id": getattr(request, "invoke_learner_id", "unknown-learner"),
            "duration_ms": duration_ms,
            "status": status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def _persist_log(self, request_id: str, log_entry: dict):
        payload = json.dumps(log_entry)
        # Always log synchronously first — this line survives even if
        # the Redis write thread never completes (process kill, etc.)
        logger.info(f"agent invoke log: {payload}")

        # Redis write happens on a best-effort background thread —
        # acceptable to lose under a hard process kill, since the
        # logger.info() above already captured it in stdout/log
        # aggregation, which should be the durable source of truth.
        t = threading.Thread(target=_write_log_to_redis, args=(f"agent_invoke_log:{request_id}", payload))
        t.start()

    def __call__(self, request):
        if self.is_async:
            return self.__acall__(request)

        if not self._should_track(request):
            return self.get_response(request)

        request_id = str(uuid.uuid4())
        request.request_id = request_id
        request.invoke_agent_name = "unknown-agent"
        request.invoke_learner_id = "unknown-learner"
        request.invoke_status = "success"

        start_time = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start_time) * 1000)

        log_entry = self._build_log_entry(request, request_id, duration_ms, response.status_code)
        self._persist_log(request_id, log_entry)

        return response

    async def __acall__(self, request):
        if not self._should_track(request):
            return await self.get_response(request)

        request_id = str(uuid.uuid4())
        request.request_id = request_id
        request.invoke_agent_name = "unknown-agent"
        request.invoke_learner_id = "unknown-learner"
        request.invoke_status = "success"

        start_time = time.time()
        response = await self.get_response(request)
        duration_ms = int((time.time() - start_time) * 1000)

        log_entry = self._build_log_entry(request, request_id, duration_ms, response.status_code)
        self._persist_log(request_id, log_entry)

        return response