import operator
from typing import Annotated, Any, Dict, TypedDict

from loguru import logger
import orjson
from django.core.exceptions import ObjectDoesNotExist
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig, ensure_config
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from accounts.models import CustomUser
from cbs.models import BankAccount
from chatbot.assistant.prompt import SYSTEM_PROMPT, NON_CUSTOMER_PROMPT


class WorkflowState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_longitude: float | None
    user_latitude: float | None


class AssistantWorkflow:
    def __init__(self, llm: BaseChatModel, tools: list[BaseTool]):
        self.llm = llm
        self.tools = tools
        self.llm_with_tools = llm.bind_tools(tools)
        self.tool_node = ToolNode(tools)
        self.graph = None

    def call_llm(self, state: WorkflowState, config: RunnableConfig):
        system_prompt = self.get_customer_context(
            config, state.get("user_longitude", None), state.get("user_latitude", None)
        )
        messages = state["messages"]
        messages = [SystemMessage(content=system_prompt)] + messages
        return {"messages": [self.llm_with_tools.invoke(messages)]}

    def get_customer_context(
        self,
        config: RunnableConfig,
        user_longitude: float | None,
        user_latitude: float | None,
    ) -> str:
        user_id = None
        config = ensure_config(config)
        user_cfg = config.get("configurable", {}).get("user", {})
        user_id = user_cfg.get("id")
        if not user_id:
            raise ValueError("User ID not found")
        user = None
        try:
            logger.debug(f"User ID: {user_id}")
            user = CustomUser.objects.get(id=user_id)
        except (CustomUser.DoesNotExist, ObjectDoesNotExist):
            raise ValueError("User not found")

        account = BankAccount.objects.filter(user=user).all()

        if account:
            customer_name = str(user)
            account_number = "-\n".join(
                [
                    f"Account No: {account.account_number} - {account.account_category} - Is Default: {account.default}"
                    for account in account
                ]
            )
            customer_phone = str(user.phone_number) if user.phone_number else ""
            customer_email = user.email or ""
            preferred_language = getattr(user, "preferred_language", "English")
            return SYSTEM_PROMPT.format(
                customer_name=customer_name,
                account_number=account_number,
                customer_phone=customer_phone,
                customer_email=customer_email,
                preferred_language=preferred_language,
                user_longitude=user_longitude,
                user_latitude=user_latitude,
            )

        else:
            user_name = str(user)
            user_phone = str(user.phone_number) if user.phone_number else ""
            user_email = user.email or ""
            preferred_language = getattr(user, "preferred_language", "English")
            return NON_CUSTOMER_PROMPT.format(
                user_name=user_name,
                user_phone=user_phone,
                user_email=user_email,
                preferred_language=preferred_language,
                user_longitude=user_longitude,
                user_latitude=user_latitude,
            )

    def build_graph(self, checkpoint_saver: BaseCheckpointSaver):
        graph = StateGraph(WorkflowState)
        graph.add_node("chat", self.call_llm)
        graph.add_node("tools", self.tool_node)
        graph.set_entry_point("chat")
        graph.add_conditional_edges("chat", tools_condition)
        graph.add_edge("tools", "chat")
        self.graph = graph.compile(checkpointer=checkpoint_saver)

    def stream(
        self,
        human_message: str,
        user_longitude: float | None,
        user_latitude: float | None,
        config: RunnableConfig,
    ):
        if self.graph is None:
            raise ValueError("Graph not built")
        response: Dict[str, Any] = {"event": None, "data": None}
        for mode, part in self.graph.stream(
            {
                "messages": [HumanMessage(content=human_message)],
                "user_longitude": user_longitude,
                "user_latitude": user_latitude,
            },
            config=config,
            stream_mode=["messages"],
        ):
            if mode == "messages":
                seq = list(part)
                msg = seq[0]
                if isinstance(msg, ToolMessage):
                    try:
                        tool_call = orjson.loads(msg.content)  # type: ignore
                    except orjson.JSONDecodeError:
                        tool_call = (
                            msg.content
                            if "error" not in str(msg.content).lower()
                            else []
                        )
                    response["event"] = "tool_response"
                    response["data"] = tool_call
                elif isinstance(msg, AIMessageChunk):
                    if msg.content:
                        content = str(msg.content)
                        response["event"] = "llm"
                        response["data"] = content
                    else:
                        continue
                else:
                    continue
            elif mode == "updates":
                if (
                    isinstance(part, dict)
                    and "chat" in part
                    and isinstance(part["chat"], dict)
                    and "messages" in part["chat"]
                ):
                    messages = part["chat"]["messages"]
                    if messages and isinstance(messages, list):
                        last_message = messages[-1]
                        if (
                            isinstance(last_message, AIMessage)
                            and hasattr(last_message, "tool_calls")
                            and last_message.tool_calls
                        ):
                            tool_call = last_message.tool_calls[0]
                            response["event"] = "tool_call"
                            response["data"] = {
                                "name": tool_call.get("name"),
                                "args": tool_call.get("args"),
                            }
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
            yield response
