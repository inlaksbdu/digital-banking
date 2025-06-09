import time

import orjson
from django.db import transaction
from django.http import StreamingHttpResponse
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from chatbot.assistant.tools.account_balance import AccountBalanceTool
from chatbot.assistant.tools.branches import BranchLocatorTool
from chatbot.assistant.tools.card_request import CardRequestTool
from chatbot.assistant.tools.customer_accounts import CustomerAccountsTool
from chatbot.assistant.workflow import AssistantWorkflow

from .models import ConversationMessage, ConversationThread
from .serializers import (
    ChatMessageSerializer,
    ConversationThreadCreateSerializer,
    ConversationThreadListSerializer,
    ConversationThreadSerializer,
)

llm = ChatOpenAI(model="gpt-4.1", temperature=0)
tools = [
    BranchLocatorTool(),
    CustomerAccountsTool(),
    CardRequestTool(),
    AccountBalanceTool(),
]
memory = InMemorySaver()
agent = AssistantWorkflow(
    llm,
    tools,
    "You are a helpful assistant that can help with customer accounts and branch locator.",
)
agent.build_graph(checkpoint_saver=memory)


@extend_schema_view(
    post=extend_schema(
        request=ChatMessageSerializer,
        responses=None,
        description="Streaming chat endpoint with SSE",
    )
)
class ChatStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        serializer = ChatMessageSerializer(data=request.data)

        with transaction.atomic():
            serializer.is_valid(raise_exception=True)
            message = serializer.validated_data["message"]  # type: ignore
            thread_id = serializer.validated_data.get("thread_id")  # type: ignore

            if thread_id:
                try:
                    thread = ConversationThread.objects.get(
                        id=thread_id, user=request.user
                    )
                except ConversationThread.DoesNotExist:
                    thread = ConversationThread.objects.create(user=request.user)
            else:
                thread = ConversationThread.objects.create(user=request.user)

            _ = ConversationMessage.objects.create(
                thread=thread, sender="human", content=message
            )

            return StreamingHttpResponse(
                self._stream_response(message, str(thread.id), request.user.id, thread),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                },
            )

    def _stream_response(self, message, thread_id, user_id, thread):
        try:
            ai_response_content = ""
            for event in agent.stream(
                message,
                RunnableConfig(
                    configurable={"user": {"id": str(user_id)}, "thread_id": thread_id}
                ),
            ):
                if event.get("event") == "llm":
                    ai_response_content += event.get("data", "")

                event_name = event.pop("event", "data")
                yield (
                    orjson.dumps(
                        {
                            "event": event_name,
                            "id": str(time.time()),
                            "data": orjson.dumps(event).decode("utf-8"),
                        }
                    )
                    + b"\n"
                )

            ConversationMessage.objects.create(
                thread=thread,
                sender="ai",
                content=ai_response_content or "Failed to generate response",
            )

        except Exception as e:
            yield (
                orjson.dumps(
                    {
                        "event": "error",
                        "id": str(time.time()),
                        "data": orjson.dumps({"message": str(e)}).decode("utf-8"),
                    }
                )
                + b"\n"
            )


class ConversationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadListSerializer

    def get_queryset(self):  # type: ignore[override]
        if getattr(
            self, "swagger_fake_view", False
        ):  # Prevent errors during schema generation
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            user=self.request.user
        ).prefetch_related("messages")


class ConversationDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadSerializer
    lookup_field = "id"
    lookup_url_kwarg = "thread_id"

    def get_queryset(self):  # type: ignore[override]
        if getattr(
            self, "swagger_fake_view", False
        ):  # Prevent errors during schema generation
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            user=self.request.user
        ).prefetch_related("messages")


class ConversationDeleteView(DestroyAPIView):
    """Delete a conversation thread"""

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadSerializer
    lookup_field = "id"
    lookup_url_kwarg = "thread_id"

    def get_queryset(self):  # type: ignore[override]
        if getattr(
            self, "swagger_fake_view", False
        ):  # Prevent errors during schema generation
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Conversation deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


class ConversationCreateView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
