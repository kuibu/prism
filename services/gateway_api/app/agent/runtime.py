from __future__ import annotations

from collections import Counter


def summarize_messages(messages: list[str], *, max_items: int = 8) -> str:
    cleaned = [message.strip() for message in messages if message.strip()]
    if not cleaned:
        return "No messages found for summarization."

    selected = cleaned[:max_items]
    word_counter: Counter[str] = Counter()
    for message in selected:
        for token in message.lower().split():
            token = token.strip(".,!?;:()[]{}\"'")
            if len(token) >= 4:
                word_counter[token] += 1

    top_terms = [term for term, _ in word_counter.most_common(5)]
    bullets = "\n".join(f"- {item}" for item in selected[:5])
    terms_line = ", ".join(top_terms) if top_terms else "(none)"

    return (
        f"Summary of {len(selected)} recent messages:\n"
        f"{bullets}\n"
        f"Top terms: {terms_line}"
    )
