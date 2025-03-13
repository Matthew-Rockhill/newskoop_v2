import os
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.text import slugify
from django.http import HttpResponseForbidden, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.forms import inlineformset_factory

from accounts.models import CustomUser
from .models import (
    Story, Category, AudioClip, Task, TaskAttachment, 
    TaskComment, StoryRevision
)
from .forms import (
    StoryForm, CategoryForm, AudioClipForm, TaskForm, 
    TaskCommentForm, TaskAttachmentForm, StoryPublishForm
)
from .permissions import (
    staff_required, editor_required, publishing_rights_required,
    can_edit_story, can_manage_task, can_manage_categories, has_radio_access
)

# Create an inline formset for AudioClip linked to a Story.
AudioClipFormSet = inlineformset_factory(
    Story,
    AudioClip,
    form=AudioClipForm,
    extra=1,          # Always display at least one blank form.
    can_delete=True   # Allow deletion of existing clips.
)

@login_required
def dashboard(request):
    """Main dashboard for the newsroom app"""
    context = {}
    
    if request.user.user_type == CustomUser.UserType.STAFF:
        # Common data for all staff
        context['recent_stories'] = Story.objects.order_by('-created_at')[:5]
        context['assigned_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status__in=['PENDING', 'IN_PROGRESS', 'REVIEW']
        ).order_by('due_date')[:5]
        context['story_count'] = Story.objects.count()
        context['draft_count'] = Story.objects.filter(status='DRAFT').count()
        context['published_count'] = Story.objects.filter(status='PUBLISHED').count()
        
        # My stories stats
        my_stories = Story.objects.filter(author=request.user)
        context['my_story_count'] = my_stories.count()
        context['my_draft_count'] = my_stories.filter(status='DRAFT').count()
        context['my_published_count'] = my_stories.filter(status='PUBLISHED').count()
        context['my_review_count'] = my_stories.filter(status='REVIEW').count()
        
        # Last updated story
        last_updated_story = my_stories.order_by('-updated_at').first()
        if last_updated_story:
            days_since = (timezone.now() - last_updated_story.updated_at).days
            context['last_updated_days'] = days_since
            
        # Pending tasks stats
        context['pending_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status='PENDING'
        ).count()
        context['in_progress_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status='IN_PROGRESS'
        ).count()
        context['tasks_created'] = Task.objects.filter(
            assigned_by=request.user
        ).count()
        
        # For editors and sub-editors
        if request.user.staff_role in ['EDITOR', 'SUPERADMIN', 'ADMIN', 'SUB_EDITOR']:
            context['awaiting_review'] = Story.objects.filter(status='REVIEW').count()
            context['all_pending_tasks'] = Task.objects.filter(status='PENDING').count()
            context['stories_for_review'] = Story.objects.filter(status='REVIEW').order_by('-created_at')[:5]
            
        # For journalists and interns
        if request.user.staff_role in ['INTERN', 'JOURNALIST']:
            context['my_draft_stories'] = my_stories.filter(status='DRAFT').order_by('-updated_at')[:5]
    
    elif request.user.user_type == CustomUser.UserType.RADIO:
        # [Radio station user logic remains unchanged]
        station = request.user.radio_station
        if station:
            query = Q(status='PUBLISHED')
            language_filter = Q()
            if station.access_english:
                language_filter |= Q(language='ENGLISH')
            if station.access_afrikaans:
                language_filter |= Q(language='AFRIKAANS')
            if station.access_xhosa:
                language_filter |= Q(language='XHOSA')
            if language_filter:
                query &= language_filter
                
            category_filter = Q()
            if station.access_news_stories:
                news_categories = Category.objects.filter(
                    Q(content_type='NEWS_STORIES') | 
                    Q(parent__content_type='NEWS_STORIES')
                )
                category_filter |= Q(category__in=news_categories)
            if station.access_news_bulletins:
                bulletin_categories = Category.objects.filter(
                    Q(content_type='NEWS_BULLETINS') | 
                    Q(parent__content_type='NEWS_BULLETINS')
                )
                category_filter |= Q(category__in=bulletin_categories)
            if station.access_sport:
                sport_categories = Category.objects.filter(
                    Q(content_type='SPORT') | 
                    Q(parent__content_type='SPORT')
                )
                category_filter |= Q(category__in=sport_categories)
            if station.access_finance:
                finance_categories = Category.objects.filter(
                    Q(content_type='FINANCE') | 
                    Q(parent__content_type='FINANCE')
                )
                category_filter |= Q(category__in=finance_categories)
            if station.access_specialty:
                specialty_categories = Category.objects.filter(
                    Q(content_type='SPECIALTY') | 
                    Q(parent__content_type='SPECIALTY')
                )
                category_filter |= Q(category__in=specialty_categories)
            if category_filter:
                query &= category_filter
                
            religion_filter = Q(religion_classification='GENERAL')
            if station.religion_access == 'GENERAL_PLUS_CHRISTIAN':
                religion_filter |= Q(religion_classification='CHRISTIAN')
            elif station.religion_access == 'GENERAL_PLUS_MUSLIM':
                religion_filter |= Q(religion_classification='MUSLIM')
            query &= religion_filter
            
            context['recent_stories'] = Story.objects.filter(query).order_by('-published_at')[:10]
            context['story_count'] = Story.objects.filter(query).count()
    
    return render(request, 'newsroom/dashboard.html', context)

