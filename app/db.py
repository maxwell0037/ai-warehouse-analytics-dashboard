"""PostgreSQL connection and query execution helpers for the dashboard."""

from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@st.cache_resource
def get_engine() -> Engine:
    """Open (and cache for the session) a SQLAlchemy engine for the analytics database.

    Credentials come from .streamlit/secrets.toml, never hardcoded here.
    """
    creds = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg2://{creds['user']}:{creds.get('password', '')}"
        f"@{creds['host']}:{creds['port']}/{creds['dbname']}"
    )
    return create_engine(url)


def run_query(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    """Execute a read-only SQL query and return the result as a DataFrame."""
    engine = get_engine()
    return pd.read_sql(sql, engine, params=params)
