def clean_items(items):
    """Lowercase and de-duplicate items while preserving order."""
    seen, out = set(), []
    for i in items:
        k = i.lower()
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out