@login_required
def story_list(request):
    """List stories with filtering options and role-based access"""
    stories = Story.objects.all().select_related('author', 'category', 'editor')
    
    if request.user.user_type == CustomUser.UserType.RADIO:
        station = request.user.radio_station
        if station:
            stories = stories.filter(status='PUBLISHED')
    else:
        # For interns and journalists, show only their own stories.
        if request.user.staff_role in ['INTERN', 'JOURNALIST']:
            stories = stories.filter(author=request.user)
    
    # Apply additional filters (status, category, language, search query)
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    language_filter = request.GET.get('language')
    search_query = request.GET.get('q')
    
    if status_filter:
        stories = stories.filter(status=status_filter)
    if category_filter:
        try:
            cat = Category.objects.get(id=category_filter)
            if cat.parent is None:
                subcategories = cat.children.all()
                stories = stories.filter(Q(category=cat) | Q(category__in=subcategories))
            else:
                stories = stories.filter(category=cat)
        except Category.DoesNotExist:
            pass
    if language_filter:
        stories = stories.filter(language=language_filter)
    if search_query:
        stories = stories.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(author__first_name__icontains=search_query) |
            Q(author__last_name__icontains=search_query)
        )
    
    paginator = Paginator(stories.order_by('-created_at'), 15)
    page_number = request.GET.get('page')
    stories_page = paginator.get_page(page_number)
    
    context = {
        'stories': stories_page,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'language_filter': language_filter,
        'search_query': search_query
    }
    
    return render(request, 'newsroom/story/story_list.html', context)

@login_required
def story_detail(request, story_id):
    """Show details of a story"""
    story = get_object_or_404(Story, id=story_id)
    if request.user.user_type == CustomUser.UserType.RADIO:
        if not has_radio_access(request.user, story):
            return HttpResponseForbidden("You don't have access to this content")
    audio_clips = story.audio_clips.all()
    tasks = None
    if request.user.user_type == CustomUser.UserType.STAFF:
        tasks = Task.objects.filter(related_story=story)
    revisions = None
    if request.user.user_type == CustomUser.UserType.STAFF:
        revisions = story.revisions.all().order_by('-revision_number')
    context = {
        'story': story,
        'audio_clips': audio_clips,
        'tasks': tasks,
        'revisions': revisions,
    }
    return render(request, 'newsroom/story/story_detail.html', context)

