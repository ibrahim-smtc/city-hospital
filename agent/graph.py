"""
LangGraph State Machine for the City Hospital AI Agent.

Wires together:
  - MessagesState: the shared state schema
  - LLM with tool binding (DeepSeek via ChatOpenAI)
  - ToolNode: auto-executes any tool the LLM calls
  - SqliteSaver: persistent SQLite-backed conversation memory per session
  - Conditional routing: LLM -> tools -> LLM -> ... -> END

The compiled `graph` object is imported by routers/chat.py to handle
incoming chat messages from the frontend.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.state import MessagesState
from agent.tools import tools
from agent.prompts import SYSTEM_PROMPT


# ─── LLM Initialization ────────────────────────────────────────────────────────
# Using Groq inference — free tier, ultra-fast, excellent tool-calling support.
# Get your free key at: https://console.groq.com
#
# Alternative: swap ChatGroq for ChatOpenAI if you have an OpenAI key:
#   from langchain_openai import ChatOpenAI
#   llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError(
        "DEEPSEEK_API_KEY is missing or not set in .env file.\n"
    )

llm = ChatOpenAI(
    model="deepseek-chat", 
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    temperature=0.2,
    max_tokens=1024,
)

# ─── Bind Tools to LLM ─────────────────────────────────────────────────────────
# After binding, the LLM knows about all 6 tools and can decide to call them.
# It will emit tool_calls instead of plain text when it needs real data.
llm_with_tools = llm.bind_tools(tools)


# ─── Graph Nodes ───────────────────────────────────────────────────────────────
def chatbot(state: MessagesState) -> dict:
    """
    Primary chatbot node.

    Prepends the system prompt to the conversation history and invokes the
    LLM. The LLM either:
      a) Returns a plain AIMessage (final answer to the user), OR
      b) Returns an AIMessage with `tool_calls` attached (wants to use a tool)

    LangGraph routes to `tools` node if tool_calls are present, otherwise ends.
    """
    messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages_with_system)
    return {"messages": [response]}


# ─── Build the Graph ───────────────────────────────────────────────────────────
workflow = StateGraph(MessagesState)

# Add the two nodes
workflow.add_node("chatbot", chatbot)
workflow.add_node("tools", ToolNode(tools))

# Entry point: always start at chatbot
workflow.add_edge(START, "chatbot")

# After chatbot runs:
# - If tool_calls exist → go to "tools" node
# - If no tool_calls → END (send response to user)
workflow.add_conditional_edges("chatbot", tools_condition)

# After tools finish executing → always return to chatbot to generate the final answer
workflow.add_edge("tools", "chatbot")

# ─── Compile with SQLite Persistence ──────────────────────────────────────────
# SqliteSaver stores conversation history in a real SQLite database file.
# This means chat history survives Python process restarts and server redeploys.
# On Railway, mount a Persistent Volume at /app/data/ to survive between deploys.

DB_DIR = ROOT_DIR / "data"
DB_DIR.mkdir(exist_ok=True)  # Create the data/ directory if it doesn't exist

memory = SqliteSaver.from_conn_string(str(DB_DIR / "langgraph_memory.db"))
graph = workflow.compile(checkpointer=memory)


# ─── Test Section ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CITY HOSPITAL LANGGRAPH AGENT - INTERACTIVE TEST")
    print("  Type your message (or 'exit' to quit)")
    print("=" * 60 + "\n")

    # Each run gets a unique thread_id for isolated conversation memory
    config = {"configurable": {"thread_id": "dev-test-session-1"}}

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            response = graph.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )

            # The last message in state is always the final AI response
            ai_message = response["messages"][-1]
            print(f"\nAria: {ai_message.content}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
