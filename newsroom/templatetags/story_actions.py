from django import template
from django.db.models import Q
from newsroom.models import Task, Story

register = template.Library()

@register.filter
def call_with(value, args):
    """Call a function with the given arguments"""
    if not value:
        return False
    if isinstance(args, str):
        args = [args]
    return value(*args)

@register.filter
def split(value, delimiter=','):
    """Split a string into a list using the specified delimiter"""
    if not value:
        return []
    return [x.strip() for x in value.split(delimiter)]

@register.simple_tag(takes_context=True)
def can_edit_story(context, story):
    """Check if current user can edit a story"""
    user = context['user']
    
    # Staff check
    if user.user_type != 'STAFF':
        return False
    
    # Authors can edit their own stories only if in DRAFT
    if story.author == user and story.status == 'DRAFT':
        return True
    
    # Editors can edit any story, including published ones
    if user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
        return True
    
    # Journalists can edit stories they're reviewing
    if user.staff_role == 'JOURNALIST':
        review_task = Task.objects.filter(
            related_story=story,
            task_type='STORY_REVIEW',
            assigned_to=user,
            status__in=['PENDING', 'IN_PROGRESS']
        ).exists()
        if review_task:
            return True
    
    return False

@register.simple_tag(takes_context=True)
def can_delete_story(context, story):
    """Check if current user can delete a story"""
    user = context['user']
    
    # Published stories cannot be deleted
    if story.status == 'PUBLISHED':
        return False
    
    # Interns can only delete their own draft stories
    if user.staff_role == 'INTERN':
        return story.author == user and story.status == 'DRAFT'
    
    # Journalists can delete their own stories
    if user.staff_role == 'JOURNALIST':
        return story.author == user and story.status in ['DRAFT', 'REVIEW']
    
    # Sub-editors and editors can delete any non-published story
    if user.staff_role in ['SUB_EDITOR', 'EDITOR', 'SUPERADMIN', 'ADMIN']:
        return story.status != 'PUBLISHED'
    
    return False

@register.simple_tag(takes_context=True)
def can_submit_for_review(context, story):
    """Check if current user can submit a story for review"""
    user = context['user']
    
    # Only interns can submit for review, and only their own draft stories
    return (
        user.user_type == 'STAFF' and
        user.staff_role == 'INTERN' and
        story.author == user and
        story.status == 'DRAFT'
    )

@register.simple_tag(takes_context=True)
def can_complete_review(context, story):
    """Check if current user can complete a review task"""
    user = context['user']
    
    # Only journalists assigned to review the story can complete review
    if user.user_type == 'STAFF' and user.staff_role == 'JOURNALIST':
        review_task = Task.objects.filter(
            related_story=story,
            task_type='STORY_REVIEW',
            assigned_to=user,
            status__in=['PENDING', 'IN_PROGRESS']
        ).exists()
        return review_task
    
    return False

@register.simple_tag(takes_context=True)
def can_submit_for_approval(context, story):
    """Check if current user can submit a story for approval"""
    user = context['user']
    
    # Must be staff
    if user.user_type != 'STAFF':
        return False
    
    # Must be draft or review status
    if story.status not in ['DRAFT', 'REVIEW']:
        return False
    
    # Journalists can submit their own stories directly for approval
    if user.staff_role == 'JOURNALIST' and story.author == user:
        return story.status == 'DRAFT'
    
    # Journalists can submit stories they've reviewed
    if user.staff_role == 'JOURNALIST':
        completed_review = Task.objects.filter(
            related_story=story,
            task_type='STORY_REVIEW',
            assigned_to=user,
            status__in=['PENDING', 'IN_PROGRESS', 'COMPLETED']
        ).exists()
        return completed_review
    
    # Authors of any role can submit their own stories
    if story.author == user:
        return True
    
    return False

@register.simple_tag(takes_context=True)
def can_approve_story(context, story):
    """Check if current user can approve a story"""
    user = context['user']
    
    # Only editors and admins can approve stories
    if user.user_type != 'STAFF' or user.staff_role not in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
        return False
    
    # Story must be pending approval
    if story.status != 'PENDING_APPROVAL':
        return False
    
    return True

@register.simple_tag(takes_context=True)
def can_publish_story(context, story):
    """Check if current user can publish a story"""
    user = context['user']
    
    # Only editors and admins can publish
    if user.user_type != 'STAFF' or user.staff_role not in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
        return False
    
    # Story must be approved
    if story.status != 'APPROVED':
        return False
    
    # For English stories, check translations
    if story.language == 'ENGLISH':
        # Check for pending translations
        pending_translations = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION',
            status__in=['PENDING', 'IN_PROGRESS', 'REVIEW']
        )
        if pending_translations.exists():
            return False
        
        # Check if all translations are approved
        completed_translations = Task.objects.filter(
            related_story=story,
            task_type='TRANSLATION',
            status='COMPLETED'
        )
        
        for task in completed_translations:
            # Find translated stories by this translator
            translated_stories = Story.objects.filter(
                author=task.assigned_to,
                is_translation=True,
                language__in=['AFRIKAANS', 'XHOSA']
            ).filter(
                Q(title__contains=story.title) | 
                Q(title__startswith=f"[{task.title.split(':')[0].strip().split(' ')[-1]}]")
            )
            
            # Check if any aren't approved
            not_approved = translated_stories.exclude(status='APPROVED').exists()
            if not_approved:
                return False
    
    return True

@register.simple_tag(takes_context=True)
def can_download_story(context, story):
    """Check if current user can download a story"""
    # Only published stories can be downloaded
    return story.status == 'PUBLISHED'

@register.simple_tag(takes_context=True)
def can_assign_xhosa_translation(context, story):
    """Check if current user can assign a Xhosa translation task"""
    user = context['user']
    
    # Only editors can assign
    if user.user_type != 'STAFF' or user.staff_role not in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
        return False
    
    # Story must be approved and in English
    if story.status != 'APPROVED' or story.language != 'ENGLISH':
        return False
    
    # Check if a Xhosa translation task already exists
    xhosa_task_exists = Task.objects.filter(
        related_story=story,
        task_type='TRANSLATION',
        title__icontains='Xhosa'
    ).exists()
    
    return not xhosa_task_exists