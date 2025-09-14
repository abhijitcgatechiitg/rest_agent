from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

app = FastAPI(title="Menu Tool Server (Fast‑MCP style)")

MENU_PATH = Path(__file__).resolve().parents[1] / "data" / "menu.json"
MENU = json.loads(MENU_PATH.read_text(encoding="utf-8"))

class SearchIn(BaseModel):
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None  # e.g. {"max_price":300, "tags":["veg"], "category":"Pizza"}

@app.get("/")
def root():
    return {"ok": True, "tool": "menu", "endpoints": ["/tools/search_menu", "/tools/get_item"]}

@app.post("/tools/search_menu")
def search_menu(payload: SearchIn):
    items = MENU.get("items", [])
    q = (payload.query or "").strip().lower()
    f = payload.filters or {}

    def text_match(it: Dict[str, Any]) -> bool:
        if not q:
            return True
        hay = " ".join([
            it.get("name", ""),
            it.get("category", ""),
            " ".join(it.get("tags", []))
        ]).lower()
        return q in hay

    def pass_filters(it: Dict[str, Any]) -> bool:
        # availability
        if not it.get("is_available", True):
            return False
        # price
        price = it.get("price", 10**9)
        if "max_price" in f and price > f["max_price"]:
            return False
        if "min_price" in f and price < f["min_price"]:
            return False
        # tags subset
        if "tags" in f:
            if not set(f["tags"]).issubset(set(it.get("tags", []))):
                return False
        # category
        if "category" in f and f["category"].lower() != it.get("category", "").lower():
            return False
        return True

    result = []
    for it in items:
        if text_match(it) and pass_filters(it):
            result.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "category": it.get("category"),
                "price": it.get("price"),
                "tags": it.get("tags", []),
                "addons": it.get("addons", []),
                "variants": it.get("variants", []),
                "is_available": it.get("is_available", True),
            })
    return result[:20]

@app.get("/tools/get_item")
def get_item(id: str):
    for it in MENU.get("items", []):
        if it.get("id") == id:
            return it
    return {"error": "not_found", "id": id}