@staff_required
def story_create(request):
    """Create a new story with drag-and-drop audio upload"""
    if request.method == 'POST':
        story_form = StoryForm(request.POST, user=request.user, is_new=True)
        if story_form.is_valid():
            story = story_form.save(commit=False)
            story.author = request.user
            story.save()
            
            # Process individual audio files
            # Find all file inputs with names starting with 'audio_file_'
            audio_files = []
            for key in request.FILES:
                if key.startswith('audio_file_'):
                    audio_files.append(request.FILES[key])
            
            # Process each audio file
            for file in audio_files:
                # Generate a title from the filename (strip extension)
                title = os.path.splitext(file.name)[0]
                
                # Create the audio clip
                AudioClip.objects.create(
                    story=story,
                    title=title,
                    audio_file=file,
                    uploaded_by=request.user
                )
            
            # Create initial revision
            StoryRevision.objects.create(
                story=story,
                content=story.content,
                revision_number=1,
                created_by=request.user
            )
            
            messages.success(request, "Story created successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
        else:
            logging.error("StoryForm errors: %s", story_form.errors)
    else:
        story_form = StoryForm(user=request.user, is_new=True)
        title = request.GET.get('title')
        if title:
            story_form.initial['title'] = title
    
    context = {
        'form': story_form,
        'is_new': True,
    }
    return render(request, 'newsroom/story/story_create.html', context)

@staff_required
@can_edit_story
def story_edit(request, story_id, story=None):
    """Edit an existing story with multiple audio upload handling"""
    if request.method == 'POST':
        # Check if this is a status update (e.g., submit for review)
        new_status = request.POST.get('status')
        
        story_form = StoryForm(request.POST, instance=story, user=request.user, is_new=False)
        if story_form.is_valid():
            updated_story = story_form.save(commit=False)
            
            # Update status if provided
            if new_status and new_status in dict(Story.STATUS_CHOICES).keys():
                updated_story.status = new_status
                messages.success(request, f"Story status updated to {dict(Story.STATUS_CHOICES)[new_status]}")
            
            updated_story.save()
            
            # Create a new revision if content has changed
            if 'content' in story_form.changed_data:
                latest_revision = StoryRevision.objects.filter(story=story).order_by('-revision_number').first()
                new_revision_number = 1 if not latest_revision else latest_revision.revision_number + 1
                StoryRevision.objects.create(
                    story=story,
                    content=updated_story.content,
                    revision_number=new_revision_number,
                    created_by=request.user
                )
            
            # Process individual audio files
            # Find all file inputs with names starting with 'audio_file_'
            audio_files = []
            for key in request.FILES:
                if key.startswith('audio_file_'):
                    audio_files.append(request.FILES[key])
            
            # Process each audio file
            for file in audio_files:
                # Generate a title from the filename (strip extension)
                title = os.path.splitext(file.name)[0]
                
                # Create the audio clip
                AudioClip.objects.create(
                    story=story,
                    title=title,
                    audio_file=file,
                    uploaded_by=request.user
                )
            
            messages.success(request, "Story updated successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
        else:
            logging.error("StoryForm errors: %s", story_form.errors)
    else:
        story_form = StoryForm(instance=story, user=request.user, is_new=False)
    
    context = {
        'form': story_form,
        'story': story,
        'is_new': False
    }
    return render(request, 'newsroom/story/story_edit.html', context)

@staff_required
@publishing_rights_required
@can_edit_story
def story_publish(request, story_id, story=None):
    """Publish a story"""
    if story.status == 'PUBLISHED':
        messages.info(request, "This story is already published")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    if request.method == 'POST':
        form = StoryPublishForm(request.POST, story=story)
        if form.is_valid():
            story.status = 'PUBLISHED'
            story.published_at = timezone.now()
            story.editor = request.user
            story.save()
            messages.success(request, "Story published successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
    else:
        form = StoryPublishForm(story=story)
    
    context = {
        'form': form,
        'story': story
    }
    return render(request, 'newsroom/story/story_publish.html', context)

@staff_required
@can_edit_story
def story_audio_upload(request, story_id, story=None):
    """Upload audio clips for a story"""
    if request.method == 'POST':
        form = AudioClipForm(request.POST, request.FILES, story=story, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Audio clip uploaded successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
    else:
        form = AudioClipForm(story=story, user=request.user)
    
    context = {
        'form': form,
        'story': story
    }
    
    return render(request, 'newsroom/story/story_audio_upload.html', context)

@staff_required
@can_edit_story
def story_audio_delete(request, story_id, audio_id, story=None):
    """Delete an audio clip from a story"""
    audio_clip = get_object_or_404(AudioClip, id=audio_id, story=story)
    
    if request.method == 'POST':
        audio_clip.delete()
        messages.success(request, "Audio clip deleted successfully")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    context = {
        'audio_clip': audio_clip,
        'story': story
    }
    
    return render(request, 'newsroom/story/story_audio_delete.html', context)

@login_required
def story_download(request, story_id):
    """Download a story (increment download counter)"""
    story = get_object_or_404(Story, id=story_id)
    
    # For radio users, check access permissions
    if request.user.user_type == CustomUser.UserType.RADIO:
        if not has_radio_access(request.user, story):
            return HttpResponseForbidden("You don't have access to this content")
    
    # Increment download counter
    story.download_count += 1
    story.save(update_fields=['download_count'])
    
    # Generate a text file with the story content
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{story.slug}.txt"'
    
    # Write story details
    response.write(f"TITLE: {story.title}\n")
    response.write(f"CATEGORY: {story.category.name}\n")
    response.write(f"AUTHOR: {story.author.get_full_name()}\n")
    response.write(f"DATE: {story.published_at or story.created_at}\n\n")
    
    # Strip HTML tags from content (simplified approach)
    import re
    clean_content = re.sub(r'<.*?>', '', story.content)
    response.write(clean_content)
    
    return response

# Category views
@staff_required
def category_list(request):
    """List all categories organized by content type"""
    # Group categories by content type
    category_groups = {}
    
    for content_type, display_name in Category.TYPE_CHOICES:
        # Get the top level content type categories
        top_categories = Category.objects.filter(
            content_type=content_type,
            level=1
        ).order_by('name')
        
        # Get the default "Uncategorized" category
        try:
            default_category = Category.objects.get(
                content_type=content_type,
                is_default=True
            )
        except Category.DoesNotExist:
            # Create it if it doesn't exist
            default_category = Category.get_or_create_default(content_type)
        
        # For each top category, get children and story counts
        categories_data = []
        for category in top_categories:
            category_data = {
                'category': category,
                'story_count': category.get_story_count(),
                'children': []
            }
            
            # Get children (parent categories)
            parent_categories = Category.objects.filter(
                parent=category,
                level=2
            ).order_by('name')
            
            for parent in parent_categories:
                parent_data = {
                    'category': parent,
                    'story_count': parent.get_story_count(),
                    'children': []
                }
                
                # Get subcategories
                subcategories = Category.objects.filter(
                    parent=parent,
                    level=3
                ).order_by('name')
                
                for subcategory in subcategories:
                    parent_data['children'].append({
                        'category': subcategory,
                        'story_count': subcategory.get_story_count()
                    })
                
                category_data['children'].append(parent_data)
            
            categories_data.append(category_data)
        
        # Add the default "Uncategorized" category
        default_data = {
            'category': default_category,
            'story_count': default_category.get_story_count(),
            'children': [],
            'is_default': True
        }
        
        category_groups[content_type] = {
            'name': display_name,
            'categories': categories_data,
            'default_category': default_data
        }
    
    context = {
        'category_groups': category_groups
    }
    
    return render(request, 'newsroom/category/category_list.html', context)

@staff_required
@can_manage_categories
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, "Category created successfully")
            return redirect('newsroom:category_list')
    else:
        form = CategoryForm()
        
        # Pre-populate parent and content type if provided in URL
        parent_id = request.GET.get('parent')
        content_type = request.GET.get('content_type')
        
        if parent_id:
            try:
                parent = Category.objects.get(id=parent_id)
                form.initial['parent'] = parent
                form.initial['content_type'] = parent.content_type
                form.fields['content_type'].disabled = True
            except Category.DoesNotExist:
                pass
        elif content_type:
            form.initial['content_type'] = content_type
    
    context = {
        'form': form,
        'is_new': True
    }
    
    return render(request, 'newsroom/category/category_create.html', context)

@staff_required
@can_manage_categories
def category_edit(request, category_id):
    """Edit an existing category"""
    category = get_object_or_404(Category, id=category_id)
    
    # Don't allow editing default categories.
    if category.is_default:
        messages.warning(request, "Default categories cannot be edited")
        return redirect('newsroom:category_list')
    
    if request.method == 'POST':
        # Log the full POST data for debugging.
        logging.debug("POST data: %s", request.POST)
        form = CategoryForm(request.POST, instance=category, is_editing=True)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully")
            return redirect('newsroom:category_list')
        else:
            logging.error("CategoryForm errors for category %s: %s", category.id, form.errors)
    else:
        form = CategoryForm(instance=category, is_editing=True)
    
    context = {
        'form': form,
        'category': category,
        'is_new': False
    }
    
    return render(request, 'newsroom/category/category_edit.html', context)

@staff_required
@editor_required
def category_delete(request, category_id):
    """Delete a category"""
    category = get_object_or_404(Category, id=category_id)
    
    # Don't allow deleting default categories
    if category.is_default:
        messages.error(request, "Default categories cannot be deleted")
        return redirect('newsroom:category_list')
    
    # Get counts for stories and subcategories
    story_count = Story.objects.filter(category=category).count()
    subcategory_count = category.children.count()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'reassign' and story_count > 0:
            # Reassign stories to the default category
            default_category = Category.get_or_create_default(category.content_type)
            Story.objects.filter(category=category).update(category=default_category)
            messages.info(request, f"{story_count} stories moved to '{default_category.name}'")
        
        # Check if we should delete subcategories or reassign them
        if subcategory_count > 0:
            if action == 'delete_subcategories':
                # First reassign stories from subcategories
                default_category = Category.get_or_create_default(category.content_type)
                for subcategory in category.children.all():
                    Story.objects.filter(category=subcategory).update(category=default_category)
                # Then delete subcategories
                category.children.all().delete()
                messages.info(request, f"Deleted {subcategory_count} subcategories")
            else:
                messages.error(request, "You must specify how to handle subcategories")
                return redirect('newsroom:category_delete', category_id=category.id)
        
        # Now delete the category
        category.delete()
        messages.success(request, "Category deleted successfully")
        return redirect('newsroom:category_list')
    
    context = {
        'category': category,
        'story_count': story_count,
        'subcategory_count': subcategory_count,
        'default_category': Category.get_or_create_default(category.content_type)
    }
    
    return render(request, 'newsroom/category/category_delete.html', context)

# Task views
@staff_required
def task_list(request):
    """List tasks with filtering options"""
    # Base queryset
    tasks = Task.objects.all().select_related('assigned_by', 'assigned_to', 'related_story')
    
    # Apply filters
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    priority_filter = request.GET.get('priority')
    search_query = request.GET.get('q')
    view_mode = request.GET.get('view', 'assigned')  # Default to tasks assigned to current user
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if type_filter:
        tasks = tasks.filter(task_type=type_filter)
    
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(assigned_to__first_name__icontains=search_query) |
            Q(assigned_to__last_name__icontains=search_query)
        )
    
    # View mode filtering
    if view_mode == 'assigned':
        tasks = tasks.filter(assigned_to=request.user)
    elif view_mode == 'created':
        tasks = tasks.filter(assigned_by=request.user)
    # else 'all' - show all tasks (for editors/admins)
    elif view_mode == 'all' and request.user.staff_role not in ['EDITOR', 'SUPERADMIN', 'ADMIN']:
        # Only editors can see all tasks
        view_mode = 'assigned'
        tasks = tasks.filter(assigned_to=request.user)
    
    # Pagination
    paginator = Paginator(tasks.order_by('-created_at'), 15)
    page_number = request.GET.get('page')
    tasks_page = paginator.get_page(page_number)
    
    context = {
        'tasks': tasks_page,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'view_mode': view_mode
    }
    
    return render(request, 'newsroom/task/task_list.html', context)

@staff_required
def task_detail(request, task_id):
    """Show task details"""
    task = get_object_or_404(Task, id=task_id)
    
    # Get attachments
    attachments = task.attachments.all()
    
    # Get comments
    comments = task.comments.all().order_by('-created_at')
    
    # Forms for adding attachments and comments
    attachment_form = TaskAttachmentForm(task=task, user=request.user)
    comment_form = TaskCommentForm(task=task, user=request.user)
    
    context = {
        'task': task,
        'attachments': attachments,
        'comments': comments,
        'attachment_form': attachment_form,
        'comment_form': comment_form
    }
    
    return render(request, 'newsroom/task/task_detail.html', context)

@staff_required
def task_create(request):
    """Create a new task"""
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.save()
            
            messages.success(request, "Task created successfully")
            return redirect('newsroom:task_detail', task_id=task.id)
    else:
        form = TaskForm(user=request.user)
        
        # Pre-populate fields if provided in URL
        task_type = request.GET.get('type')
        if task_type:
            form.initial['task_type'] = task_type
        
        story_id = request.GET.get('story')
        if story_id:
            try:
                story = Story.objects.get(id=story_id)
                form.initial['related_story'] = story
                form.initial['title'] = f"Task related to: {story.title}"
            except Story.DoesNotExist:
                pass
        
        assigned_to = request.GET.get('assigned_to')
        if assigned_to:
            try:
                user = CustomUser.objects.get(id=assigned_to)
                form.initial['assigned_to'] = user
            except CustomUser.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'is_new': True
    }
    
    return render(request, 'newsroom/task/task_create.html', context)

@staff_required
@can_manage_task
def task_edit(request, task_id, task=None):
    """Edit an existing task"""
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated successfully")
            return redirect('newsroom:task_detail', task_id=task.id)
    else:
        form = TaskForm(instance=task, user=request.user)
    
    context = {
        'form': form,
        'task': task,
        'is_new': False
    }
    
    return render(request, 'newsroom/task/task_edit.html', context)

@staff_required
@can_manage_task
def task_status_update(request, task_id, task=None):
    """Update task status"""
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Task.STATUS_CHOICES).keys():
            task.status = new_status
            
            # Set completed_at if status is COMPLETED
            if new_status == 'COMPLETED':
                task.completed_at = timezone.now()
            elif task.completed_at and new_status != 'COMPLETED':
                # Reset completed_at if status changed from COMPLETED
                task.completed_at = None
                
            task.save()
            
            # Add a comment about the status change
            TaskComment.objects.create(
                task=task,
                author=request.user,
                content=f"Status changed to {dict(Task.STATUS_CHOICES)[new_status]}"
            )
            
            messages.success(request, "Task status updated successfully")
        else:
            messages.error(request, "Invalid task status")
    
    return redirect('newsroom:task_detail', task_id=task.id)

