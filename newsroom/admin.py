# newsroom/admin.py
from django.contrib import admin
from .models import Category, Story, AudioClip, Task, TaskAttachment, TaskComment

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'content_type', 'created_at')
    list_filter = ('content_type', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

class AudioClipInline(admin.TabularInline):
    model = AudioClip
    extra = 1

class StoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'language', 'created_at', 'published_at')
    list_filter = ('status', 'category', 'language', 'religion_classification')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [AudioClipInline]
    readonly_fields = ('view_count', 'download_count')
    date_hierarchy = 'created_at'
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        # Once published, certain fields should be read-only
        if obj and obj.status == 'PUBLISHED':
            readonly_fields.extend(['title', 'slug', 'author'])
        return readonly_fields

class AudioClipAdmin(admin.ModelAdmin):
    list_display = ('title', 'story', 'uploaded_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description', 'story__title')

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 1

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_type', 'status', 'priority', 'assigned_to', 'due_date')
    list_filter = ('status', 'task_type', 'priority')
    search_fields = ('title', 'description')
    inlines = [TaskAttachmentInline, TaskCommentInline]
    readonly_fields = ('created_at', 'completed_at')
    date_hierarchy = 'created_at'

# Register models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Story, StoryAdmin)
admin.site.register(AudioClip, AudioClipAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskComment)
admin.site.register(TaskAttachment)