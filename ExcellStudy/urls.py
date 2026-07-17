"""
URL configuration for ExcellStudy project.
All app routes registered with proper namespacing.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from apps.core import views as core_views


def home(request):
    """Render the landing page."""
    return render(request, 'landing.html')


urlpatterns = [
    # Root redirect
    path('', home, name='home'),

    # Auth
    path('login/', core_views.login_view, name='login'),
    path('signup/', core_views.signup_view, name='signup'),
    path('logout/', core_views.logout_view, name='logout'),

    # Admin
    path('admin/', admin.site.urls),

    # Frontend views
    path('learner/', include('apps.learner.urls')),
    path('developer/', include('apps.developer.urls')),
    path('playground/', include('apps.playground.urls')),
    path('marketplace/', include('apps.marketplace.urls')),

    # API endpoints
    path('api/v1/agents/', include('apps.agents.urls')),
    path('api/v1/pipeline/', include('apps.pipeline.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
