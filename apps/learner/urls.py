from django.urls import path
from . import views

app_name = 'learner'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('agents/<slug:agent_slug>/', views.AgentSessionView.as_view(), name='agent-session'),
    path('upload-image/', views.LearnerImageUploadView.as_view(), name='learner-image-upload'),
    path('api/context/', views.learner_context_api, name='learner_context_api'),
]
