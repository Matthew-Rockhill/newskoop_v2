# newsroom/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django_quill.fields import QuillFormField

from .models import Story, Category, Task, AudioClip, TaskComment, TaskAttachment

class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'parent', 'content_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit parent choices to parent categories only
        parent_categories = Category.objects.filter(parent__isnull=True)
        self.fields['parent'].queryset = parent_categories
        
        # If editing a parent category, remove itself from parent options
        if self.instance.pk and not self.instance.parent:
            self.fields['parent'].queryset = parent_categories.exclude(pk=self.instance.pk)
        
        # Add CSS classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        content_type = cleaned_data.get('content_type')
        
        # Validate that only parent categories have content_type
        if parent and content_type:
            raise ValidationError("Only parent categories can have a content type")
        if not parent and not content_type:
            raise ValidationError("Parent categories must have a content type")
            
        return cleaned_data

class StoryForm(forms.ModelForm):
    """Form for creating and editing stories"""
    content = QuillFormField(required=True)
    
    class Meta:
        model = Story
        fields = ['title', 'slug', 'content', 'category', 'religion_classification', 'language']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'religion_classification': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.is_new = kwargs.pop('is_new', True)
        super().__init__(*args, **kwargs)
        
        # Only editors and sub-editors can categorize
        if self.user and self.user.staff_role not in ['EDITOR', 'SUB_EDITOR']:
            self.fields['category'].disabled = True
            self.fields['category'].help_text = "Only editors and sub-editors can categorize stories"
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            title = self.cleaned_data.get('title')
            if title:
                slug = slugify(title)
            else:
                raise ValidationError("Slug cannot be generated without a title")
        
        # Check for uniqueness, but exclude the current instance when updating
        if self.is_new or self.instance.slug != slug:
            if Story.objects.filter(slug=slug).exists():
                raise ValidationError("A story with this slug already exists")
        
        return slug
    
    def save(self, commit=True):
        story = super().save(commit=False)
        
        if not story.pk:  # New story
            story.author = self.user
        
        if commit:
            story.save()
        return story

class AudioClipForm(forms.ModelForm):
    """Form for uploading audio clips"""
    
    class Meta:
        model = AudioClip
        fields = ['title', 'description', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.story = kwargs.pop('story', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            if not audio_file.name.endswith(('.mp3', '.wav', '.m4a', '.ogg')):
                raise ValidationError("Unsupported file format. Please upload an audio file (MP3, WAV, M4A, OGG).")
            
            # Add file size validation if needed
            if audio_file.size > 20 * 1024 * 1024:  # 20MB limit
                raise ValidationError("The audio file is too large (> 20MB)")
        
        return audio_file
    
    def save(self, commit=True):
        audio_clip = super().save(commit=False)
        
        if self.story:
            audio_clip.story = self.story
        
        if self.user:
            audio_clip.uploaded_by = self.user
        
        if commit:
            audio_clip.save()
        
        return audio_clip

class TaskForm(forms.ModelForm):
    """Form for creating and managing tasks"""
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'task_type', 'priority', 'assigned_to', 'related_story', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'related_story': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit assigned_to to staff users only
        from accounts.models import CustomUser
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(user_type='STAFF', is_active=True)
        
        # If this is a translation task, limit related_story to published stories
        if self.initial.get('task_type') == 'TRANSLATION':
            self.fields['related_story'].queryset = Story.objects.filter(status='PUBLISHED')
    
    def save(self, commit=True):
        task = super().save(commit=False)
        
        if self.user and not task.pk:  # New task
            task.assigned_by = self.user
        
        if commit:
            task.save()
        
        return task

class TaskCommentForm(forms.ModelForm):
    """Form for adding comments to tasks"""
    
    class Meta:
        model = TaskComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop('task', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        comment = super().save(commit=False)
        
        if self.task:
            comment.task = self.task
        
        if self.user:
            comment.author = self.user
        
        if commit:
            comment.save()
        
        return comment

class TaskAttachmentForm(forms.ModelForm):
    """Form for adding attachments to tasks"""
    
    class Meta:
        model = TaskAttachment
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop('task', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        attachment = super().save(commit=False)
        
        if self.task:
            attachment.task = self.task
        
        if self.user:
            attachment.uploaded_by = self.user
        
        if commit:
            attachment.save()
        
        return attachment

class StoryPublishForm(forms.Form):
    """Form for publishing a story"""
    confirm = forms.BooleanField(
        required=True,
        label="I confirm that this story is ready for publication",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        self.story = kwargs.pop('story', None)
        super().__init__(*args, **kwargs)
    
    def clean_confirm(self):
        confirm = self.cleaned_data.get('confirm')
        if not confirm:
            raise ValidationError("You must confirm that the story is ready for publication")
        return confirm