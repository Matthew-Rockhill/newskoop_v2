# newsroom/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
import logging
from accounts.models import CustomUser, RadioStation

# Get logger for this module
logger = logging.getLogger('newsroom')

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
        is_new = self._state.adding
        old_name = None
        old_content_type = None
        
        if not is_new:
            try:
                old = Category.objects.get(pk=self.pk)
                old_name = old.name
                old_content_type = old.content_type
            except Category.DoesNotExist:
                pass

        try:
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
            
            # Log the action
            if is_new:
                logger.info(
                    f"New category created: {self.name} (ID: {self.id}) "
                    f"of type {self.content_type}"
                )
            else:
                changes = []
                if old_name != self.name:
                    changes.append(f"name from '{old_name}' to '{self.name}'")
                if old_content_type != self.content_type:
                    changes.append(f"content type from '{old_content_type}' to '{self.content_type}'")
                
                if changes:
                    logger.info(
                        f"Category updated: {self.name} (ID: {self.id}) - "
                        f"Changed {', '.join(changes)}"
                    )
                else:
                    logger.debug(
                        f"Category updated: {self.name} (ID: {self.id})"
                    )
                    
        except Exception as e:
            logger.error(
                f"Error saving category {self.name}: {str(e)}",
                exc_info=True
            )
            raise
    
    @classmethod
    def get_or_create_default(cls, content_type):
        """Get or create the default 'Uncategorised' category for the given content type"""
        try:
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
            
            if created:
                logger.info(
                    f"Created default category for {content_type}: "
                    f"{default_category.name} (ID: {default_category.id})"
                )
            else:
                logger.debug(
                    f"Retrieved existing default category for {content_type}: "
                    f"{default_category.name} (ID: {default_category.id})"
                )
            
            return default_category
            
        except Exception as e:
            logger.error(
                f"Error creating default category for {content_type}: {str(e)}",
                exc_info=True
            )
            raise
        
    def get_story_count(self):
        """Get the total number of stories in this category and its children"""
        try:
            from .models import Story  # Import here to avoid circular import
            
            # Direct stories in this category
            count = Story.objects.filter(category=self).count()
            
            # Add stories from child categories
            for child in self.children.all():
                count += child.get_story_count()
                
            logger.debug(
                f"Story count for category {self.name}: {count} stories"
            )
            return count
            
        except Exception as e:
            logger.error(
                f"Error getting story count for category {self.name}: {str(e)}",
                exc_info=True
            )
            return 0
    
    def is_deletable(self):
        """Check if category can be safely deleted"""
        try:
            from .models import Story  # Import here to avoid circular import
            
            # Can't delete if it has stories
            if Story.objects.filter(category=self).exists():
                logger.warning(
                    f"Cannot delete category {self.name}: has associated stories"
                )
                return False
                
            # Can't delete if it has children
            if self.children.exists():
                logger.warning(
                    f"Cannot delete category {self.name}: has child categories"
                )
                return False
                
            # Can't delete default categories
            if self.is_default:
                logger.warning(
                    f"Cannot delete category {self.name}: is a default category"
                )
                return False
                
            logger.debug(f"Category {self.name} can be safely deleted")
            return True
            
        except Exception as e:
            logger.error(
                f"Error checking if category {self.name} is deletable: {str(e)}",
                exc_info=True
            )
            return False
    
    def reassign_stories(self, target_category=None):
        """
        Reassign all stories from this category to another.
        If no target is specified, uses the default category for this content type.
        """
        try:
            from .models import Story  # Import here to avoid circular import
            
            if target_category is None:
                target_category = Category.get_or_create_default(self.content_type)
                
            story_count = Story.objects.filter(category=self).count()
            Story.objects.filter(category=self).update(category=target_category)
            
            logger.info(
                f"Reassigned {story_count} stories from category {self.name} "
                f"to {target_category.name}"
            )
            
            # Also handle child categories recursively
            for child in self.children.all():
                child.reassign_stories(target_category)
                
        except Exception as e:
            logger.error(
                f"Error reassigning stories from category {self.name}: {str(e)}",
                exc_info=True
            )
            raise

