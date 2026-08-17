def resolve_strategy_pack_id(*, meets_minimum: bool) -> str:
    return "author-full" if meets_minimum else "blocked"
