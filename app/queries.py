"""Loads the pre-tested KPI queries directly from sql/03_kpi_queries.sql.

The SQL text lives in exactly one place (that file). This module locates
each numbered query section and exposes it as a constant - it does not
rewrite or re-derive any SQL.
"""

import re
from pathlib import Path

_SQL_PATH = Path(__file__).resolve().parent.parent / "sql" / "03_kpi_queries.sql"
_SECTION_BOUNDARY = re.compile(r"-- ={10,}\n-- \d+\.\s.*?\n-- ={10,}\n")


def _load_sections() -> list[str]:
    """Split the KPI file into its 8 numbered query sections, in file order.

    Each returned string keeps its original business-question/description
    comments and is trimmed to end at that section's own closing semicolon,
    dropping any trailing usage-tip comments that follow it in the file.
    """
    raw = _SQL_PATH.read_text()
    chunks = _SECTION_BOUNDARY.split(raw)[1:]  # [0] is the file's top-of-file preamble
    sections = []
    for chunk in chunks:
        end = chunk.index(";") + 1
        sections.append(chunk[:end].strip())
    return sections


_SECTIONS = _load_sections()

DAILY_OPERATIONS_SUMMARY = _SECTIONS[0]
PRODUCTIVITY_BY_WAREHOUSE = _SECTIONS[1]
LABOR_COST_TREND = _SECTIONS[2]
CARRIER_PERFORMANCE_RANKING = _SECTIONS[3]
EXCEPTION_RATE_BY_WAREHOUSE = _SECTIONS[4]
MACHINE_DOWNTIME_SUMMARY = _SECTIONS[5]
LATE_SHIPMENT_RATE = _SECTIONS[6]
ROOT_CAUSE_LABOR_COST_INCREASE = _SECTIONS[7]
