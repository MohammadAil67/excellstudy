from django.urls import path
from apps.agents import views

urlpatterns = [
    path("agents/", views.agent_list, name="agent-list"),
    path("agents/<slug:agent_slug>/invoke/", views.invoke_agent, name="agent-invoke"),
    path("agents/<slug:slug>/health/", views.agent_health, name="agent-health"),
]