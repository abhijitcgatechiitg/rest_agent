from __future__ import annotations
import json, re
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .state import AgentState, CartItem
from .llm import get_claude
from .prompts import SYSTEM_PROMPT, PLANNER_PROMPT
from . import tools_client as tools

GENERIC_MENU_PHRASES = [
    "menu","show menu","show me the menu","show me menu","list menu","full menu","show all","all items"
]

def is_greeting(text: str) -> bool:
    t = (text or "").lower().strip()
    return t in {"hi","hello","hey","hi there"} or any(p in t for p in GENERIC_MENU_PHRASES)

def safe_json(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None

def compute_cart_summary(cart: List[CartItem]) -> Dict[str, Any]:
    subtotal = sum(ci.get("line_total", 0.0) for ci in cart)
    return {"subtotal": round(subtotal, 2), "num_items": sum(ci.get("qty", 0) for ci in cart)}

def resolve_item_by_name(name: str, filters: Optional[Dict[str, Any]]=None) -> Optional[Dict[str, Any]]:
    items = tools.search_menu(query=name, filters=filters or {})
    if not items:
        items = tools.search_menu(query=name, filters={})
    if not items:
        return None
    return items[0]

def add_to_cart(cart: List[CartItem], name: str, qty: int = 1, variant: Optional[str] = None, addons: Optional[List[str]] = None) -> Optional[CartItem]:
    item = resolve_item_by_name(name)
    if not item:
        return None
    unit = float(item.get("price", 0))
    add_on_total = 0.0
    selected_addons: List[str] = []
    if addons:
        addon_map = {a["name"].lower(): float(a["price"]) for a in item.get("addons", [])}
        for a in addons:
            key = a.lower().strip()
            if key in addon_map:
                add_on_total += addon_map[key]
                selected_addons.append(a)
    line_total = (unit + add_on_total) * (qty or 1)
    cart_item: CartItem = {
        "id": item["id"],
        "name": item["name"],
        "qty": int(qty or 1),
        "price": unit,
        "variant": variant,
        "addons": selected_addons,
        "line_total": round(line_total, 2),
    }
    cart.append(cart_item)
    return cart_item

# --------- Nodes ---------
def plan_node(state: AgentState) -> AgentState:
    llm = get_claude(0.0)  # change here for current claude(13/09
    # last human message
    user_text = ""
    for m in reversed(state.get("messages", [])):
        t = getattr(m, "type", None) or m.get("type")
        if t == "human":
            user_text = getattr(m, "content", None) or m.get("content")
            break

    # First-time greet
    if not state.get("welcomed", False) and is_greeting(user_text):
        state["plan"] = {"action": "greet", "query": None, "filters": {}, "items_to_add": []}
        state["intent"] = "greet"
        return state

    if llm is None:
        # Minimal fallback planner
        t = (user_text or "").lower()
        if "show cart" in t or "cart" in t:
            act = "show_cart"
        elif "add " in t:
            act = "add_to_cart"
        elif is_greeting(t):
            act = "greet"
        else:
            act = "browse_menu"
        state["plan"] = {"action": act, "query": None if is_greeting(t) else user_text, "filters": {}, "items_to_add": []}
        state["intent"] = act
        return state

    out = get_claude(0.0).invoke([SystemMessage(content=PLANNER_PROMPT), HumanMessage(content=user_text or "menu")])
    plan = safe_json(getattr(out, "content", "") if hasattr(out, "content") else out)
    if not plan or "action" not in plan:
        plan = {"action": "browse_menu", "query": None, "filters": {}, "items_to_add": []}
    state["plan"] = plan
    state["intent"] = plan.get("action")
    return state

def act_browse_node(state: AgentState) -> AgentState:
    plan = state.get("plan") or {}
    query = plan.get("query")
    filters = plan.get("filters") or {}
    if query is None or (isinstance(query, str) and is_greeting(query)):
        query = None
    try:
        items = tools.search_menu(query=query, filters=filters)
    except Exception:
        items = []
    if not items:
        try:
            items = tools.search_menu(query=None, filters={})
        except Exception:
            items = []
    state["filters"] = filters
    state["last_items"] = items
    return state

def act_add_node(state: AgentState) -> AgentState:
    plan = state.get("plan") or {}
    to_add = plan.get("items_to_add") or []
    cart = state.get("cart") or []
    for spec in to_add:
        if not spec.get("name"):
            continue
        add_to_cart(cart, name=spec["name"], qty=int(spec.get("qty") or 1),
                    variant=spec.get("variant"), addons=spec.get("addons") or [])
    state["cart"] = cart
    state["cart_summary"] = compute_cart_summary(cart)
    return state

def act_show_cart_node(state: AgentState) -> AgentState:
    cart = state.get("cart") or []
    state["cart_summary"] = compute_cart_summary(cart)
    return state

def respond_node(state: AgentState) -> AgentState:
    llm = get_claude(0.2)
    plan = state.get("plan") or {}
    action = plan.get("action", "browse_menu")
    items = state.get("last_items", []) or []
    cart = state.get("cart") or []
    summary = state.get("cart_summary") or {}
    welcomed = state.get("welcomed", False)

    # Build a grouped menu preview for LLM context
    def group_items(items: List[Dict[str, Any]]):
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            by_cat.setdefault(it.get("category","Other"), []).append(it)
        return by_cat

    # Find last user text (for LLM context)
    user_text = ""
    for m in reversed(state.get("messages", [])):
        t = getattr(m, "type", None) or m.get("type")
        if t == "human":
            user_text = getattr(m, "content", None) or m.get("content")
            break

    if llm is None:
        # Naive renderer — concise and friendly (no hard “no results”)
        lines = []
        if action in ("greet", "browse_menu"):
            if not welcomed and action == "greet":
                lines.append("Welcome! Here’s our menu (say things like ‘add 2 Margherita’ or ‘show cart’):")
            by_cat = group_items(items or tools.search_menu(None, {}))
            for cat in ["Pizza","Burger","Fries","Drinks","Dessert","Wrap","Bowl","Sides","Beverage"]:
                if cat in by_cat:
                    picks = by_cat[cat][:3]
                    if picks:
                        lines.append(f"\n{cat}:")
                        for it in picks:
                            lines.append(f"• {it.get('name')} — ₹{it.get('price')} ({cat})")
        elif action == "add_to_cart":
            lines.append("Added to cart:")
            for ci in cart[-len(plan.get("items_to_add", [])):]:
                add_str = (", +" + ", ".join(ci.get("addons", []))) if ci.get("addons") else ""
                v = f" [{ci.get('variant')}]" if ci.get("variant") else ""
                lines.append(f"• {ci['name']}{v} x{ci['qty']}{add_str} — ₹{ci['line_total']}")
            lines.append(f"\nSubtotal: ₹{summary.get('subtotal', 0)}  |  Items: {summary.get('num_items', 0)}")
        else:  # show_cart
            lines.append("Your cart:")
            for ci in cart:
                add_str = (", +" + ", ".join(ci.get("addons", []))) if ci.get("addons") else ""
                v = f" [{ci.get('variant')}]" if ci.get("variant") else ""
                lines.append(f"• {ci['name']}{v} x{ci['qty']}{add_str} — ₹{ci['line_total']}")
            lines.append(f"\nSubtotal: ₹{summary.get('subtotal', 0)}  |  Items: {summary.get('num_items', 0)}")
        text = "\n".join(lines).strip() or "Here are some popular picks to get started."
        state["messages"].append({"type": "ai", "content": text})
        if action == "greet":
            state["welcomed"] = True
        return state

    # LLM rendering (Claude)
    context_lines = []
    if action in ("greet","browse_menu"):
        if not welcomed and action == "greet":
            context_lines.append("WELCOME: greet the user briefly; then show menu preview and examples.")
        by_cat = group_items(items or tools.search_menu(None, {}))
        for cat in ["Pizza","Burger","Fries","Drinks","Dessert","Wrap","Bowl","Sides","Beverage"]:
            picks = by_cat.get(cat, [])[:3]
            if picks:
                context_lines.append(f"{cat}:")
                for it in picks:
                    context_lines.append(f"- {it.get('name')} | ₹{it.get('price')}")
    elif action in ("add_to_cart","show_cart"):
        context_lines.append("CURRENT CART:")
        for ci in cart:
            add_str = (", +" + ", ".join(ci.get("addons", []))) if ci.get("addons") else ""
            context_lines.append(f"{ci['name']} x{ci['qty']}{add_str} | line ₹{ci['line_total']}")
        context_lines.append(f"SUBTOTAL: ₹{summary.get('subtotal', 0)}  |  ITEMS: {summary.get('num_items', 0)}")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=("User: " + (user_text or "hi") + "\n\nContext:\n" + "\n".join(context_lines) + "\n\nRespond briefly.")),
    ]
    out = get_claude(0.2).invoke(messages)
    state["messages"].append(out if isinstance(out, AIMessage) else AIMessage(content=str(out)))
    if action == "greet":
        state["welcomed"] = True
    return state

# --------- Graph ---------
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan_node)
    graph.add_node("act_browse", act_browse_node)
    graph.add_node("act_add", act_add_node)
    graph.add_node("act_show_cart", act_show_cart_node)
    graph.add_node("respond", respond_node)

    def route(state: AgentState):
        intent = (state.get("plan") or {}).get("action", "browse_menu")
        if intent == "add_to_cart":
            return "act_add"
        if intent == "show_cart":
            return "act_show_cart"
        # greet and browse both fetch/preview menu
        return "act_browse"

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", route, path_map={
        "act_browse": "act_browse",
        "act_add": "act_add",
        "act_show_cart": "act_show_cart",
    })
    graph.add_edge("act_browse", "respond")
    graph.add_edge("act_add", "respond")
    graph.add_edge("act_show_cart", "respond")
    graph.add_edge("respond", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
