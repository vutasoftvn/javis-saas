from collections.abc import Callable


def narrate_snapshot(snapshot: dict, narrator: Callable[[dict], str]) -> str:
    """Narrate figures already computed by domain services; never calculate here."""
    return narrator(snapshot)
