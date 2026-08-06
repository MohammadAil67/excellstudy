from django.urls import path, include
from . import views
from apps.blog.urls import developer_blog_urlpatterns

app_name = 'developer'

urlpatterns = [
    path('', views.MyAgentsListView.as_view(), name='portal'),
    path('register-agent/', views.RegisterAgentView.as_view(), name='register-agent'),
    path('my-agents/', views.MyAgentsListView.as_view(), name='my-agents'),
    path('api/agents/check-registration/', views.CheckRegistrationView.as_view(), name='check-registration'),
    path('pipeline/<str:job_id>/', views.pipeline_status, name='pipeline_status'),
    path('guides/creating-an-agent/', views.creation_guide, name='creation-guide'),
    path('guides/deploy/', views.deploy_guide, name='deploy-guide'),
    path('settings/github-username/', views.UpdateGithubUsernameView.as_view(), name='update-github-username'),
    path('agents/<slug:agent_slug>/toggle-status/', views.ToggleAgentStatusView.as_view(), name='toggle-agent-status'),
    path('agents/<slug:agent_slug>/trigger/', views.TriggerPipelineView.as_view(), name='trigger-pipeline'),
    path('agents/<slug:agent_slug>/delete/', views.DeleteAgentView.as_view(), name='delete-agent'),

    # Blog management
    path('blog/', include((developer_blog_urlpatterns, 'blog'))),
]
