from django.urls import path
from apps.blog import views

# Public blog URLs — namespace: 'blog'
blog_urlpatterns = [
    path('', views.blog_list, name='list'),
    path('<slug:slug>/', views.blog_detail, name='detail'),
]

# Developer blog management URLs — included under /developer/blog/
developer_blog_urlpatterns = [
    path('', views.my_blogs, name='my_blogs'),
    path('create/', views.create_blog, name='create_blog'),
    path('<slug:slug>/edit/', views.edit_blog, name='edit_blog'),
    path('<slug:slug>/submit/', views.submit_blog, name='submit_blog'),
    path('<slug:slug>/delete/', views.delete_blog, name='delete_blog'),
]

# Admin panel URLs — namespace: 'admin_panel'
admin_panel_urlpatterns = [
    path('blog/', views.admin_blog_panel, name='blog'),
    path('blog/<slug:slug>/approve/', views.approve_blog, name='approve_blog'),
    path('blog/<slug:slug>/reject/', views.reject_blog, name='reject_blog'),
]
