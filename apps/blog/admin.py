from django.contrib import admin
from apps.blog.models import Blog
from django.utils import timezone


@admin.action(description='Approve selected posts')
def approve_posts(modeladmin, request, queryset):
    queryset.filter(status='pending').update(status='approved', published_at=timezone.now())


@admin.action(description='Reject selected posts')
def reject_posts(modeladmin, request, queryset):
    queryset.filter(status='pending').update(status='rejected')


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display  = ('title', 'author', 'status', 'created_at', 'published_at')
    list_filter   = ('status',)
    search_fields = ('title', 'author__user__username')
    readonly_fields = ('slug', 'created_at', 'updated_at', 'published_at')
    actions = [approve_posts, reject_posts]
