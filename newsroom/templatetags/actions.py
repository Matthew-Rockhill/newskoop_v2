from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def get_story_actions(story, user):
    """Generate list of actions for a story based on user permissions"""
    actions = []
    
    # View action is always available
    actions.append({
        'label': 'View Story',
        'url': reverse('newsroom:story_detail', args=[story.id]),
        'type': 'link',
        'icon': 'eye'
    })
    
    # Edit action
    if user.user_type == 'STAFF' and (story.status != 'PUBLISHED' or 
        user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']):
        actions.append({
            'label': 'Edit Story',
            'url': reverse('newsroom:story_edit', args=[story.id]),
            'type': 'link',
            'icon': 'edit'
        })
    
    # Publish action
    if (user.user_type == 'STAFF' and 
        story.status in ['DRAFT', 'REVIEW', 'APPROVED'] and 
        user.staff_role in ['EDITOR', 'SUPERADMIN', 'ADMIN']):
        actions.append({
            'label': 'Publish Story',
            'url': reverse('newsroom:story_publish', args=[story.id]),
            'type': 'link',
            'icon': 'check'
        })
    
    # Download action
    if story.status == 'PUBLISHED':
        actions.append({
            'label': 'Download',
            'url': reverse('newsroom:story_download', args=[story.id]),
            'type': 'link',
            'icon': 'download'
        })
    
    return actions

@register.simple_tag
def get_user_actions(user_obj, current_user):
    """Generate list of actions for a user based on current user's permissions"""
    actions = []
    
    # If no user object is provided, only show create actions
    if user_obj is None:
        if current_user.staff_role in ['SUPERADMIN', 'ADMIN']:
            actions.append({
                'label': 'Create Staff User',
                'url': reverse('accounts:create_staff_user'),
                'type': 'link',
                'icon': 'plus'
            })
            actions.append({
                'label': 'Create Radio User',
                'url': reverse('accounts:create_radio_user'),
                'type': 'link',
                'icon': 'plus'
            })
        return actions
    
    # For specific user actions
    if current_user.staff_role in ['SUPERADMIN', 'ADMIN']:
        actions.append({
            'label': 'Edit User',
            'url': reverse('accounts:edit_user', args=[user_obj.id]),
            'type': 'link',
            'icon': 'edit'
        })
        
        # Reset password action
        actions.append({
            'label': 'Reset Password',
            'url': reverse('accounts:reset_password', args=[user_obj.id]),
            'type': 'link',
            'icon': 'key'
        })
        
        # Delete action
        actions.append({
            'label': 'Delete User',
            'url': reverse('accounts:delete_user_confirm', args=[user_obj.id]),
            'type': 'danger',
            'icon': 'trash',
            'confirm': 'Are you sure you want to delete this user? This action cannot be undone.'
        })
    
    return actions

@register.simple_tag
def get_station_actions(station, user):
    """Generate list of actions for a station based on user permissions"""
    actions = []
    
    # If no station is provided, only show create action
    if station is None:
        if user.staff_role in ['SUPERADMIN', 'ADMIN']:
            actions.append({
                'label': 'Create Station',
                'url': reverse('accounts:station_create'),
                'type': 'link',
                'icon': 'plus'
            })
        return actions
    
    # For specific station actions
    if user.staff_role in ['SUPERADMIN', 'ADMIN']:
        actions.append({
            'label': 'Edit Station',
            'url': reverse('accounts:station_edit', args=[station.id]),
            'type': 'link',
            'icon': 'edit'
        })
        
        actions.append({
            'label': 'Manage Users',
            'url': reverse('accounts:user_list') + f'?station={station.id}',
            'type': 'link',
            'icon': 'users'
        })
        
        actions.append({
            'label': 'Delete Station',
            'url': reverse('accounts:station_delete_confirm', args=[station.id]),
            'type': 'danger',
            'icon': 'trash',
            'confirm': 'Are you sure you want to delete this station? This action cannot be undone.'
        })
    
    return actions

@register.simple_tag
def get_profile_actions(user):
    """Generate list of actions for user profile"""
    actions = []
    
    actions.append({
        'label': 'Edit Profile',
        'url': reverse('accounts:profile'),
        'type': 'link',
        'icon': 'edit'
    })
    
    actions.append({
        'label': 'Change Password',
        'url': reverse('accounts:change_password'),
        'type': 'link',
        'icon': 'key'
    })
    
    return actions

@register.simple_tag
def get_tag_actions(tag, user):
    """Generate list of actions for a tag based on user permissions"""
    actions = []
    
    if user.staff_role in ['EDITOR', 'SUB_EDITOR', 'SUPERADMIN', 'ADMIN']:
        actions.append({
            'label': 'Edit Tag',
            'url': reverse('newsroom:tag_edit', args=[tag.id]),
            'type': 'link',
            'icon': 'edit'
        })
        
        actions.append({
            'label': 'Delete Tag',
            'url': reverse('newsroom:tag_delete', args=[tag.id]),
            'type': 'danger',
            'icon': 'trash',
            'confirm': 'Are you sure you want to delete this tag? This action cannot be undone.'
        })
    
    return actions 