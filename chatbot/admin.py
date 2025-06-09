from django.contrib import admin
from .models import ConversationThread, ConversationMessage


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at", "message_count")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "sender", "content_preview", "timestamp")
    list_filter = ("sender", "timestamp")
    search_fields = ("content", "thread__user__username")
    readonly_fields = ("id", "timestamp")

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content Preview"
