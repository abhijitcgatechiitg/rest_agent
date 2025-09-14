# from langchain_core.messages import HumanMessage
# from .graph import build_graph
# from .state import AgentState

# def main():
#     print("\n🍕 Restaurant Agent (LangGraph + Claude). Type 'exit' to quit.\n")
#     app = build_graph()
#     state: AgentState = {"messages": []}
#     cfg = {"configurable": {"thread_id": "cli-session-1"}}
#     while True:
#         user = input("You: ").strip()
#         if user.lower() in {"exit", "quit"}:
#             break
#         state["messages"].append(HumanMessage(content=user))
#         state = app.invoke(state, config=cfg)
#         # Print last assistant message
#         msgs = state.get("messages", [])
#         last = msgs[-1] if msgs else None
#         text = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
#         print("Agent:", text, "\n")

# if __name__ == "__main__":
#     main()

from langchain_core.messages import HumanMessage
from .graph import build_graph
from .state import AgentState

def main():
    print("\n🍕 Restaurant Agent (LangGraph + MCP). Type 'exit' to quit.\n")
    app = build_graph()
    cfg = {"configurable": {"thread_id": "cli-session"}}
    state: AgentState = {"messages": [], "cart": [], "welcomed": False}

    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break
        state["messages"].append(HumanMessage(content=user))
        state = app.invoke(state, config=cfg)
        last = state.get("messages", [])[-1]
        print("Agent:", getattr(last, "content", None) or last.get("content"), "\n")

if __name__ == "__main__":
    main()
