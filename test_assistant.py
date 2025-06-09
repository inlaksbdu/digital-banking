import os
import sys
import django

sys.path.append("/Users/zak/digital-banking")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from langchain_openai import ChatOpenAI
from chatbot.assistant.workflow import AssistantWorkflow
from chatbot.assistant.tools.branches import BranchLocatorTool
from chatbot.assistant.tools.customer_accounts import CustomerAccountsTool
from chatbot.assistant.tools.card_request import CardRequestTool
from chatbot.assistant.tools.account_balance import AccountBalanceTool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig

llm = ChatOpenAI(model="gpt-4.1", temperature=0)
tools = [
    BranchLocatorTool(),
    CustomerAccountsTool(),
    CardRequestTool(),
    AccountBalanceTool(),
]
workflow = AssistantWorkflow(
    llm,
    tools,
    "You are a helpful assistant that can help with customer accounts and branch locator.",
)
memory = InMemorySaver()
graph = workflow.build_graph(checkpoint_saver=memory)

while (q := input("You: ")) != "q":
    for chunk in workflow.stream(
        q, RunnableConfig(configurable={"user": {"id": "5"}, "thread_id": "123"})
    ):
        print(chunk)
