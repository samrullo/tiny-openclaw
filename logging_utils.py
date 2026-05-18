import json


def compact_json(value, max_chars=1000):
    try:
        text = json.dumps(value, default=str, ensure_ascii=False)
    except TypeError:
        text = str(value)

    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...<truncated {len(text) - max_chars} chars>"
