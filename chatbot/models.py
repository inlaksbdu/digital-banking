import uuid
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class ConversationThread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Thread {self.id} - {self.user.username}"

    class Meta:
        ordering = ["-updated_at"]


class ConversationMessage(models.Model):
    SENDER_CHOICES = [
        ("human", "Human"),
        ("ai", "AI"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        ConversationThread, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}..."

    class Meta:
        ordering = ["timestamp"]
