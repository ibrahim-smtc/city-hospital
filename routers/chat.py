"""
routers/chat.py
---------------
API endpoint for hospital chatbot / AI assistant.

Endpoint:
  POST /chat  — send a chat message and receive an assistant response
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from models import ChatRequest, ChatResponse  # type: ignore # pyrefly: ignore [missing-import]

# Import the compiled LangGraph agent we just built!
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.graph import graph

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post(
    "",
    response_model=ChatResponse,
    summary="Send chat message",
    description="Send a message to Aria, the hospital AI assistant.",
)
def chat_endpoint(request: ChatRequest):
    """
    Process incoming chat inquiry using the LangGraph AI agent.
    """
    try:
        # Pass the frontend's session_id to LangGraph's SqliteSaver
        # This ensures each user has their own isolated conversation history!
        config = {"configurable": {"thread_id": request.session_id or "default-session"}}
        
        # Invoke the LangGraph agent
        response = graph.invoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
        )
        
        # The last message is Aria's final answer
        ai_reply = response["messages"][-1].content
        
        return ChatResponse(
            success=True,
            reply=ai_reply,
            session_id=request.session_id,
        )
    except Exception as e:
        return ChatResponse(
            success=False,
            reply=f"Error connecting to Aria: {str(e)}",
            session_id=request.session_id,
        )


@router.get(
    "/history",
    summary="Get chat history",
    description="Retrieve the full conversation history for a given session ID.",
)
def chat_history(session_id: str):
    """
    Returns the full conversation history from LangGraph's SQLite memory
    for a given session_id so the frontend can re-populate the chat on page load.
    """
    try:
        config = {"configurable": {"thread_id": session_id}}
        state = graph.get_state(config)
        
        messages = []
        if state and state.values.get("messages"):
            for msg in state.values["messages"]:
                role = "bot" if msg.type in ("ai", "assistant") else "user"
                # Only include non-empty text messages (skip tool calls, etc.)
                if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                    messages.append({"role": role, "content": msg.content})
        
        return {"success": True, "messages": messages}
    except Exception as e:
        return {"success": False, "messages": [], "error": str(e)}
