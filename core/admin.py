from django.contrib import admin
from .models import Upload, Photo, Question, Answer

class PhotoInline(admin.TabularInline):
    """Displays photos inline within the Upload admin page."""
    model = Photo
    extra = 0
    readonly_fields = ('id', 'filename', 'order', 'image', 'uploaded_at')
    can_delete = False

@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'total_photos', 'processed_photos', 'progress_percentage', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'progress_percentage')
    inlines = [PhotoInline]

class AnswerInline(admin.StackedInline):
    """Displays answers inline within the Question admin page."""
    model = Answer
    extra = 0
    readonly_fields = (
        'id', 'provider', 'model', 'content', 'status', 
        'error_message', 'tokens_used', 'response_time', 'created_at'
    )
    can_delete = False

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'photo_filename', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('photo__filename', 'extracted_text')
    readonly_fields = ('id', 'photo', 'extracted_text', 'error_message', 'created_at', 'updated_at')
    inlines = [AnswerInline]

    @admin.display(description='Photo Filename')
    def photo_filename(self, obj):
        return obj.photo.filename

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'upload', 'filename', 'order')
    search_fields = ('filename', 'upload__id')
    list_display_links = ('id', 'filename')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'provider', 'model', 'status', 'created_at')
    list_filter = ('provider', 'status')
    search_fields = ('question__id', 'content')