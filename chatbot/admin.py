from django.contrib import admin
from .models import ConversationThread, ConversationEntry, Escalation


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at", "message_count")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.entries.count()


@admin.register(ConversationEntry)
class ConversationEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "human_message", "ai_message", "created_at")
    list_filter = ("created_at",)
    search_fields = ("human_message", "ai_message", "thread__user__username")
    readonly_fields = ("id", "created_at")

    @admin.display(description="Content Preview")
    def content_preview(self, obj):
        return (
            obj.human_message[:100] + "..."
            if len(obj.human_message) > 100
            else obj.human_message
        )


@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "issue_summary",
        "is_urgent",
        "customer_sentiment",
        "escalate_to",
        "status",
        "created_at",
    )
    list_filter = ("is_urgent", "customer_sentiment", "status", "created_at")
    search_fields = ("user__username", "user__email", "issue_summary")
    readonly_fields = ("id", "created_at", "updated_at")
