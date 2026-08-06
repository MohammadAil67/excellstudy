import uuid
from django.db import models
from django.utils.text import slugify
from apps.core.models import Developer


class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('pending',  'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    title            = models.CharField(max_length=200)
    slug             = models.SlugField(max_length=250, unique=True, editable=False)
    author           = models.ForeignKey(
                           Developer, on_delete=models.CASCADE, related_name='blogs'
                       )
    content          = models.TextField(help_text='Write in Markdown format.')
    excerpt          = models.TextField(
                           blank=True,
                           help_text='Short summary shown in the blog list. Leave blank to auto-generate.'
                       )
    cover_image      = models.ImageField(
                           upload_to='blog_covers/',
                           blank=True,
                           null=True,
                           help_text='Optional header image file.'
                       )
    status           = models.CharField(
                           max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True
                       )
    rejection_reason = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    published_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'

    def __str__(self):
        return f'{self.title} — {self.author}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        # Auto-generate excerpt from content if not provided
        if not self.excerpt and self.content:
            # Take first 200 chars of content, strip markdown symbols
            plain = self.content.replace('#', '').replace('*', '').replace('_', '').strip()
            self.excerpt = plain[:200] + ('...' if len(plain) > 200 else '')
        super().save(*args, **kwargs)

    @property
    def is_editable(self):
        """Developer can edit draft, rejected, or approved posts."""
        return self.status in ('draft', 'rejected', 'approved')

    @property
    def can_submit(self):
        """Only draft posts can be submitted for review."""
        return self.status == 'draft'
