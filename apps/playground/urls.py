from django.urls import path
from . import views

app_name = 'playground'

urlpatterns = [
    path('', views.canvas, name='canvas'),
    path('api/compile/', views.compile_graph_view, name='compile'),
]
