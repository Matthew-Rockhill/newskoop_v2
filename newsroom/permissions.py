# newsroom/permissions.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import CustomUser

def staff_required(view_func):
    """Decorator that ensures only staff users can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Decorator that ensures only admins and super admins can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        allowed_roles = ['SUPERADMIN', 'ADMIN']
        if request.user.staff_role not in allowed_roles:
            raise PermissionDenied("Only administrators can access this page")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def editor_required(view_func):
    """Decorator that ensures only editors and admins can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        allowed_roles = ['EDITOR', 'SUPERADMIN', 'ADMIN']
        if request.user.staff_role not in allowed_roles:
            raise PermissionDenied("Only editors and administrators can access this page")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def editor_or_subeditor_required(view_func):
    """Decorator that ensures only editors, sub-editors and admins can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        allowed_roles = ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']
        if request.user.staff_role not in allowed_roles:
            raise PermissionDenied("Only editors and sub-editors can access this page")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def publishing_rights_required(view_func):
    """Decorator that ensures only users with publishing rights can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        # Editors and Sub-Editors can publish content
        allowed_roles = ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']
        if request.user.staff_role not in allowed_roles:
            messages.error(request, "You don't have permission to publish content")
            return redirect('newsroom:story_list')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_edit_story(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        story_id = kwargs.get('story_id')
        if not story_id:
            raise ValueError("Story ID not provided")
        
        try:
            story = Story.objects.get(id=story_id)
        except Story.DoesNotExist:
            messages.error(request, "Story not found")
            return redirect('newsroom:story_list')
        
        # Rule 1: Editors/Admins can edit anything
        is_editor = request.user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']
        if is_editor:
            # Allow edit, but attach story to kwargs for the view
            kwargs['story'] = story
            return view_func(request, *args, **kwargs)
            
        # Rule 2: Author can edit if in DRAFT stage
        is_author = story.author == request.user
        if is_author and story.status == 'DRAFT':
            kwargs['story'] = story
            return view_func(request, *args, **kwargs)
            
        # Rule 3: Journalists can edit stories assigned to them for review
        has_review_task = Task.objects.filter(
            related_story=story,
            task_type='STORY_REVIEW',
            assigned_to=request.user,
            status__in=['PENDING', 'IN_PROGRESS']
        ).exists()
        
        if has_review_task and story.status == 'REVIEW':
            kwargs['story'] = story
            return view_func(request, *args, **kwargs)
        
        # No permission to edit
        messages.error(request, "You don't have permission to edit this story at its current stage")
        return redirect('newsroom:story_detail', story_id=story_id)
    
    return _wrapped_view

def can_manage_categories(view_func):
    """Decorator that ensures only users with category management rights can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        # Only editors and admins can manage categories
        allowed_roles = ['EDITOR', 'SUPERADMIN', 'ADMIN', 'SUB_EDITOR']
        if request.user.staff_role not in allowed_roles:
            messages.error(request, "You don't have permission to manage categories")
            return redirect('newsroom:dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_manage_task(view_func):
    """
    Decorator that ensures users can only manage tasks if:
    1. They created the task, or
    2. They are assigned to the task, or
    3. They have an editor/admin role
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        task_id = kwargs.get('task_id')
        if not task_id:
            raise ValueError("Task ID not provided")
        
        from .models import Task
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            messages.error(request, "Task not found")
            return redirect('newsroom:task_list')
        
        # Check permissions
        is_creator = task.assigned_by == request.user
        is_assignee = task.assigned_to == request.user
        has_admin_role = request.user.staff_role in ['EDITOR', 'SUPERADMIN', 'ADMIN']
        
        if not (is_creator or is_assignee or has_admin_role):
            messages.error(request, "You don't have permission to manage this task")
            return redirect('newsroom:task_detail', task_id=task_id)
        
        kwargs['task'] = task  # Add task to kwargs for the view
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def can_view_all_tasks(view_func):
    """Decorator that ensures only admins, editors can view all tasks"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        # Check if trying to view all tasks
        view_mode = request.GET.get('view', 'assigned')
        
        # If not admin/editor and trying to view all, redirect to assigned tasks
        if view_mode == 'all' and request.user.staff_role not in ['EDITOR', 'SUPERADMIN', 'ADMIN']:
            messages.info(request, "You can only view tasks assigned to you or created by you")
            return redirect(f"{request.path}?view=assigned")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def has_radio_access(user, story):
    """
    Check if a radio station user has access to a specific story
    based on their station's permissions and the story's category.
    """
    if user.user_type != CustomUser.UserType.RADIO:
        return False
    
    if not user.radio_station:
        return False
    
    station = user.radio_station
    
    # Check if the story is published
    if story.status != 'PUBLISHED':
        return False
    
    # Check language access
    if story.language == 'ENGLISH' and not station.access_english:
        return False
    elif story.language == 'AFRIKAANS' and not station.access_afrikaans:
        return False
    elif story.language == 'XHOSA' and not station.access_xhosa:
        return False
    
    # Check category access
    parent_category = story.category.parent or story.category
    content_type = parent_category.content_type
    
    if content_type == 'NEWS_STORIES' and not station.access_news_stories:
        return False
    elif content_type == 'NEWS_BULLETINS' and not station.access_news_bulletins:
        return False
    elif content_type == 'SPORT' and not station.access_sport:
        return False
    elif content_type == 'FINANCE' and not station.access_finance:
        return False
    elif content_type == 'SPECIALTY' and not station.access_specialty:
        return False
    
    # Check religion classification access
    if story.religion_classification == 'CHRISTIAN' and station.religion_access != 'GENERAL_PLUS_CHRISTIAN':
        return False
    elif story.religion_classification == 'MUSLIM' and station.religion_access != 'GENERAL_PLUS_MUSLIM':
        return False
    
    return True

def editor_or_subeditor_required(view_func):
    """Decorator that ensures only editors, sub-editors and admins can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.user_type != CustomUser.UserType.STAFF:
            raise PermissionDenied("Only staff users can access this page")
        
        allowed_roles = ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']
        if request.user.staff_role not in allowed_roles:
            raise PermissionDenied("Only editors and sub-editors can access this page")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view