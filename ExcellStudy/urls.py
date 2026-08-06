"""
URL configuration for ExcellStudy project.
All app routes registered with proper namespacing.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from apps.core import views as core_views
from apps.blog.urls import blog_urlpatterns, admin_panel_urlpatterns


def home(request):
    """Render the landing page with real database statistics and live agents."""
    from apps.core.models import Learner, AgentRegistry, Course
    
    total_learners = Learner.objects.count()
    live_agents_qs = AgentRegistry.objects.filter(status='live').select_related('developer', 'developer__user')
    total_agents = live_agents_qs.count()
    
    # Calculate unique subjects from courses and live agents
    subjects = set(Course.objects.values_list('subject', flat=True).distinct())
    for agent in live_agents_qs:
        if isinstance(agent.subject_areas, list):
            subjects.update(agent.subject_areas)
    total_subjects = len(subjects)

    # Format numbers
    if total_learners >= 1000:
        learners_display = f"{total_learners/1000:.1f}K"
    else:
        learners_display = str(total_learners)

    agents_display = f"{total_agents}+" if total_agents > 0 else "0"

    featured_agents = list(live_agents_qs[:6])

    context = {
        'learners_display': learners_display,
        'agents_display': agents_display,
        'total_subjects': total_subjects,
        'featured_agents': featured_agents,
    }
    return render(request, 'landing.html', context)


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

    # Blog
    path('blog/', include((blog_urlpatterns, 'blog'))),

    # Admin panel (superuser only)
    path('admin-panel/', include((admin_panel_urlpatterns, 'admin_panel'))),
]

from django.conf import settings
from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
