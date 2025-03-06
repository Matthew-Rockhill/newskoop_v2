# newsroom/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

class Category(models.Model):
    """
    News categories for organizing content
    Can be a parent or child category
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # If parent is null, this is a top-level/parent category
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # These are the broad parent categories that map to station permissions
    TYPE_CHOICES = [
        ('NEWS_STORIES', 'News Stories'),
        ('NEWS_BULLETINS', 'News Bulletins'),
        ('SPORT', 'Sport'),
        ('FINANCE', 'Finance'),
        ('SPECIALTY', 'Specialty'),
    ]
    # Only set on parent categories, used for access control
    content_type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure content_type is only set on parent categories
        if not self.parent and not self.content_type:
            raise ValidationError("Parent categories must have a content type")
        if self.parent:
            self.content_type = None
        super().save(*args, **kwargs)

class Story(models.Model):
    """
    The main content model for all types of stories
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    
    # Story status
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('REVIEW', 'In Review'),
        ('APPROVED', 'Approved'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    
    # Classification
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='stories')
    
    # Religious content classification
    RELIGION_CHOICES = [
        ('GENERAL', 'General'),
        ('CHRISTIAN', 'Christian'),
        ('MUSLIM', 'Muslim'),
    ]
    religion_classification = models.CharField(max_length=10, choices=RELIGION_CHOICES, default='GENERAL')
    
    # Language tracking
    LANGUAGE_CHOICES = [
        ('ENGLISH', 'English'),
        ('AFRIKAANS', 'Afrikaans'),
        ('XHOSA', 'Xhosa'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='ENGLISH')
    
    # Translation tracking
    is_translation = models.BooleanField(default=False)
    translated_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                      related_name='translations')
    
    # Attribution and metadata
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                              related_name='authored_stories')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                              related_name='edited_stories', null=True, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Analytics
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Stories"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def publish(self, editor):
        """Publish the story by changing status and recording publish time"""
        self.status = 'PUBLISHED'
        self.published_at = timezone.now()
        self.editor = editor
        self.save()
    
    def get_audio_clips(self):
        """Return all audio clips for this story"""
        return self.audio_clips.all()

class AudioClip(models.Model):
    """
    Audio clips attached to stories
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # File
    audio_file = models.FileField(upload_to='audio_clips/%Y/%m/%d/')
    duration = models.DurationField(null=True, blank=True)  # Store duration in seconds
    
    # Relationship
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='audio_clips')
    
    # Metadata
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.title} - {self.story.title}"

class Task(models.Model):
    """
    Tasks for managing workflow
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Task status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('REVIEW', 'In Review'), 
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    
    # Task type
    TYPE_CHOICES = [
        ('STORY_WRITING', 'Story Writing'),
        ('STORY_EDITING', 'Story Editing'),
        ('FOLLOW_UP', 'Follow Up'),
        ('TRANSLATION', 'Translation'),
        ('AUDIO_RECORDING', 'Audio Recording'),
        ('OTHER', 'Other'),
    ]
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='STORY_WRITING')
    
    # Priority
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Assignments
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                                  related_name='assigned_tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                                  related_name='tasks')
    
    # Related content
    related_story = models.ForeignKey(Story, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='tasks')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def complete(self):
        """Mark task as completed"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save()

class TaskAttachment(models.Model):
    """
    Files attached to tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/%d/')
    title = models.CharField(max_length=200)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class TaskComment(models.Model):
    """
    Comments on tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"

class StoryRevision(models.Model):
    """
    Track revisions to stories
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='revisions')
    content = models.TextField()
    revision_number = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-revision_number']
        unique_together = ['story', 'revision_number']
    
    def __str__(self):
        return f"Revision {self.revision_number} of {self.story.title}"