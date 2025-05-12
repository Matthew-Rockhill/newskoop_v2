# newsroom/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    """
    News categories for organizing content
    Can be a top-level (content type), parent or child category
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, 
                                   help_text="When active, this category appears in menus")
    
    # Parent-child relationship
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='children')
    
    # These are the broad content types that map to station permissions
    TYPE_CHOICES = [
        ('NEWS_STORIES', 'News Stories'),
        ('NEWS_BULLETINS', 'News Bulletins'),
        ('SPORT', 'Sport'),
        ('FINANCE', 'Finance'),
        ('SPECIALTY', 'Specialty'),
    ]
    # Required for all categories, defines the top-level group
    content_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Track category level for UI display and validation
    LEVEL_CHOICES = [
        (1, 'Content Type (Top Level)'),
        (2, 'Parent Category'),
        (3, 'Subcategory'),
    ]
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES, default=2)
    
    # Indicates if this is the default "Uncategorized" category for its content type
    is_default = models.BooleanField(default=False, 
                                    help_text="Default category for uncategorized content")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['content_type', 'level', 'name']
        constraints = [
            # Ensure only one default category per content type
            models.UniqueConstraint(
                fields=['content_type', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_category_per_type'
            )
        ]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name)
            
            # Ensure slug uniqueness by appending a number if needed
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Set level based on parent relationship
        if self.parent is None:
            if self.is_default:
                self.level = 2  # Default "Uncategorized" is a parent category
            else:
                self.level = 1  # Top level for content type categories
        elif self.parent.level == 1:
            self.level = 2  # Parent category
        else:
            self.level = 3  # Subcategory
            
        # Ensure the category inherits content_type from its parent
        if self.parent and self.parent.content_type:
            self.content_type = self.parent.content_type
            
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_default(cls, content_type):
        """Get or create the default 'Uncategorised' category for the given content type"""
        defaults = {
            'name': f"Uncategorised {dict(cls.TYPE_CHOICES)[content_type]}",
            'slug': f"uncategorised-{content_type.lower().replace('_', '-')}",
            'is_default': True,
            'level': 2,  # Parent level
            'description': f"Default category for uncategorised {dict(cls.TYPE_CHOICES)[content_type].lower()}"
        }
        
        default_category, created = cls.objects.get_or_create(
            content_type=content_type, 
            is_default=True,
            defaults=defaults
        )
        
        return default_category
        
    def get_story_count(self):
        """Get the total number of stories in this category and its children"""
        from .models import Story  # Import here to avoid circular import
        
        # Direct stories in this category
        count = Story.objects.filter(category=self).count()
        
        # Add stories from child categories
        for child in self.children.all():
            count += child.get_story_count()
            
        return count
    
    def is_deletable(self):
        """Check if category can be safely deleted"""
        from .models import Story  # Import here to avoid circular import
        
        # Can't delete if it has stories
        if Story.objects.filter(category=self).exists():
            return False
            
        # Can't delete if it has children
        if self.children.exists():
            return False
            
        # Can't delete default categories
        if self.is_default:
            return False
            
        return True
    
    def reassign_stories(self, target_category=None):
        """
        Reassign all stories from this category to another.
        If no target is specified, uses the default category for this content type.
        """
        from .models import Story  # Import here to avoid circular import
        
        if target_category is None:
            target_category = Category.get_or_create_default(self.content_type)
            
        Story.objects.filter(category=self).update(category=target_category)
        
        # Also handle child categories recursively
        for child in self.children.all():
            child.reassign_stories(target_category)

class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    tags = models.ManyToManyField('Tag', blank=True, related_name='stories')

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('REVIEW', 'In Review'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'), 
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='stories')
    RELIGION_CHOICES = [
        ('GENERAL', 'General'),
        ('CHRISTIAN', 'Christian'),
        ('MUSLIM', 'Muslim'),
    ]
    religion_classification = models.CharField(max_length=10, choices=RELIGION_CHOICES, default='GENERAL')
    LANGUAGE_CHOICES = [
        ('ENGLISH', 'English'),
        ('AFRIKAANS', 'Afrikaans'),
        ('XHOSA', 'Xhosa'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='ENGLISH')
    is_translation = models.BooleanField(default=False, help_text="Whether this story is a translation of another story")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='authored_stories')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='edited_stories', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Stories"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided.
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Story.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def publish(self, editor):
        self.status = 'PUBLISHED'
        self.published_at = timezone.now()
        self.editor = editor
        self.save()

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
        ('STORY_REVIEW', 'Story Review'),
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
    
class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, related_name='created_tags')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided.
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Tag.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
# Add to models.py
class StoryActivity(models.Model):
    """
    Track major activity on stories without storing full content revisions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # Activity types
    ACTIVITY_TYPES = [
        ('CREATE', 'Created'),
        ('EDIT', 'Edited'),
        ('STATUS', 'Status Changed'),
        ('REVIEW', 'Submitted for Review'),
        ('APPROVE', 'Approved'),
        ('PUBLISH', 'Published'),
        ('TRANSLATION', 'Translation Added'),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    
    # Additional activity data
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Story Activities"
    
    def __str__(self):
        return f"{self.get_activity_type_display()} by {self.user.get_full_name()} on {self.created_at.strftime('%Y-%m-%d')}"

# Add helper function for recording activity
def record_story_activity(story, user, activity_type, old_status=None, new_status=None, description=None):
    """Helper function to record story activity"""
    activity = StoryActivity.objects.create(
        story=story,
        user=user,
        activity_type=activity_type,
        old_status=old_status,
        new_status=new_status,
        description=description
    )
    return activity