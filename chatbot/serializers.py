from rest_framework import serializers
from .models import ConversationThread, ConversationEntry


class ConversationEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationEntry
        fields = ["id", "human_message", "ai_message", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConversationThreadSerializer(serializers.ModelSerializer):
    entries = ConversationEntrySerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = ConversationThread
        fields = [
            "id",
            "created_at",
            "updated_at",
            "message_count",
            "entries",
            "latest_message",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.entries.count()

    def get_latest_message(self, obj):
        latest = obj.entries.last()
        if latest:
            return {
                "id": str(latest.id),
                "human_message": latest.human_message,
                "ai_message": latest.ai_message,
                "created_at": latest.created_at.isoformat(),
            }
        return None


class ConversationThreadListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = ConversationThread
        fields = ["id", "created_at", "updated_at", "message_count", "latest_message"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.entries.count()

    def get_latest_message(self, obj):
        latest = obj.entries.last()
        if latest:
            return {
                "id": str(latest.id),
                "human_message": latest.human_message,
                "ai_message": latest.ai_message,
                "created_at": latest.created_at.isoformat(),
            }
        return None


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000, required=True)
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    user_longitude = serializers.FloatField(required=False, allow_null=True)
    user_latitude = serializers.FloatField(required=False, allow_null=True)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class ChatResponseSerializer(serializers.Serializer):
    thread_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    message = serializers.CharField()


class ConversationThreadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationThread
        fields = ["id", "created_at"]
        read_only_fields = ["id", "created_at"]
