from django import template
from django.db.models import Count
from collections import defaultdict

register = template.Library()

@register.filter
def regroup_by(queryset, attribute):
    """
    Regroups a queryset by a specific attribute, counting items.
    Returns a dictionary with attribute values as keys and counts as values.
    
    Example usage:
    {{ tasks|regroup_by:"status" }}
    """
    if not queryset:
        return {}
    
    result = defaultdict(int)
    
    # Count items by the requested attribute
    for item in queryset:
        value = getattr(item, attribute)
        result[value] += 1
    
    return dict(result)

@register.filter
def lookup(dictionary, key):
    """
    Gets a value from a dictionary by key.
    Returns 0 if key doesn't exist.
    
    Example usage:
    {{ task_counts|lookup:"PENDING" }}
    """
    return dictionary.get(key, 0)