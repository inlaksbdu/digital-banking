import time
from venv import logger

import orjson
from django.conf import settings
from django.db import transaction
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
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

from chatbot.assistant.tools.account_balance import AccountBalanceTool
from chatbot.assistant.tools.branches import BranchLocatorTool
from chatbot.assistant.tools.card_request import CardRequestTool
from chatbot.assistant.tools.complaints import ComplaintTool
from chatbot.assistant.tools.customer_accounts import CustomerAccountsTool
from chatbot.assistant.tools.escation import EscalationTool
from chatbot.assistant.workflow import AssistantWorkflow

from .models import ConversationEntry, ConversationThread
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
    ComplaintTool(),
    AccountBalanceTool(),
    EscalationTool(),
]


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

        logger.debug(f"Creating new thread for user {request.user}")

        with transaction.atomic():
            serializer.is_valid(raise_exception=True)
            message = serializer.validated_data["message"]  # type: ignore
            thread_id = serializer.validated_data.get("thread_id")  # type: ignore
            user_longitude = serializer.validated_data.get("user_longitude")  # type: ignore
            user_latitude = serializer.validated_data.get("user_latitude")  # type: ignore

            if thread_id:
                try:
                    thread = ConversationThread.objects.get(
                        id=thread_id, user=request.user
                    )
                except ConversationThread.DoesNotExist:
                    thread = ConversationThread.objects.create(user=request.user, id=thread_id)
            else:
                thread = ConversationThread.objects.create(user=request.user)

            pool = ConnectionPool(
                conninfo=settings.DB_URI,
                max_size=20,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                },
            )
            checkpointer = PostgresSaver(pool)  # type: ignore
            checkpointer.setup()
            agent = AssistantWorkflow(
                llm=llm,
                tools=tools,
            )
            agent.build_graph(checkpoint_saver=checkpointer)
            return StreamingHttpResponse(
                self._stream_response(
                    agent,
                    message,
                    str(thread.id),
                    request.user.id,
                    thread,
                    user_longitude,
                    user_latitude,
                ),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                },
            )

    def _stream_response(
        self,
        agent: AssistantWorkflow,
        message: str,
        thread_id: str,
        user_id: str,
        thread: ConversationThread,
        user_longitude: float | None,
        user_latitude: float | None,
    ):
        try:
            ai_response_content = ""
            for event in agent.stream(
                human_message=message,
                user_longitude=user_longitude,
                user_latitude=user_latitude,
                config=RunnableConfig(
                    configurable={
                        "user": {"id": user_id},
                        "thread_id": thread_id,
                    }
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
                            "data": event,
                        }
                    )
                    + b"\n"
                )

            ConversationEntry.objects.create(
                thread=thread,
                human_message=message,
                ai_message=ai_response_content or "Failed to generate response",
            )

        except Exception as e:
            yield (
                orjson.dumps(
                    {
                        "event": "error",
                        "id": str(time.time()),
                        "data": {"message": str(e)},
                    }
                )
                + b"\n"
            )


class ConversationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadListSerializer

    def get_queryset(self):  # type: ignore[override]
        if getattr(self, "swagger_fake_view", False):
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            user=self.request.user
        ).prefetch_related("entries")


class ConversationDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadSerializer
    lookup_field = "id"
    lookup_url_kwarg = "thread_id"

    def get_queryset(self):  # type: ignore[override]
        if getattr(self, "swagger_fake_view", False):
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            user=self.request.user
        ).prefetch_related("entries")


class ConversationDeleteView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThreadSerializer
    lookup_field = "id"
    lookup_url_kwarg = "thread_id"

    def get_queryset(self):  # type: ignore[override]
        if getattr(self, "swagger_fake_view", False):
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
