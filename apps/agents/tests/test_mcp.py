import pytest
import respx
import httpx
from django.contrib.auth.models import User
from apps.core.models import Developer, AgentRegistry
from apps.agents.registry import get_agent, register_agent, update_health
from apps.agents.router import forward_to_agent


@pytest.mark.django_db
def test_get_agent_from_db():
    # Setup test user and developer profile
    user = User.objects.create_user(username="testdev", password="password")
    developer = Developer.objects.create(user=user)

    agent_live = AgentRegistry.objects.create(
        name="BioHelper",
        developer=developer,
        input_type="text_with_units",
        output_types=["text"],
        subject_areas=["biology"],
        status="live",
        health_status="healthy",
    )

    # Assert fallback DB lookup by slug works
    retrieved = get_agent(agent_live.slug)
    assert retrieved is not None
    assert retrieved['name'] == "BioHelper"
    assert retrieved['status'] == "live"


@pytest.mark.django_db
def test_register_agent_and_update_health():
    user = User.objects.create_user(username="testdev", password="password")
    developer = Developer.objects.create(user=user)

    agent = AgentRegistry.objects.create(
        name="ChemHelper",
        developer=developer,
        input_type="text_with_units",
        output_types=["text"],
        subject_areas=["chemistry"],
        status="live",
        health_status="unknown",
    )

    # Test updating health status
    update_health(agent.slug, "healthy")
    agent.refresh_from_db()
    assert agent.health_status == "healthy"


@pytest.mark.asyncio
@respx.mock
async def test_forward_to_agent_success():
    agent_data = {
        "name": "BioHelper",
        "slug": "dev-testdev-biohelper",
        "k8s_service_url": "http://biohelper-service.local"
    }

    respx.post("http://biohelper-service.local/invoke").mock(
        return_value=httpx.Response(200, json={"response": "Hello Biology"})
    )

    payload = {"value": "biology questions"}
    context = {"learner_id": "learner-1"}
    
    result = await forward_to_agent(
        agent=agent_data,
        input_payload=payload,
        learner_context=context,
        request_id="req-123"
    )

    assert result["status_code"] == 200
    assert result["body"] == {"response": "Hello Biology"}