@staff_required
@can_manage_task
def task_add_comment(request, task_id, task=None):
    """Add a comment to a task"""
    if request.method == 'POST':
        form = TaskCommentForm(request.POST, task=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment added successfully")
    
    return redirect('newsroom:task_detail', task_id=task.id)

@staff_required
@can_manage_task
def task_add_attachment(request, task_id, task=None):
    """Add an attachment to a task"""
    if request.method == 'POST':
        form = TaskAttachmentForm(request.POST, request.FILES, task=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Attachment added successfully")
    
    return redirect('newsroom:task_detail', task_id=task.id)

@staff_required
@can_manage_task
def task_delete_attachment(request, task_id, attachment_id, task=None):
    """Delete an attachment from a task"""
    attachment = get_object_or_404(TaskAttachment, id=attachment_id, task=task)
    
    if request.method == 'POST':
        attachment.delete()
        messages.success(request, "Attachment deleted successfully")
    
    return redirect('newsroom:task_detail', task_id=task.id)

# Story revisions
@staff_required
@can_edit_story
def story_view_revision(request, story_id, revision_id, story=None):
    """View a specific revision of a story"""
    revision = get_object_or_404(StoryRevision, id=revision_id, story=story)
    
    context = {
        'story': story,
        'revision': revision
    }
    
    return render(request, 'newsroom/story/story_revision.html', context)

@staff_required
@can_edit_story
def story_restore_revision(request, story_id, revision_id, story=None):
    """Restore a story to a previous revision"""
    revision = get_object_or_404(StoryRevision, id=revision_id, story=story)
    
    if request.method == 'POST':
        # Update the story content
        story.content = revision.content
        story.save()
        
        # Create a new revision
        latest_revision = StoryRevision.objects.filter(story=story).order_by('-revision_number').first()
        new_revision_number = latest_revision.revision_number + 1
        
        StoryRevision.objects.create(
            story=story,
            content=revision.content,
            revision_number=new_revision_number,
            created_by=request.user
        )
        
        messages.success(request, f"Story restored to revision {revision.revision_number}")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    context = {
        'story': story,
        'revision': revision
    }
    
    return render(request, 'newsroom/story/story_restore_revision.html', context)