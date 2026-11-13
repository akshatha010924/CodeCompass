"""Tiny demo service used to try CodeCompass."""
from utils.text import clean_items
from database import save_record

API_KEY = "sk-demo-1234567890abcdef"


def process_data(data):
    """Remove whitespace from each item and drop empty ones."""
    if not data:
        return []
    return [item.strip() for item in data if item.strip()]


def handle_request(payload, cache={}):
    try:
        items = process_data(payload.get("items"))
    except:
        pass
    cache[payload.get("id")] = items
    save_record(payload.get("id"), clean_items(items))
    return {"count": len(items)}
