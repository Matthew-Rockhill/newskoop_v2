# newsroom/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django_quill.fields import QuillFormField

from .models import Story, Category, Task, AudioClip, TaskComment, TaskAttachment, Tag

class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""

    class Meta:
        model = Category
        fields = ['name', 'description', 'content_type', 'parent', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Pass "is_editing" flag when editing an existing category
        self.is_editing = kwargs.pop('is_editing', False)
        super().__init__(*args, **kwargs)

        # Add common CSS classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

        # Use a different class for checkboxes
        if 'is_active' in self.fields:
            self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

        if self.is_editing and self.instance and self.instance.pk:
            if self.instance.parent is None:
                # For a parent category, disable content_type to prevent changes.
                self.fields['content_type'].disabled = True
                self.fields['content_type'].help_text = "Content type cannot be changed after creation"
            else:
                # For subcategories, inherit content_type.
                self.fields['content_type'].widget = forms.HiddenInput()
                self.fields['content_type'].initial = self.instance.parent.content_type

        # Set up the parent queryset based on the content type.
        self.setup_parent_choices()

    def setup_parent_choices(self):
        """Limit parent choices based on the selected content type."""
        if not self.is_bound:  # Form not submitted yet.
            if self.instance and self.instance.pk and self.instance.content_type:
                content_type = self.instance.content_type
                self.setup_parent_choices_for_type(content_type)
        else:
            content_type = self.data.get('content_type')
            if content_type:
                self.setup_parent_choices_for_type(content_type)

    def setup_parent_choices_for_type(self, content_type):
        potential_parents = Category.objects.filter(
            content_type=content_type,
            level__in=[1, 2]  # Only allow top-level and parent categories
        ).exclude(is_default=True)
        if self.is_editing and self.instance and self.instance.pk:
            # Exclude self and its descendants to avoid circular relations.
            descendants = Category.objects.filter(parent=self.instance)
            exclude_ids = [self.instance.pk] + [d.pk for d in descendants]
            potential_parents = potential_parents.exclude(pk__in=exclude_ids)
        self.fields['parent'].queryset = potential_parents
        self.fields['parent'].empty_label = "None (Top Level Category)"

    def save(self, commit=True):
        # Get the instance, but don't save it yet
        instance = super().save(commit=False)
        
        # Generate slug from name
        original_slug = slugify(instance.name)
        if not instance.pk:  # New category
            instance.slug = original_slug
        elif not instance.slug:  # Existing category with no slug
            instance.slug = original_slug
        
        # Ensure uniqueness for the slug
        counter = 1
        temp_slug = instance.slug
        while Category.objects.filter(slug=temp_slug).exclude(pk=instance.pk).exists():
            temp_slug = f"{original_slug}-{counter}"
            counter += 1
        
        instance.slug = temp_slug
        
        # Now save if commit is True
        if commit:
            instance.save()
            
        return instance
    
class StoryForm(forms.ModelForm):
    """Form for creating and editing stories"""
    content = QuillFormField(required=True)
    
    class Meta:
        model = Story
        fields = ['title', 'content', 'category', 'religion_classification', 'language', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'religion_classification': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control select2-tags'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.is_new = kwargs.pop('is_new', True)
        super().__init__(*args, **kwargs)
        
        # Set the content field as required
        self.fields['content'].required = True
        
        # For interns and journalists, remove fields they shouldn't see
        if self.user and self.user.staff_role in ['INTERN', 'JOURNALIST']:
            if 'category' in self.fields:
                self.fields.pop('category', None)
            if 'religion_classification' in self.fields:
                self.fields.pop('religion_classification', None)
            # Remove tags field for non-editors
            if 'tags' in self.fields:
                self.fields.pop('tags', None)
            
        # Ensure the category field is available to editors and admins
        elif self.user and self.user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
            # Make sure the category queryset is properly set
            if 'category' in self.fields:
                self.fields['category'].queryset = Category.objects.filter(
                    level__in=[2, 3]  # Only allow parent categories and subcategories
                ).order_by('content_type', 'name')
    
    def clean_content(self):
        """Ensure content is not empty after HTML cleanup"""
        content = self.cleaned_data.get('content')
        if not content or content.strip() == '':
            raise forms.ValidationError("Content is required")
        return content
    
    def clean_tags(self):
        """Validate tags selection"""
        tags = self.cleaned_data.get('tags', [])
        
        # Validate tag count
        if len(tags) > 10:
            raise forms.ValidationError("You can select a maximum of 10 tags per story")
        
        # Validate tag combinations
        tag_names = [tag.name.lower() for tag in tags]
        
        # Check for duplicate concepts (e.g., "election" and "elections")
        for i, tag1 in enumerate(tag_names):
            for tag2 in tag_names[i+1:]:
                if tag1 in tag2 or tag2 in tag1:
                    raise forms.ValidationError(f"Tags '{tag1}' and '{tag2}' are too similar. Please choose one.")
        
        return tags
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If category is not in the form (for interns/journalists), don't validate it
        if 'category' not in self.fields:
            return cleaned_data
            
        # Ensure category is provided for others
        category = cleaned_data.get('category')
        if not category and self.user and self.user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
            self.add_error('category', "Please select a category")
            
        return cleaned_data
    
    def save(self, commit=True):
        story = super().save(commit=False)
        
        # For interns/journalists, assign default values if creating a new story
        if self.is_new and self.user and self.user.staff_role in ['INTERN', 'JOURNALIST']:
            # Use the default category for NEWS_STORIES content type
            default_category = Category.get_or_create_default('NEWS_STORIES')
            story.category = default_category
            story.religion_classification = 'GENERAL'
        
        # Always set the author when creating a new story
        if self.is_new and self.user:
            story.author = self.user
        
        if commit:
            story.save()
            
            # Save the many-to-many relationships
            if 'tags' in self.cleaned_data:
                self._save_m2m()
            
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
            'title': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50'}),
            'description': forms.Textarea(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50', 'rows': 3}),
            'task_type': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50'}),
            'priority': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50'}),
            'assigned_to': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50'}),
            'related_story': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50', 'type': 'datetime-local'}),
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
    
    # Add to forms.py
class TagForm(forms.ModelForm):
    """Form for creating and editing tags"""
    
    class Meta:
        model = Tag
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def save(self, commit=True):
        # Get the instance, but don't save it yet
        instance = super().save(commit=False)
        
        # Generate slug from name if not provided
        if not instance.slug:
            original_slug = slugify(instance.name)
            slug = original_slug
            counter = 1
            while Tag.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            instance.slug = slug
        
        # Now save if commit is True
        if commit:
            instance.save()
            
        return instance

class StoryTagsForm(forms.Form):
    """Form for managing tags on a story"""
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select tags that best describe this story's content"
    )
    
    def __init__(self, *args, **kwargs):
        self.story = kwargs.pop('story', None)
        super().__init__(*args, **kwargs)
        
        # Add validation for story status
        if self.story and self.story.status == 'PUBLISHED':
            self.fields['tags'].help_text += " (Note: Changes to published stories will be logged)"
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        
        # Validate tag count
        if len(tags) > 10:
            raise forms.ValidationError("You can select a maximum of 10 tags per story")
        
        # Validate tag combinations
        tag_names = [tag.name.lower() for tag in tags]
        
        # Check for duplicate concepts (e.g., "election" and "elections")
        for i, tag1 in enumerate(tag_names):
            for tag2 in tag_names[i+1:]:
                if tag1 in tag2 or tag2 in tag1:
                    raise forms.ValidationError(f"Tags '{tag1}' and '{tag2}' are too similar. Please choose one.")
        
        return tags