class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    tags = models.ManyToManyField('Tag', blank=True, related_name='stories')

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('REVIEW', 'In Review'),
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
    
    # Workflow fields
    is_translation = models.BooleanField(default=False, help_text="Whether this story is a translation of another story")
    translation_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                                     related_name='translations',
                                     help_text="The original story this is a translation of")
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='reviewed_stories',
                               help_text="The journalist assigned to review this story")
    
    # Author and editor fields
    author = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='authored_stories')
    editor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='edited_stories', 
                             null=True, blank=True)
    
    # Timestamps and metrics
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
        # Auto-generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.title)
            
            # Ensure slug uniqueness by appending a number if needed
            original_slug = self.slug
            counter = 1
            while Story.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # If this is a translation, ensure it's marked as such
        if self.translation_of:
            self.is_translation = True
        
        super().save(*args, **kwargs)
    
    def publish(self, published_by):
        try:
            self.status = 'PUBLISHED'
            self.published_at = timezone.now()
            self.save()
            logger.info(
                f"Story published: {self.title} (ID: {self.id})",
                extra={
                    'story_id': self.id,
                    'published_by_id': published_by.id,
                    'published_at': self.published_at
                }
            )
        except Exception as e:
            logger.error(
                f"Error publishing story: {str(e)}",
                extra={
                    'story_id': self.id,
                    'published_by_id': published_by.id,
                    'error': str(e)
                }
            )
            raise
    
    def archive(self, archived_by):
        try:
            self.status = 'ARCHIVED'
            self.save()
            logger.info(
                f"Story archived: {self.title} (ID: {self.id})",
                extra={
                    'story_id': self.id,
                    'archived_by_id': archived_by.id
                }
            )
        except Exception as e:
            logger.error(
                f"Error archiving story: {str(e)}",
                extra={
                    'story_id': self.id,
                    'archived_by_id': archived_by.id,
                    'error': str(e)
                }
            )
            raise
    
    def increment_view_count(self):
        try:
            self.view_count += 1
            self.save(update_fields=['view_count'])
            logger.debug(
                f"Story view count incremented: {self.title} (ID: {self.id})",
                extra={
                    'story_id': self.id,
                    'new_view_count': self.view_count
                }
            )
        except Exception as e:
            logger.error(
                f"Error incrementing view count: {str(e)}",
                extra={
                    'story_id': self.id,
                    'error': str(e)
                }
            )
            raise
    
    def increment_download_count(self):
        try:
            self.download_count += 1
            self.save(update_fields=['download_count'])
            logger.debug(
                f"Story download count incremented: {self.title} (ID: {self.id})",
                extra={
                    'story_id': self.id,
                    'new_download_count': self.download_count
                }
            )
        except Exception as e:
            logger.error(
                f"Error incrementing download count: {str(e)}",
                extra={
                    'story_id': self.id,
                    'error': str(e)
                }
            )
            raise
    
    def can_be_edited_by(self, user):
        try:
            can_edit = (
                user.is_staff or
                self.author == user or
                self.editor == user or
                self.reviewer == user
            )
            logger.debug(
                f"Story edit permission check: {self.title} (ID: {self.id})",
                extra={
                    'story_id': self.id,
                    'user_id': user.id,
                    'can_edit': can_edit
                }
            )
            return can_edit
        except Exception as e:
            logger.error(
                f"Error checking edit permissions: {str(e)}",
                extra={
                    'story_id': self.id,
                    'user_id': user.id,
                    'error': str(e)
                }
            )
            raise

    @property
    def get_related_stories(self):
        """Get stories related to this one based on tags and category"""
        # Get stories with common tags
        tag_related = Story.objects.filter(
            tags__in=self.tags.all()
        ).exclude(
            id=self.id
        ).distinct()

        # Get stories in the same category
        category_related = Story.objects.filter(
            category=self.category
        ).exclude(
            id=self.id
        ).distinct()

        # Combine and order by relevance (number of common tags)
        related = (tag_related | category_related).distinct()
        related = related.annotate(
            common_tags=Count('tags', filter=Q(tags__in=self.tags.all()))
        ).order_by('-common_tags', '-created_at')[:5]

        return related

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
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.title} - {self.story.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(
                    f"New audio clip created: {self.title}",
                    extra={
                        'clip_id': self.id,
                        'story_id': self.story.id,
                        'uploaded_by_id': self.uploaded_by.id,
                        'file_path': self.audio_file.path if self.audio_file else None
                    }
                )
            else:
                logger.info(
                    f"Audio clip updated: {self.title}",
                    extra={
                        'clip_id': self.id,
                        'story_id': self.story.id,
                        'uploaded_by_id': self.uploaded_by.id
                    }
                )
        except Exception as e:
            logger.error(
                f"Error saving audio clip: {str(e)}",
                extra={
                    'clip_id': self.id if not is_new else None,
                    'title': self.title,
                    'story_id': self.story.id if self.story else None,
                    'error': str(e)
                }
            )
            raise

    def delete(self, *args, **kwargs):
        try:
            clip_id = self.id
            clip_title = self.title
            story_id = self.story.id
            super().delete(*args, **kwargs)
            logger.info(
                f"Audio clip deleted: {clip_title}",
                extra={
                    'clip_id': clip_id,
                    'story_id': story_id
                }
            )
        except Exception as e:
            logger.error(
                f"Error deleting audio clip: {str(e)}",
                extra={
                    'clip_id': self.id,
                    'title': self.title,
                    'story_id': self.story.id if self.story else None,
                    'error': str(e)
                }
            )
            raise

class Task(models.Model):
    """
    Tasks for managing workflow
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Task status
    STATUS_CHOICES = [
        ('WRITE', 'Write Story'),
        ('EDIT', 'Edit Story'),
        ('REVIEW', 'Review Story'),
        ('TRANSLATE', 'Translate Story'),
        ('RECORD', 'Record Audio'),
        ('OTHER', 'Other'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WRITE')
    
    # Task type
    TYPE_CHOICES = [
        ('WRITE', 'Write Story'),
        ('EDIT', 'Edit Story'),
        ('REVIEW', 'Review Story'),
        ('TRANSLATE', 'Translate Story'),
        ('RECORD', 'Record Audio'),
        ('OTHER', 'Other'),
    ]
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='WRITE')
    
    # Priority
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Assignments
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, 
                                  related_name='assigned_tasks')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.PROTECT, 
                                  related_name='tasks')
    
    # Related content
    related_story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        old_instance = None
        
        if not is_new:
            try:
                old_instance = Task.objects.get(pk=self.pk)
                old_status = old_instance.status
            except Task.DoesNotExist:
                pass
        
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(
                    f"New task created: {self.title}",
                    extra={
                        'task_id': self.id,
                        'task_type': self.task_type,
                        'priority': self.priority,
                        'assigned_by_id': self.assigned_by.id,
                        'assigned_to_id': self.assigned_to.id,
                        'story_id': self.related_story.id if self.related_story else None
                    }
                )
            else:
                changes = []
                if old_status != self.status:
                    changes.append(f"status: {old_status} -> {self.status}")
                if old_instance and old_instance.title != self.title:
                    changes.append(f"title: {old_instance.title} -> {self.title}")
                if old_instance and old_instance.priority != self.priority:
                    changes.append(f"priority: {old_instance.priority} -> {self.priority}")
                if old_instance and old_instance.assigned_to != self.assigned_to:
                    changes.append(f"assigned_to: {old_instance.assigned_to.id} -> {self.assigned_to.id}")
                
                if changes:
                    logger.info(
                        f"Task updated: {self.title}",
                        extra={
                            'task_id': self.id,
                            'changes': changes,
                            'assigned_by_id': self.assigned_by.id
                        }
                    )
        except Exception as e:
            logger.error(
                f"Error saving task: {str(e)}",
                extra={
                    'task_id': self.id if not is_new else None,
                    'title': self.title,
                    'error': str(e)
                }
            )
            raise
    
    def complete(self):
        """Mark task as completed"""
        try:
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
            self.save()
            logger.info(
                f"Task completed: {self.title}",
                extra={
                    'task_id': self.id,
                    'completed_at': self.completed_at,
                    'assigned_to_id': self.assigned_to.id
                }
            )
        except Exception as e:
            logger.error(
                f"Error completing task: {str(e)}",
                extra={
                    'task_id': self.id,
                    'title': self.title,
                    'error': str(e)
                }
            )
            raise

    def cancel(self):
        try:
            self.status = 'CANCELLED'
            self.save()
            logger.info(
                f"Task cancelled: {self.title}",
                extra={
                    'task_id': self.id,
                    'assigned_by_id': self.assigned_by.id
                }
            )
        except Exception as e:
            logger.error(
                f"Error cancelling task: {str(e)}",
                extra={
                    'task_id': self.id,
                    'title': self.title,
                    'error': str(e)
                }
            )
            raise
    
    def delete(self, *args, **kwargs):
        try:
            task_id = self.id
            task_title = self.title
            story_id = self.related_story.id if self.related_story else None
            super().delete(*args, **kwargs)
            logger.info(
                f"Task deleted: {task_title}",
                extra={
                    'task_id': task_id,
                    'story_id': story_id
                }
            )
        except Exception as e:
            logger.error(
                f"Error deleting task: {str(e)}",
                extra={
                    'task_id': self.id,
                    'title': self.title,
                    'error': str(e)
                }
            )
            raise

class TaskAttachment(models.Model):
    """
    Files attached to tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/%d/')
    title = models.CharField(max_length=200)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(
                    f"New task attachment added: {self.title} (ID: {self.id}) "
                    f"to task '{self.task.title}' by {self.uploaded_by.email}"
                )
            else:
                logger.debug(
                    f"Task attachment updated: {self.title} (ID: {self.id})"
                )
                
        except Exception as e:
            logger.error(
                f"Error saving task attachment {self.title}: {str(e)}",
                exc_info=True
            )
            raise

    def delete(self, *args, **kwargs):
        try:
            attachment_title = self.title
            task_title = self.task.title
            super().delete(*args, **kwargs)
            logger.info(
                f"Task attachment deleted: {attachment_title} "
                f"from task '{task_title}'"
            )
        except Exception as e:
            logger.error(
                f"Error deleting task attachment {self.title}: {str(e)}",
                exc_info=True
            )
            raise

class TaskComment(models.Model):
    """
    Comments on tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(
                    f"New task comment added: by {self.author.email} "
                    f"on task '{self.task.title}'"
                )
            else:
                logger.debug(
                    f"Task comment updated: by {self.author.email} "
                    f"on task '{self.task.title}'"
                )
                
        except Exception as e:
            logger.error(
                f"Error saving task comment by {self.author.email}: {str(e)}",
                exc_info=True
            )
            raise

    def delete(self, *args, **kwargs):
        try:
            author_email = self.author.email
            task_title = self.task.title
            super().delete(*args, **kwargs)
            logger.info(
                f"Task comment deleted: by {author_email} "
                f"from task '{task_title}'"
            )
        except Exception as e:
            logger.error(
                f"Error deleting task comment by {self.author.email}: {str(e)}",
                exc_info=True
            )
            raise

class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_tags')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(
                    f"New tag created: {self.name}",
                    extra={
                        'tag_id': self.id,
                        'created_by_id': self.created_by.id if self.created_by else None
                    }
                )
            else:
                logger.info(
                    f"Tag updated: {self.name}",
                    extra={
                        'tag_id': self.id,
                        'created_by_id': self.created_by.id if self.created_by else None
                    }
                )
        except Exception as e:
            logger.error(
                f"Error saving tag: {str(e)}",
                extra={
                    'tag_id': self.id if not is_new else None,
                    'name': self.name,
                    'error': str(e)
                }
            )
            raise
    
    def delete(self, *args, **kwargs):
        try:
            tag_id = self.id
            tag_name = self.name
            super().delete(*args, **kwargs)
            logger.info(
                f"Tag deleted: {tag_name}",
                extra={
                    'tag_id': tag_id
                }
            )
        except Exception as e:
            logger.error(
                f"Error deleting tag: {str(e)}",
                extra={
                    'tag_id': self.id,
                    'name': self.name,
                    'error': str(e)
                }
            )
            raise
    
    def validate_story_tag_count(self, story):
        """Validate that adding this tag won't exceed the story's tag limit"""
        if story.tags.count() >= 10:
            raise ValidationError("A story can have a maximum of 10 tags")
    
    @property
    def story_count(self):
        """Get the number of stories using this tag"""
        return self.stories.count()

# Add to models.py
class StoryActivity(models.Model):
    """
    Track major activity on stories without storing full content revisions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    
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

#helper function for recording activity
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