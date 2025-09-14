# from typing import TypedDict, Optional, Dict, Any
# from typing_extensions import Annotated
# from langgraph.graph.message import add_messages

# class AgentState(TypedDict, total=False):
#     messages: Annotated[list, add_messages]
#     email: Optional[str]
#     intent: Optional[str]        # browse | add_to_cart | checkout | track_order | help
#     query: Optional[str]
#     filters: Optional[Dict[str, Any]]
#     last_items: Optional[list]   # results returned from menu tool

from typing import TypedDict, Optional, Dict, Any, List
from typing_extensions import Annotated
from langgraph.graph.message import add_messages

class CartItem(TypedDict, total=False):
    id: str
    name: str
    qty: int
    price: float          # unit price
    variant: Optional[str]
    addons: List[str]
    line_total: float

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_id: Optional[str]
    intent: Optional[str]          # greet | browse_menu | add_to_cart | show_cart
    filters: Optional[Dict[str, Any]]
    plan: Optional[Dict[str, Any]] # LLM planner output
    last_items: Optional[List[Dict[str, Any]]]  # results from menu tool
    cart: List[CartItem]
    cart_summary: Optional[Dict[str, Any]]
    welcomed: bool                 # show welcome once
