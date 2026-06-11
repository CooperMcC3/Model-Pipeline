"""
etl/extract.py
Handles extraction of raw data from a MySQL database.
"""
import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class MySQLExtractor:
    """Connects to MySQL and extracts data as a pandas DataFrame."""

    def __init__(self, config: dict) -> None:
        self.db_cfg = config["database"]
        self.engine = None

    def connect(self) -> None:
        """Create and validate a SQLAlchemy engine for MySQL."""
        cfg = self.db_cfg
        url = (
            f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        )
        try:
            self.engine = create_engine(url, pool_pre_ping=True)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(
                "Connected to MySQL: %s@%s/%s",
                cfg["user"], cfg["host"], cfg["database"],
            )
        except SQLAlchemyError as exc:
            raise ConnectionError(f"Failed to connect to MySQL: {exc}") from exc

    def extract(self, query: str = None) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame.

        Args:
            query: Optional SQL string. Defaults to SELECT * FROM configured table.

        Returns:
            DataFrame containing the query results.

        Raises:
            RuntimeError: If called before connect().
            ValueError: If the query returns no rows.
        """
        if self.engine is None:
            raise RuntimeError("Not connected. Call connect() first.")

        table = self.db_cfg.get("table", "sales_data")
        sql = query or f"SELECT * FROM `{table}`"
        logger.info("Running query: %s", sql)

        try:
            df = pd.read_sql(sql, self.engine)
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Query execution failed: {exc}") from exc

        if df.empty:
            raise ValueError(f"No data returned from table '{table}'.")

        logger.info("Extracted %d rows x %d columns", len(df), len(df.columns))
        return df

    def close(self) -> None:
        """Dispose of the engine and release all connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("Database connection closed")
