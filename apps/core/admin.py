from django.contrib import admin
from .models import Learner, Developer, AgentRegistry, Course, Module, LearnerProgress


@admin.register(Learner)
class LearnerAdmin(admin.ModelAdmin):
    list_display = ['user', 'age', 'grade', 'learning_style', 'mood_signal']
    list_filter = ['learning_style', 'mood_signal']
    search_fields = ['user__username', 'user__email']


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display = ['namespace', 'user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['namespace', 'user__username']
    readonly_fields = ['namespace', 'api_key']


@admin.register(AgentRegistry)
class AgentRegistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'version', 'developer', 'status', 'health_status', 'sessions_today']
    list_filter = ['status', 'health_status', 'input_type']
    search_fields = ['name', 'slug', 'developer__namespace']
    readonly_fields = ['slug']
    filter_horizontal = ('related_courses',)
    prepopulated_fields = {}  # slug is auto-derived, not prepopulated


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'age_group_min', 'age_group_max']
    list_filter = ['subject']
    search_fields = ['title']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'concept_key']
    list_filter = ['course']


@admin.register(LearnerProgress)
class LearnerProgressAdmin(admin.ModelAdmin):
    list_display = ['learner', 'module', 'score', 'completed_at', 'agent_used']
    list_filter = ['completed_at']
    search_fields = ['learner__user__username']
