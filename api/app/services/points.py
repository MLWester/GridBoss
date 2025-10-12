from __future__ import annotations

from collections.abc import Iterable

DEFAULT_F1_POINTS: dict[int, int] = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1,
}


def default_points_entries() -> list[tuple[int, int]]:
    """Return the default F1 points mapping as (position, points) pairs."""
    return sorted(DEFAULT_F1_POINTS.items(), key=lambda item: item[0])


def normalize_points_entries(entries: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Normalize user-provided point entries, ensuring sorted unique positions."""
    seen: set[int] = set()
    normalized: list[tuple[int, int]] = []
    for position, points in entries:
        if position in seen:
            raise ValueError("Duplicate position in points map")
        seen.add(position)
        normalized.append((position, points))
    normalized.sort(key=lambda item: item[0])
    return normalized


def build_points_map(entries: Iterable[tuple[int, int]]) -> dict[int, int]:
    """Convert normalized point entries into a lookup map."""
    return {position: points for position, points in entries}
