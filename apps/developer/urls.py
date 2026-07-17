from django.urls import path
from . import views

app_name = 'developer'

urlpatterns = [
    path('', views.MyAgentsListView.as_view(), name='portal'),
    path('register-agent/', views.RegisterAgentView.as_view(), name='register-agent'),
    path('my-agents/', views.MyAgentsListView.as_view(), name='my-agents'),
    path('api/agents/check-registration/', views.CheckRegistrationView.as_view(), name='check-registration'),
    path('pipeline/<str:job_id>/', views.pipeline_status, name='pipeline_status'),
]
