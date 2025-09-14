import requests

MENU_URL = "http://localhost:8001/tools/search_menu"
GET_ITEM_URL = "http://localhost:8001/tools/get_item"

def search_menu(query=None, filters=None, timeout=10):
    payload = {"query": query, "filters": filters or {}}
    r = requests.post(MENU_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def get_item(id: str, timeout=10):
    r = requests.get(GET_ITEM_URL, params={"id": id}, timeout=timeout)
    r.raise_for_status()
    return r.json()
