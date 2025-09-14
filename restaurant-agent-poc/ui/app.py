import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph import build_graph
from agent.state import AgentState

st.set_page_config(page_title="Restaurant Agent (LangGraph + Claude)", page_icon="🍕")

if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
if "state" not in st.session_state:
    st.session_state.state: AgentState = {"messages": []}

st.title("🍕 Restaurant Ordering Agent — LangGraph + Claude")
user = st.chat_input("Ask for items, e.g., 'show veg pizzas under ₹300'")

if user:
    st.session_state.state["messages"].append(HumanMessage(content=user))
    st.session_state.state = st.session_state.graph_app.invoke(st.session_state.state)
    with st.chat_message("user"):
        st.write(user)

# show last assistant message
msgs = st.session_state.state.get("messages", [])
if msgs:
    last = msgs[-1]
    text = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
    if text:
        with st.chat_message("assistant"):
            st.write(text)