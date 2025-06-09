from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    # Streaming chat endpoint
    path("chat/stream/", views.ChatStreamView.as_view(), name="chat_stream"),
    # Conversation management endpoints
    path(
        "conversations/", views.ConversationListView.as_view(), name="conversation_list"
    ),
    path(
        "conversations/create/",
        views.ConversationCreateView.as_view(),
        name="conversation_create",
    ),
    path(
        "conversations/<uuid:thread_id>/",
        views.ConversationDetailView.as_view(),
        name="conversation_detail",
    ),
    path(
        "conversations/<uuid:thread_id>/delete/",
        views.ConversationDeleteView.as_view(),
        name="conversation_delete",
    ),
]
