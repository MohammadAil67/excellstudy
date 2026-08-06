from django import forms
from apps.blog.models import Blog


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content', 'excerpt', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Blog post title',
            }),
            'content': forms.Textarea(attrs={
                'id': 'blog-content-editor',
                'class': 'form-textarea',
                'rows': 20,
                'placeholder': 'Write your blog post in Markdown...',
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Short summary (optional — auto-generated if left blank)',
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
        }
        labels = {
            'cover_image': 'Cover Image (optional)',
            'excerpt': 'Excerpt (optional)',
        }


class RejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Explain why this post is being rejected...',
        }),
        label='Rejection Reason',
    )
