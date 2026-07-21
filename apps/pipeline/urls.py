from django.urls import path
from . import views

app_name = 'pipeline'

urlpatterns = [
    path('webhook/', views.pipeline_webhook, name='webhook'),
    path('<slug:slug>/status/', views.agent_pipeline_status, name='status'),
    path('<slug:slug>/step-update/', views.pipeline_step_update, name='step_update'),
    path('<slug:slug>/events/', views.pipeline_events_stream, name='events_stream'),
]
