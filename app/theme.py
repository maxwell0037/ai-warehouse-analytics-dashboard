"""Shared chart styling constants and helpers.

Centralized so every section renders repeated encodings (e.g. warehouse
colors) identically instead of each section picking its own colors.
"""

# Fixed categorical order (dark-surface steps): slot 1 blue, slot 2 orange, slot 3 aqua.
CATEGORICAL_PALETTE = ["#3987e5", "#d95926", "#199e70"]
CRITICAL_COLOR = "#e66767"  # status "critical" - reserved for flagging, never a series color
WARNING_COLOR = "#fab219"  # status "warning" - reserved for flagging, never a series color
GRIDLINE_COLOR = "#2c2c2a"
AXIS_COLOR = "#383835"
MUTED_TEXT = "#898781"

# Sequential magnitude ramp (single hue, light -> dark blue), per the dataviz
# skill: the lightest step means "near zero" and is allowed to recede toward
# the dark surface; darkest step marks the highest value.
SEQUENTIAL_SCALE = [
    [0.0, "#cde2fb"],
    [0.15, "#9ec5f4"],
    [0.3, "#6da7ec"],
    [0.45, "#3987e5"],
    [0.6, "#2a78d6"],
    [0.75, "#1c5cab"],
    [0.9, "#104281"],
    [1.0, "#0d366b"],
]


def warehouse_color_map(warehouse_names) -> dict:
    """Assign each warehouse a stable color, independent of any one query's row order.

    Sorting names before assigning slots means the same warehouse gets the
    same color in every section, regardless of how that section's query
    happens to order its rows (e.g. by name vs. by a ranked metric).
    """
    stable_order = sorted(set(warehouse_names))
    return {name: CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)] for i, name in enumerate(stable_order)}
