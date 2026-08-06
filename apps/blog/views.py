import markdown as md
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden

from apps.blog.models import Blog
from apps.blog.forms import BlogForm, RejectionForm
from apps.core.models import Developer

# ── Guard decorators ─────────────────────────────────────────────────────────

def developer_required(view_func):
    """Redirect to login if user is not a developer."""
    @login_required
    def wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'developer_profile'):
            messages.error(request, 'You need a developer account to access this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapped


def superuser_required(view_func):
    """Return 403 if user is not a superuser."""
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden(
                """
                <html><body style="font-family:sans-serif;text-align:center;padding:80px;">
                <h1 style="font-size:3rem;">403</h1>
                <h2>Access Denied</h2>
                <p>You do not have permission to access this page.</p>
                <a href="/" style="color:#f5c800;">← Go Home</a>
                </body></html>
                """
            )
        return view_func(request, *args, **kwargs)
    return wrapped



# ── Public views ─────────────────────────────────────────────────────────────

def blog_list(request):
    """Publicly visible list of all approved blog posts."""
    posts = Blog.objects.filter(status='approved').select_related('author__user')
    return render(request, 'blog/list.html', {'posts': posts})


def blog_detail(request, slug):
    """Single approved blog post rendered from Markdown."""
    post = get_object_or_404(Blog, slug=slug, status='approved')
    content_html = md.markdown(
        post.content,
        extensions=['extra', 'codehilite', 'nl2br', 'toc'],
    )
    return render(request, 'blog/detail.html', {
        'post': post,
        'content_html': content_html,
    })


# ── Developer views ───────────────────────────────────────────────────────────

@developer_required
def my_blogs(request):
    """Developer's own blog posts — all statuses."""
    developer = request.user.developer_profile
    posts = Blog.objects.filter(author=developer).order_by('-created_at')
    return render(request, 'blog/my_blogs.html', {'posts': posts})


@developer_required
def create_blog(request):
    """Create a new blog post — save as draft or submit for review."""
    developer = request.user.developer_profile
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = developer
            action = request.POST.get('form_action', 'draft')
            if action == 'submit':
                post.status = 'pending'
                msg = 'Post submitted for review!'
            else:
                post.status = 'draft'
                msg = 'Blog post saved as draft.'
            post.save()
            messages.success(request, msg)
            return redirect('developer:blog:my_blogs')
    else:
        form = BlogForm()
    return render(request, 'blog/create_edit.html', {'form': form, 'action': 'Create'})


@developer_required
def edit_blog(request, slug):
    """Edit a draft, rejected, or approved blog post."""
    developer = request.user.developer_profile
    post = get_object_or_404(Blog, slug=slug, author=developer)
    if not post.is_editable:
        messages.error(request, 'You can only edit draft, rejected, or approved posts.')
        return redirect('developer:blog:my_blogs')
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get('form_action', 'draft')
            if action == 'submit':
                post.status = 'pending'
                post.rejection_reason = ''
                msg = 'Post submitted for review!'
            else:
                post.status = 'draft'
                post.rejection_reason = ''
                msg = 'Blog post updated.'
            post.save()
            messages.success(request, msg)
            return redirect('developer:blog:my_blogs')
    else:
        form = BlogForm(instance=post)
    return render(request, 'blog/create_edit.html', {
        'form': form,
        'post': post,
        'action': 'Edit',
    })


@developer_required
def submit_blog(request, slug):
    """Submit a draft post for superuser review."""
    developer = request.user.developer_profile
    post = get_object_or_404(Blog, slug=slug, author=developer)
    if post.status != 'draft':
        messages.error(request, 'Only draft posts can be submitted for review.')
        return redirect('developer:blog:my_blogs')
    post.status = 'pending'
    post.save()
    messages.success(request, 'Post submitted for review.')
    return redirect('developer:blog:my_blogs')


@developer_required
def delete_blog(request, slug):
    """Delete a blog post."""
    developer = request.user.developer_profile
    post = get_object_or_404(Blog, slug=slug, author=developer)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Blog post deleted.')
    return redirect('developer:blog:my_blogs')


# ── Superuser / Admin panel views ─────────────────────────────────────────────

@superuser_required
def admin_blog_panel(request):
    """Superuser approval queue — shows all pending posts."""
    pending = Blog.objects.filter(status='pending').select_related('author__user')
    approved = Blog.objects.filter(status='approved').select_related('author__user')[:10]
    rejected = Blog.objects.filter(status='rejected').select_related('author__user')[:10]
    return render(request, 'blog/admin_panel.html', {
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    })


@superuser_required
def approve_blog(request, slug):
    """Approve a pending blog post."""
    post = get_object_or_404(Blog, slug=slug, status='pending')
    post.status = 'approved'
    post.published_at = timezone.now()
    post.rejection_reason = ''
    post.save()
    messages.success(request, f'"{post.title}" has been approved and published.')
    return redirect('admin_panel:blog')


@superuser_required
def reject_blog(request, slug):
    """Reject a pending blog post with a reason."""
    post = get_object_or_404(Blog, slug=slug, status='pending')
    if request.method == 'POST':
        form = RejectionForm(request.POST)
        if form.is_valid():
            post.status = 'rejected'
            post.rejection_reason = form.cleaned_data['rejection_reason']
            post.save()
            messages.success(request, f'"{post.title}" has been rejected.')
            return redirect('admin_panel:blog')
    else:
        form = RejectionForm()
    return render(request, 'blog/reject_form.html', {'form': form, 'post': post})
