from django.urls import path
from apps.agents import views

urlpatterns = [
    path("", views.agent_list, name="agent-list"),
    path("<slug:agent_slug>/invoke/", views.invoke_agent, name="agent-invoke"),
    path("<slug:slug>/health/", views.agent_health, name="agent-health"),
]