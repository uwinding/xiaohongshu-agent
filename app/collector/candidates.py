from app.collector.search import SearchResult, Hotword


def parse_search_sorts(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    sorts = []
    seen = set()
    for item in raw_items:
        sort = str(item).strip()
        if not sort or sort in seen:
            continue
        seen.add(sort)
        sorts.append(sort)
    return sorts


def merge_search_result(
    target: SearchResult,
    source: SearchResult,
    seen_hotwords: set[str] | None = None,
    seen_cards: set[str] | None = None,
) -> SearchResult:
    seen_hotwords = seen_hotwords if seen_hotwords is not None else {h.text for h in target.hotwords}
    seen_cards = seen_cards if seen_cards is not None else {c.note_id for c in target.cards}

    for hotword in source.hotwords:
        if hotword.text in seen_hotwords:
            continue
        seen_hotwords.add(hotword.text)
        target.hotwords.append(Hotword(rank=len(target.hotwords) + 1, text=hotword.text))

    for card in source.cards:
        if card.note_id in seen_cards:
            continue
        seen_cards.add(card.note_id)
        target.cards.append(card)
    target.has_more = target.has_more or source.has_more
    return target
