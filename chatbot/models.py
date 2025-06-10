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


class ConversationEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        ConversationThread, on_delete=models.CASCADE, related_name="entries"
    )
    human_message = models.TextField()
    ai_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entry {self.id} - Thread {self.thread.id}"

    class Meta:
        ordering = ["created_at"]


class Escalation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="escalations")
    issue_summary = models.TextField()
    is_urgent = models.BooleanField(default=False)
    customer_sentiment = models.CharField(
        max_length=20,
        choices=[
            ("angry", "Angry"),
            ("frustrated", "Frustrated"),
            ("neutral", "Neutral"),
            ("positive", "Positive"),
        ],
        default="neutral",
    )
    escalate_to = models.EmailField(max_length=254)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Escalation {self.id} - {self.user}"
