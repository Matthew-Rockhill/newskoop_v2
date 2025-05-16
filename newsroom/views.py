import os
import uuid
import logging
import json
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.text import slugify
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied

from accounts.models import CustomUser
from .models import (
    Story, Category, AudioClip, Task, TaskAttachment, 
    TaskComment, Tag, StoryActivity, record_story_activity
)
from .forms import (
    StoryForm, CategoryForm, AudioClipForm, TaskForm, 
    TaskCommentForm, TaskAttachmentForm, StoryPublishForm, TagForm, StoryTagsForm
)
from .permissions import (
    staff_required, editor_required, publishing_rights_required,
    can_edit_story, can_manage_task, can_manage_categories, has_radio_access, editor_or_subeditor_required
)

# Import the template tag functions
from .templatetags.story_actions import (
    can_submit_for_review, can_submit_for_approval, can_approve_story, 
    can_publish_story, can_download_story, can_assign_xhosa_translation,
    can_edit_story as can_edit_story_tag, can_delete_story
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('story_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('newsroom.story_creation')


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
        context['assigned_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status__in=['PENDING', 'IN_PROGRESS', 'REVIEW']
        ).order_by('due_date')[:5]
        
        # My stories stats
        my_stories = Story.objects.filter(author=request.user)
        context['my_stories'] = my_stories.order_by('-updated_at')[:5]
        context['my_story_count'] = my_stories.count()
        context['my_draft_count'] = my_stories.filter(status='DRAFT').count()
        context['my_published_count'] = my_stories.filter(status='PUBLISHED').count()
        
        # Task stats
        context['pending_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status='PENDING'
        ).count()
        context['completed_tasks'] = Task.objects.filter(
            assigned_to=request.user, 
            status='COMPLETED'
        ).count()
        
        # For editors and sub-editors
        if request.user.staff_role in ['EDITOR', 'SUPERADMIN', 'ADMIN', 'SUB_EDITOR']:
            # Stories awaiting review
            context['awaiting_review'] = Story.objects.filter(status='REVIEW').count()
            # Stories awaiting approval
            context['awaiting_approval'] = Story.objects.filter(status='PENDING_APPROVAL').count()
            # Stories awaiting publication (already approved)
            context['awaiting_publication'] = Story.objects.filter(status='APPROVED').count()
            
            # All pending tasks across the system
            context['all_pending_tasks'] = Task.objects.filter(status='PENDING').count()
            
            # Stories at different stages in the workflow
            context['stories_for_review'] = Story.objects.filter(status='REVIEW').order_by('-created_at')[:5]
            context['stories_for_approval'] = Story.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')[:5]
            context['stories_ready_for_publishing'] = Story.objects.filter(status='APPROVED').order_by('-created_at')[:5]
            
            # Recent activity for sub-editors
            if request.user.staff_role == 'SUB_EDITOR':
                context['recent_activity'] = StoryActivity.objects.filter(
                    story__status__in=['REVIEW', 'PENDING_APPROVAL', 'APPROVED']
                ).select_related('story', 'user').order_by('-created_at')[:10]
            
            # Translation tasks
            context['translation_tasks'] = Task.objects.filter(
                task_type='TRANSLATION',
                status__in=['PENDING', 'IN_PROGRESS']
            ).order_by('due_date')[:5]
            
            context['translation_task_count'] = Task.objects.filter(
                task_type='TRANSLATION',
                status__in=['PENDING', 'IN_PROGRESS']
            ).count()
            
            # Translations needing approval
            context['translations_for_approval'] = Story.objects.filter(
                is_translation=True,
                status='PENDING_APPROVAL'
            ).order_by('-created_at')[:5]
            
            context['translation_approval_count'] = Story.objects.filter(
                is_translation=True,
                status='PENDING_APPROVAL'
            ).count()
            
            # Track which English stories have incomplete translations
            english_stories_with_translations = Story.objects.filter(
                language='ENGLISH',
                status__in=['APPROVED', 'PUBLISHED']
            ).annotate(
                translation_count=Count('tasks', filter=Q(tasks__task_type='TRANSLATION')),
                completed_translation_count=Count('tasks', filter=Q(tasks__task_type='TRANSLATION', tasks__status='COMPLETED'))
            ).filter(
                translation_count__gt=0
            ).order_by('-created_at')
            
            # Filter to stories with incomplete translations
            context['incomplete_translations'] = [
                story for story in english_stories_with_translations 
                if story.translation_count > story.completed_translation_count
            ][:5]
            
    elif request.user.user_type == CustomUser.UserType.RADIO:
        # Radio station dashboard logic (keep as is)
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
    stories = Story.objects.all().select_related('author', 'category', 'editor').prefetch_related('tags')
    
    if request.user.user_type == CustomUser.UserType.RADIO:
        station = request.user.radio_station
        if station:
            stories = stories.filter(status='PUBLISHED')
    else:
        # For interns and journalists, show only their own stories.
        if request.user.staff_role in ['INTERN', 'JOURNALIST']:
            stories = stories.filter(author=request.user)
        # For sub-editors, show only stories that are pending approval or higher, or their own stories.
        elif request.user.staff_role == 'SUB_EDITOR':
            stories = stories.filter(
                Q(status__in=['PENDING_APPROVAL', 'APPROVED', 'TRANSLATED', 'PUBLISHED']) |
                Q(author=request.user)
            )
    
    # Apply additional filters (status, category, language, search query)
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    language_filter = request.GET.get('language')
    tag_filter = request.GET.get('tag')
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
    if tag_filter:
        stories = stories.filter(tags__id=tag_filter)
    if search_query:
        stories = stories.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(author__first_name__icontains=search_query) |
            Q(author__last_name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Fetch categories for filter dropdown
    categories = Category.objects.filter(level__in=[2, 3]).order_by('name')
    
    # Fetch popular tags for filter dropdown
    popular_tags = Tag.objects.annotate(story_count=Count('stories')).order_by('-story_count')[:10]
    
    paginator = Paginator(stories.order_by('-created_at'), 15)
    page_number = request.GET.get('page')
    stories_page = paginator.get_page(page_number)
    
    # Define page actions
    actions = []
    
    # New Story button (staff only)
    if request.user.user_type == 'STAFF':
        actions.append({
            'label': 'New Story',
            'url': reverse('newsroom:story_create'),
            'icon': 'plus',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
        })
    
    context = {
        'stories': stories_page,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'language_filter': language_filter,
        'tag_filter': tag_filter,
        'search_query': search_query,
        'categories': categories,
        'popular_tags': popular_tags,
        'actions': actions
    }
    
    return render(request, 'newsroom/story/story_list.html', context)

@login_required
def story_detail(request, story_id):
    """View story details"""
    story = get_object_or_404(Story, id=story_id)
    
    # Get audio clips for this story
    audio_clips = story.audio_clips.all()
    tasks = None
    journalists = None
    reviewer_task = None
    
    if request.user.user_type == CustomUser.UserType.STAFF:
        tasks = Task.objects.filter(related_story=story)
        
        # Get journalists for review assignment dropdown - only for interns
        if story.status == 'DRAFT' and story.author == request.user and request.user.staff_role == 'INTERN':
            journalists = CustomUser.objects.filter(
                user_type='STAFF',
                staff_role='JOURNALIST',  # Only journalists can review
                is_active=True
            ).exclude(id=request.user.id)
        
        # Check if current user is reviewing this story
        reviewer_task = Task.objects.filter(
            related_story=story,
            task_type='STORY_REVIEW',
            assigned_to=request.user,
            status__in=['PENDING', 'IN_PROGRESS']
        ).first()
    
    # Define page actions
    actions = generate_story_actions(request, story)
    
    context = {
        'story': story,
        'audio_clips': audio_clips,
        'tasks': tasks,
        'journalists': journalists,
        'reviewer_task': reviewer_task,
        'actions': actions,
    }
    return render(request, 'newsroom/story/story_detail.html', context)

@staff_required
def story_create(request):
    """Create a new story with drag-and-drop audio upload"""
    if request.method == 'POST':
        story_form = StoryForm(request.POST, request.FILES, user=request.user, is_new=True)
        if story_form.is_valid():
            story = story_form.save()
            
            # Process audio files - track which files we've processed
            processed_files = set()
            audio_files = []
            
            # First check for files with audio_file_X pattern (our JS enhancement)
            for key in request.FILES:
                if key.startswith('audio_file_'):
                    file = request.FILES[key]
                    audio_files.append(file)
                    processed_files.add(file.name)
            
            # Then check for multiple files uploaded via audio_files field
            if 'audio_files' in request.FILES:
                for file in request.FILES.getlist('audio_files'):
                    if file.name not in processed_files:
                        audio_files.append(file)
            
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
            
            record_story_activity(story, request.user, 'CREATE', 
                     new_status='DRAFT',
                     description="Story created")
            
            messages.success(request, "Story created successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
        else:
            messages.error(request, "Please correct the errors below")
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
        story_form = StoryForm(request.POST, request.FILES, instance=story, user=request.user, is_new=False)
        if story_form.is_valid():
            updated_story = story_form.save()
            
            # Process individual audio files
            audio_files = request.FILES.getlist('audio_files')
            
            # Process each audio file
            for file in audio_files:
                title = os.path.splitext(file.name)[0]
                AudioClip.objects.create(
                    story=story,
                    title=title,
                    audio_file=file,
                    uploaded_by=request.user
                )
            
            record_story_activity(story, request.user, 'EDIT',
                    description="Content edited")
            
            messages.success(request, "Story updated successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
        else:
            messages.error(request, "Please correct the errors below")
    else:
        story_form = StoryForm(instance=story, user=request.user, is_new=False)
    
    # Define page actions
    actions = generate_story_actions(request, story)
    
    context = {
        'form': story_form,
        'story': story,
        'is_new': False,
        'actions': actions
    }
    return render(request, 'newsroom/story/story_edit.html', context)

@staff_required
@can_edit_story
def story_submit_review(request, story_id, story=None):
    """Submit a story for review by a journalist"""
    if not story:
        story = get_object_or_404(Story, id=story_id)
    
    # Check if user can submit this story for review
    if not story.can_be_edited_by(request.user):
        raise PermissionDenied("You don't have permission to submit this story for review")
    
    if story.status != 'DRAFT':
        messages.error(request, "Only draft stories can be submitted for review")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    # Get available journalists
    journalists = CustomUser.objects.filter(staff_role='JOURNALIST', is_active=True)
    
    if request.method == 'POST':
        reviewer_id = request.POST.get('reviewer')
        if not reviewer_id:
            messages.error(request, "Please select a journalist to review the story")
            return redirect('newsroom:story_submit_review', story_id=story.id)
        
        reviewer = get_object_or_404(CustomUser, id=reviewer_id, staff_role='JOURNALIST')
        
        # Create a review task
        review_task = Task.objects.create(
            title=f"Review Story: {story.title}",
            description=f"Please review the story '{story.title}' and provide feedback.",
            task_type='STORY_REVIEW',
            status='PENDING',
            priority='MEDIUM',
            assigned_by=request.user,
            assigned_to=reviewer,
            related_story=story
        )
        
        # Update story status and reviewer
        story.reviewer = reviewer
        story.status = 'REVIEW'
        story.save()
        
        # Record the activity
        record_story_activity(
            story, request.user, 'SUBMIT_REVIEW',
            old_status='DRAFT',
            new_status='REVIEW',
            description=f"Submitted for review by {reviewer.get_full_name()}"
        )
        
        messages.success(request, "Story submitted for review successfully")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    return render(request, 'newsroom/story/story_submit_review.html', {
        'story': story,
        'journalists': journalists
    })

@staff_required
def api_list_journalists(request):
    """API endpoint to list journalists for the reviewer dropdown"""
    # Get journalists and editors
    users = CustomUser.objects.filter(
        user_type='STAFF',
        staff_role__in=['JOURNALIST', 'EDITOR', 'SUB_EDITOR'],
        is_active=True
    ).exclude(id=request.user.id)  # Exclude the current user
    
    # Format the data for the dropdown
    data = [
        {
            'id': str(user.id),
            'full_name': user.get_full_name(),
            'role': user.get_staff_role_display()
        }
        for user in users
    ]
    
    return JsonResponse(data, safe=False)

def validate_story_status_transition(user, story, target_status):
    """
    Validate if a story can transition from its current status to the target status.
    
    Args:
        user: The user attempting to make the transition
        story: The story object
        target_status: The target status to transition to
        
    Returns:
        tuple: (is_valid, message) where is_valid is a boolean and message is an error message if invalid
    """
    current_status = story.status
    
    # Define allowed transitions based on user role and current status
    if target_status == 'PUBLISHED':
        # Only editors and above can publish stories
        if user.staff_role not in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
            return False, "You don't have permission to publish stories"
        
        # Only approved stories can be published
        if current_status != 'APPROVED':
            return False, f"Cannot publish: Story must be approved first (current status: {current_status})"
    
    elif target_status == 'APPROVED':
        # Only sub-editors and above can approve stories
        if user.staff_role not in ['SUB_EDITOR', 'EDITOR', 'SUPERADMIN', 'ADMIN']:
            return False, "You don't have permission to approve stories"
        
        # Only stories pending approval can be approved
        if current_status != 'PENDING_APPROVAL':
            return False, f"Cannot approve: Story must be pending approval first (current status: {current_status})"
    
    elif target_status == 'PENDING_APPROVAL':
        # Authors or reviewers can submit for approval
        is_author = story.author == user
        is_reviewer = story.reviewer == user
        
        if not (is_author or is_reviewer):
            return False, "Only the author or assigned reviewer can submit a story for approval"
        
        # Only draft or reviewed stories can be submitted for approval
        if current_status not in ['DRAFT', 'REVIEW']:
            return False, f"Cannot submit for approval: Story must be in draft or review status (current status: {current_status})"
    
    elif target_status == 'REVIEW':
        # Only the author can submit a story for review
        if story.author != user:
            return False, "Only the author can submit a story for review"
        
        # Only draft stories can be submitted for review
        if current_status != 'DRAFT':
            return False, f"Cannot submit for review: Story must be in draft status (current status: {current_status})"
    
    elif target_status == 'ARCHIVED':
        # Only editors and above can archive stories
        if user.staff_role not in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
            return False, "You don't have permission to archive stories"
    
    # If we get here, the transition is valid
    return True, ""

@staff_required
@publishing_rights_required
@can_edit_story
def story_publish(request, story_id, story=None):
    """Publish a story"""
    # Check if the story is already published
    if story.status == 'PUBLISHED':
        messages.info(request, "This story is already published")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    # Validate that the status transition is allowed
    is_valid, message = validate_story_status_transition(request.user, story, 'PUBLISHED')
    if not is_valid:
        messages.error(request, message)
        return redirect('newsroom:story_detail', story_id=story.id)
    
    # Check for translations if this is an English story
    if story.language == 'ENGLISH':
        # Check for incomplete translation tasks
        pending_translations = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION',
            status__in=['PENDING', 'IN_PROGRESS', 'REVIEW']
        )
        
        if pending_translations.exists():
            translation_info = ", ".join([t.get_status_display() for t in pending_translations])
            messages.error(request, f"Cannot publish: {pending_translations.count()} translation tasks still pending ({translation_info})")
            return redirect('newsroom:story_detail', story_id=story.id)
        
        # Check if all translations are approved by looking at stories created through the translation tasks
        completed_translation_tasks = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION',
            status='COMPLETED'
        )
        
        for task in completed_translation_tasks:
            # Get the author who completed this translation task
            translator = task.assigned_to
            
            # Find translated stories by this translator that are marked as translations
            translated_stories = Story.objects.filter(
                author=translator,
                is_translation=True,
                language__in=['AFRIKAANS', 'XHOSA']
            ).filter(
                # Look for either the standard naming pattern or the original story title in the translation title
                Q(title__contains=story.title) | 
                Q(title__startswith=f"[{task.title.split(':')[0].strip().split(' ')[-1]}]")
            )
            
            # Check if any translations are not approved
            for translated_story in translated_stories:
                if translated_story.status != 'APPROVED':
                    messages.error(request, f"Cannot publish: Translation '{translated_story.title}' is not yet approved")
                    return redirect('newsroom:story_detail', story_id=story.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'publish':
            # Get the publication date (use current time if not provided)
            published_at_str = request.POST.get('published_at')
            if published_at_str:
                try:
                    # Parse the datetime-local input value (format: YYYY-MM-DDThh:mm)
                    published_at = timezone.datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M')
                    # Make it timezone-aware
                    published_at = timezone.make_aware(published_at)
                except (ValueError, TypeError):
                    # If there's any error parsing, use current time
                    published_at = timezone.now()
            else:
                published_at = timezone.now()
            
            # Get editorial notes if provided
            editorial_notes = request.POST.get('editorial_notes', '')
            
            # Update the story
            story.status = 'PUBLISHED'
            story.published_at = published_at
            story.editor = request.user
            
            # Save the changes
            story.save()
            
            # Also publish any approved translations
            if story.language == 'ENGLISH':
                # Find all translation tasks for this story
                translation_tasks = Task.objects.filter(
                    related_story=story,
                    task_type='TRANSLATION',
                    status='COMPLETED'
                )
                
                for task in translation_tasks:
                    translator = task.assigned_to
                    
                    # Find translated stories by this translator
                    translated_stories = Story.objects.filter(
                        author=translator,
                        is_translation=True,
                        status='APPROVED',
                        language__in=['AFRIKAANS', 'XHOSA']
                    ).filter(
                        Q(title__contains=story.title) | 
                        Q(title__startswith=f"[{task.title.split(':')[0].strip().split(' ')[-1]}]")
                    )
                    
                    for translated_story in translated_stories:
                        translated_story.status = 'PUBLISHED'
                        translated_story.published_at = published_at
                        translated_story.editor = request.user
                        translated_story.save()
                        
                        messages.info(request, f"Also published translation: {translated_story.title}")
            
            # Handle notifications if selected
            should_notify = request.POST.get('send_notifications') is not None
            if should_notify:
                # Send notifications logic would go here
                # For now, just log it
                print(f"Should send notifications for story {story.id}")
            
            messages.success(request, "Story published successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
    
    # For GET requests, prepare the form context
    now = timezone.now()
    
    # Get translation status for display
    translation_tasks = []
    all_translations_complete = True
    
    if story.language == 'ENGLISH':
        translation_tasks = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION'
        ).select_related('assigned_to')
        
        # Check if all translations are complete
        all_translations_complete = not translation_tasks.filter(
            status__in=['PENDING', 'IN_PROGRESS', 'REVIEW']
        ).exists()
    
    context = {
        'story': story,
        'now': now,
        'translation_tasks': translation_tasks,
        'all_translations_complete': all_translations_complete,
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
            logging.error("CategoryForm errors: %s", form.errors)
            messages.error(request, "Please correct the errors below")
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
        # Log the full POST data for debugging
        logging.debug("Category edit POST data: %s", request.POST)
        
        form = CategoryForm(request.POST, instance=category, is_editing=True)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully")
            return redirect('newsroom:category_list')
        else:
            logging.error("CategoryForm errors for category %s: %s", category.id, form.errors)
            messages.error(request, "Please correct the errors below")
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

@staff_required
@editor_or_subeditor_required
@can_edit_story
def story_approve(request, story_id, story=None):
    """Approve a story by a sub-editor"""
    if not story:
        story = get_object_or_404(Story, id=story_id)
    
    # Check if user can approve this story
    if request.user.staff_role != 'SUB_EDITOR':
        raise PermissionDenied("Only sub-editors can approve stories")
    
    if story.status != 'PENDING_APPROVAL':
        messages.error(request, "Only stories pending approval can be approved")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    story.status = 'APPROVED'
    story.save()
    
    # Record the activity
    record_story_activity(
        story, request.user, 'APPROVE',
        old_status='PENDING_APPROVAL',
        new_status='APPROVED',
        description="Story approved"
    )
    
    messages.success(request, "Story approved successfully")
    return redirect('newsroom:story_detail', story_id=story.id)

@staff_required
def submit_translation(request, task_id):
    """Create or update a translation based on a translation task"""
    # Get the translation task
    task = get_object_or_404(Task, id=task_id, task_type='TRANSLATION')
    
    # Get the original story
    original_story = task.related_story
    if not original_story:
        messages.error(request, "Original story not found for this translation task")
        return redirect('newsroom:task_detail', task_id=task.id)
    
    # Determine target language from task title
    target_language = None
    if "Afrikaans" in task.title:
        target_language = 'AFRIKAANS'
    elif "Xhosa" in task.title:
        target_language = 'XHOSA'
    
    if not target_language:
        messages.error(request, "Could not determine target language for translation")
        return redirect('newsroom:task_detail', task_id=task.id)
    
    # Check if translation story already exists - looking for stories by this translator that are translations
    translation_story = Story.objects.filter(
        author=request.user,
        is_translation=True,
        language=target_language,
        tasks__in=[task.id]  # This connects the translation to the task
    ).first()
    
    if request.method == 'POST':
        # Process the form submission
        translation_title = request.POST.get('title')
        translation_content = request.POST.get('content')
        
        if not translation_title or not translation_content:
            messages.error(request, "Title and content are required")
            return redirect('newsroom:submit_translation', task_id=task.id)
        
        if translation_story:
            # Update existing translation
            translation_story.title = translation_title
            translation_story.content = translation_content
            translation_story.save()
            
            # Create a new revision
            latest_revision = StoryRevision.objects.filter(story=translation_story).order_by('-revision_number').first()
            new_revision_number = 1 if not latest_revision else latest_revision.revision_number + 1
            
            StoryRevision.objects.create(
                story=translation_story,
                content=translation_content,
                revision_number=new_revision_number,
                created_by=request.user
            )
        else:
            # Create new translation story
            translation_story = Story.objects.create(
                title=translation_title,
                content=translation_content,
                category=original_story.category,
                religion_classification=original_story.religion_classification,
                language=target_language,
                is_translation=True,
                author=request.user,
                status='REVIEW'  # Start in review status
            )
            
            # Link this story to the task to make it easier to find related translations
            task.related_translations = task.related_translations or []
            if hasattr(task, 'related_translations'):
                task.related_translations.append(str(translation_story.id))
            
            # Create initial revision
            StoryRevision.objects.create(
                story=translation_story,
                content=translation_content,
                revision_number=1,
                created_by=request.user
            )
        
        # Update task status
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.save()
        
        # Add a comment
        TaskComment.objects.create(
            task=task,
            author=request.user,
            content=f"Translation completed and submitted for review."
        )
        
        messages.success(request, "Translation submitted successfully")
        return redirect('newsroom:story_detail', story_id=translation_story.id)
    
    # For GET requests, show the translation form
    context = {
        'task': task,
        'original_story': original_story,
        'translation_story': translation_story,
        'target_language': target_language,
    }
    return render(request, 'newsroom/story/submit_translation.html', context)

@staff_required
@editor_or_subeditor_required
def translation_status_report(request):
    """View to display the status of all translations"""
    
    # Get all English stories that have translation tasks
    stories_with_translations = Story.objects.filter(
        language='ENGLISH',
        tasks__task_type='TRANSLATION'
    ).distinct()
    
    # Get status information for each story
    stories_data = []
    for story in stories_with_translations:
        # Get translation tasks
        translation_tasks = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION'
        ).select_related('assigned_to')
        
        # Count tasks by status
        task_counts = {
            'PENDING': 0,
            'IN_PROGRESS': 0,
            'REVIEW': 0,
            'COMPLETED': 0,
            'CANCELLED': 0,
            'total': len(translation_tasks)
        }
        
        for task in translation_tasks:
            if task.status in task_counts:
                task_counts[task.status] += 1
        
        # Determine overall status
        overall_status = 'complete' if task_counts['COMPLETED'] == task_counts['total'] else 'incomplete'
        
        # Add to stories data
        stories_data.append({
            'story': story,
            'tasks': translation_tasks,
            'task_counts': task_counts,
            'overall_status': overall_status
        })
    
    context = {
        'stories_data': stories_data,
        'pending_count': sum(data['task_counts']['PENDING'] for data in stories_data),
        'in_progress_count': sum(data['task_counts']['IN_PROGRESS'] for data in stories_data),
        'review_count': sum(data['task_counts']['REVIEW'] for data in stories_data),
        'completed_count': sum(data['task_counts']['COMPLETED'] for data in stories_data),
        'total_count': sum(data['task_counts']['total'] for data in stories_data),
        'complete_stories': sum(1 for data in stories_data if data['overall_status'] == 'complete')
    }
    
    return render(request, 'newsroom/reports/translation_status.html', context)

@staff_required
@can_edit_story
def story_submit_approval(request, story_id, story=None):
    """Submit a reviewed story for approval by a sub-editor"""
    if not story:
        story = get_object_or_404(Story, id=story_id)
    
    # Check if user can submit this story for approval
    if not story.can_be_edited_by(request.user):
        raise PermissionDenied("You don't have permission to submit this story for approval")
    
    # Allow submission if:
    # 1. User is the author and story is in DRAFT status (for journalists submitting their own stories)
    # 2. User is the reviewer and story is in REVIEW status (for journalists reviewing intern stories)
    if not ((story.author == request.user and story.status == 'DRAFT') or 
            (story.reviewer == request.user and story.status == 'REVIEW')):
        messages.error(request, "You can only submit stories for approval if you are the author or reviewer")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    story.status = 'PENDING_APPROVAL'
    story.save()
    
    # Record the activity
    record_story_activity(
        story, request.user, 'SUBMIT_APPROVAL',
        old_status=story.status,
        new_status='PENDING_APPROVAL',
        description="Submitted for approval"
    )
    
    messages.success(request, "Story submitted for approval successfully")
    return redirect('newsroom:story_detail', story_id=story.id)

@staff_required
@can_edit_story
def story_complete_review(request, story_id, task_id, story=None):
    """Mark a review task as completed"""
    if request.method == 'POST':
        # Get the task
        task = get_object_or_404(Task, id=task_id, related_story=story, task_type='STORY_REVIEW', assigned_to=request.user)
        
        # Update the task status
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.save()
        
        # Add a comment
        TaskComment.objects.create(
            task=task,
            author=request.user,
            content=f"Review completed by {request.user.get_full_name()}."
        )
        
        messages.success(request, "Review completed. You can now submit the story for approval.")
        return redirect('newsroom:story_detail', story_id=story.id)
    
    return redirect('newsroom:story_detail', story_id=story.id)

@staff_required
@editor_or_subeditor_required
def tag_list(request):
    """List all tags"""
    tags = Tag.objects.all().order_by('name')
    
    # Define page actions
    actions = [{
        'label': 'Create Tag',
        'url': reverse('newsroom:tag_create'),
        'icon': 'plus',
        'type': 'primary'
    }]
    
    context = {
        'tags': tags,
        'actions': actions
    }
    
    return render(request, 'newsroom/tag/tag_list.html', context)

@staff_required
@editor_or_subeditor_required
def tag_create(request):
    """Create a new tag"""
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.created_by = request.user
            tag.save()
            messages.success(request, "Tag created successfully")
            return redirect('newsroom:tag_list')
        else:
            logging.error("TagForm errors: %s", form.errors)
            messages.error(request, "Please correct the errors below")
    else:
        form = TagForm()
    
    context = {
        'form': form,
        'is_new': True
    }
    
    return render(request, 'newsroom/tag/tag_create.html', context)

@staff_required
@editor_or_subeditor_required
def tag_edit(request, tag_id):
    """Edit an existing tag"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, "Tag updated successfully")
            return redirect('newsroom:tag_list')
        else:
            logging.error("TagForm errors for tag %s: %s", tag.id, form.errors)
            messages.error(request, "Please correct the errors below")
    else:
        form = TagForm(instance=tag)
    
    context = {
        'form': form,
        'tag': tag,
        'is_new': False
    }
    
    return render(request, 'newsroom/tag/tag_edit.html', context)

@staff_required
@editor_or_subeditor_required
def tag_delete(request, tag_id):
    """Delete a tag"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    # Get count of stories using this tag
    story_count = tag.stories.count()
    
    if request.method == 'POST':
        # Delete the tag (it will be removed from all stories automatically)
        tag.delete()
        messages.success(request, "Tag deleted successfully")
        return redirect('newsroom:tag_list')
    
    context = {
        'tag': tag,
        'story_count': story_count
    }
    
    return render(request, 'newsroom/tag/tag_delete.html', context)

@staff_required
@editor_or_subeditor_required
@can_edit_story
def story_manage_tags(request, story_id, story=None):
    """Add or remove tags from a story"""
    if request.method == 'POST':
        form = StoryTagsForm(request.POST, story=story)
        if form.is_valid():
            # Get the selected tags
            selected_tags = form.cleaned_data['tags']
            
            # Get the old tags for comparison
            old_tags = set(story.tags.all())
            new_tags = set(selected_tags)
            
            # Calculate changes
            added_tags = new_tags - old_tags
            removed_tags = old_tags - new_tags
            
            # Validate tag count before making changes
            if len(new_tags) > 10:
                messages.error(request, "A story can have a maximum of 10 tags")
                return redirect('newsroom:story_manage_tags', story_id=story.id)
            
            # Clear existing tags and add the selected ones
            story.tags.clear()
            for tag in selected_tags:
                try:
                    tag.validate_story_tag_count(story)
                    story.tags.add(tag)
                except ValidationError as e:
                    messages.error(request, str(e))
                    return redirect('newsroom:story_manage_tags', story_id=story.id)
            
            # Log this activity with detailed changes
            changes = []
            if added_tags:
                changes.append(f"Added tags: {', '.join(tag.name for tag in added_tags)}")
            if removed_tags:
                changes.append(f"Removed tags: {', '.join(tag.name for tag in removed_tags)}")
            
            record_story_activity(story, request.user, 'EDIT', 
                                 description="Tags updated: " + "; ".join(changes))
            
            messages.success(request, "Story tags updated successfully")
            return redirect('newsroom:story_detail', story_id=story.id)
    else:
        # Pre-select the story's current tags
        form = StoryTagsForm(initial={'tags': story.tags.all()}, story=story)
    
    # Get popular tags for suggestions
    popular_tags = Tag.objects.annotate(
        usage_count=Count('stories')
    ).order_by('-usage_count')[:15]
    
    # Get related tags based on story category
    related_tags = []
    if story.category:
        related_tags = Tag.objects.filter(
            stories__category=story.category
        ).exclude(
            id__in=story.tags.values_list('id', flat=True)
        ).annotate(
            story_count=Count('stories')
        ).order_by('-story_count')[:10]
    
    context = {
        'form': form,
        'story': story,
        'popular_tags': popular_tags,
        'related_tags': related_tags
    }
    
    return render(request, 'newsroom/story/story_manage_tags.html', context)

@staff_required
@editor_or_subeditor_required
def tag_detail(request, tag_id):
    """Show details of a tag and stories using it"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    # Get stories using this tag
    stories = tag.stories.all().order_by('-created_at')
    
    # Paginate stories
    paginator = Paginator(stories, 15)
    page_number = request.GET.get('page')
    stories_page = paginator.get_page(page_number)
    
    context = {
        'tag': tag,
        'stories': stories_page
    }
    
    return render(request, 'newsroom/tag/tag_detail.html', context)

def generate_story_actions(request, story):
    """Generate consistent action buttons for story pages"""
    actions = []
    user = request.user
    
    # Edit Story button - only show if story can be edited in its current state
    if can_edit_story_tag({"user": user}, story):
        # Don't show edit button for published stories unless user is editor/admin
        if story.status != 'PUBLISHED' or user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
            actions.append({
                'label': 'Edit Story',
                'url': reverse('newsroom:story_edit', kwargs={'story_id': story.id}),
                'icon': 'edit',
                'type': 'link',
                'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
            })
    
    # Manage Tags button (for editors and above) - only show for non-archived stories
    if user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN'] and story.status != 'ARCHIVED':
        actions.append({
            'label': 'Manage Tags',
            'url': reverse('newsroom:story_manage_tags', kwargs={'story_id': story.id}),
            'icon': 'tag',
            'type': 'link',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
        })
    
    # Submit for Review button (Interns only) - only show for draft stories
    if can_submit_for_review({"user": user}, story) and story.status == 'DRAFT':
        actions.append({
            'label': 'Submit for Review',
            'id': 'submit-for-review-btn',
            'url': '#',  # This is handled by JavaScript to open modal
            'icon': 'check-circle',
            'type': 'button',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-warning hover:bg-warning-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-warning'
        })
    
    # Complete Review button (Journalists reviewing) - only show for stories in review
    reviewer_task = Task.objects.filter(
        related_story=story,
        task_type='STORY_REVIEW',
        assigned_to=user,
        status__in=['PENDING', 'IN_PROGRESS']
    ).first()
    
    if reviewer_task and story.status == 'REVIEW':
        actions.append({
            'label': 'Complete Review',
            'url': reverse('newsroom:story_complete_review', kwargs={'story_id': story.id, 'task_id': reviewer_task.id}),
            'icon': 'check',
            'type': 'submit',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-success hover:bg-success-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success'
        })
    
    # Submit for Approval button - only show for stories in review
    if can_submit_for_approval({"user": user}, story) and story.status == 'REVIEW':
        actions.append({
            'label': 'Submit for Approval',
            'url': reverse('newsroom:story_submit_approval', kwargs={'story_id': story.id}),
            'icon': 'check',
            'type': 'submit',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-success hover:bg-success-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success'
        })
    
    # Approve Story button - only show for stories pending approval
    if can_approve_story({"user": user}, story) and story.status == 'PENDING_APPROVAL':
        actions.append({
            'label': 'Approve Story',
            'url': reverse('newsroom:story_approve', kwargs={'story_id': story.id}),
            'icon': 'check',
            'type': 'submit',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-success hover:bg-success-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success'
        })
    
    # Create Translation button - only show for approved English stories
    if (user.staff_role in ['EDITOR', 'SUPERADMIN', 'ADMIN'] and 
        story.status == 'APPROVED' and 
        story.language == 'ENGLISH' and 
        not story.is_translation):
        actions.append({
            'label': 'Create Translation',
            'url': reverse('newsroom:story_create_translation', kwargs={'story_id': story.id}),
            'icon': 'translate',
            'type': 'link',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
        })
    
    # Publish button - only show for approved stories
    if can_publish_story({"user": user}, story) and story.status == 'APPROVED':
        actions.append({
            'label': 'Publish',
            'url': reverse('newsroom:story_publish', kwargs={'story_id': story.id}),
            'icon': 'check',
            'type': 'submit',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-success hover:bg-success-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success'
        })
    
    # Delete button - only show for non-published stories
    if can_delete_story({"user": user}, story) and story.status != 'PUBLISHED':
        actions.append({
            'label': 'Delete Story',
            'url': reverse('newsroom:story_delete', kwargs={'story_id': story.id}),
            'icon': 'trash',
            'type': 'link',
            'class': 'inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-danger hover:bg-danger-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-danger'
        })
    
    return actions

@staff_required
@can_edit_story
def story_delete(request, story_id, story=None):
    """Delete a story"""
    if request.method == 'POST':
        # Check if user can delete this story
        if not story.can_be_deleted_by(request.user):
            raise PermissionDenied("You don't have permission to delete this story")
        
        # Delete the story
        story.delete()
        messages.success(request, "Story deleted successfully")
        return redirect('newsroom:story_list')
    
    context = {
        'story': story
    }
    
    return render(request, 'newsroom/story/story_delete.html', context)

@staff_required
@can_edit_story
def story_create_translation(request, story_id, story=None):
    """Create a new translation task for a story."""
    if not story:
        story = get_object_or_404(Story, id=story_id)
    
    # Check if the story is in a state where translations can be created
    if story.status not in ['APPROVED', 'PUBLISHED']:
        messages.error(request, 'Translations can only be created for approved or published stories.')
        return redirect('newsroom:story_detail', story_id=story.id)
    
    if request.method == 'POST':
        target_language = request.POST.get('language')
        if not target_language:
            messages.error(request, 'Please select a target language for translation.')
            return redirect('newsroom:story_create_translation', story_id=story.id)
        
        # Check if a translation task already exists for this language
        existing_task = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION',
            title__icontains=target_language
        ).exists()
        
        if existing_task:
            messages.error(request, f'A translation task for {target_language} already exists.')
            return redirect('newsroom:story_detail', story_id=story.id)
        
        # Get available translators (users with JOURNALIST role)
        translators = CustomUser.objects.filter(
            user_type=CustomUser.UserType.STAFF,
            staff_role='JOURNALIST'
        )
        
        if not translators.exists():
            messages.error(request, 'No translators available. Please ensure there are journalists in the system.')
            return redirect('newsroom:story_detail', story_id=story.id)
        
        # Create a new translation task
        task = Task.objects.create(
            title=f"Translate to {target_language}: {story.title}",
            description=f"Create a {target_language} translation of the story: {story.title}",
            task_type='TRANSLATION',
            status='PENDING',
            priority='MEDIUM',
            assigned_by=request.user,
            assigned_to=translators.first(),  # Assign to the first available translator
            related_story=story
        )
        
        messages.success(request, f'Translation task for {target_language} created successfully.')
        return redirect('newsroom:task_detail', task_id=task.id)
    
    # For GET requests, show the translation form
    context = {
        'story': story,
        'languages': [
            ('AFRIKAANS', 'Afrikaans'),
            ('XHOSA', 'Xhosa')
        ]
    }
    return render(request, 'newsroom/story/story_create_translation.html', context)