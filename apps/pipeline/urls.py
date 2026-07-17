from django.urls import path
from . import views

app_name = 'pipeline'

urlpatterns = [
    path('webhook/', views.pipeline_webhook, name='webhook'),
    path('<slug:slug>/status/', views.agent_pipeline_status, name='status'),
]
