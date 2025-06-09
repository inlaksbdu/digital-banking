from rest_framework import serializers
from .models import ConversationThread, ConversationMessage


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = ["id", "sender", "content", "timestamp"]
        read_only_fields = ["id", "timestamp"]


class ConversationMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = ["sender", "content"]

    def validate_sender(self, value):
        if value not in ["human", "ai"]:
            raise serializers.ValidationError("Sender must be either 'human' or 'ai'")
        return value


class ConversationThreadSerializer(serializers.ModelSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = ConversationThread
        fields = [
            "id",
            "created_at",
            "updated_at",
            "message_count",
            "messages",
            "latest_message",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_latest_message(self, obj):
        latest = obj.messages.last()
        if latest:
            return {
                "id": str(latest.id),
                "sender": latest.sender,
                "content": latest.content[:100] + "..."
                if len(latest.content) > 100
                else latest.content,
                "timestamp": latest.timestamp.isoformat(),
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
        return obj.messages.count()

    def get_latest_message(self, obj):
        latest = obj.messages.last()
        if latest:
            return {
                "id": str(latest.id),
                "sender": latest.sender,
                "content": latest.content[:100] + "..."
                if len(latest.content) > 100
                else latest.content,
                "timestamp": latest.timestamp.isoformat(),
            }
        return None


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000, required=True)
    thread_id = serializers.UUIDField(required=False, allow_null=True)

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
