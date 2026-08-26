"""
State schema for the LangGraph agent.

MessagesState holds the entire conversation history as a list of messages.
The `add_messages` reducer ensures new messages are APPENDED to the list
rather than overwriting it on every node update.
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class MessagesState(TypedDict):
    """
    The single shared state object that flows through every node in the graph.

    Fields:
        messages: A growing list of HumanMessage, AIMessage, and ToolMessage
                  objects that represent the full conversation history.
                  `add_messages` is the reducer — it appends new messages
                  instead of replacing the whole list.
    """
    messages: Annotated[list, add_messages]
