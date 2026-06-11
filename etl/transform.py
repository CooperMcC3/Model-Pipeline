"""
etl/transform.py
Cleans, validates, and feature-engineers the raw sales DataFrame,
then persists the result as a CSV file.
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataTransformer:
    """Cleans and transforms a raw sales DataFrame."""

    # Columns that must be present and non-null for a row to be kept
    CRITICAL_COLS = ["product", "category", "order_date", "region"]

    def __init__(self, config: dict) -> None:
        self.paths_cfg = config["paths"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates, handle missing values, and validate data.

        Steps applied (in order):
        1. Drop exact duplicate rows.
        2. Drop rows missing any critical column.
        3. Fill missing unit_price with the per-category median
           (global median as fallback).
        4. Remove rows with quantity <= 0 (invalid business data).
        5. Enforce correct dtypes.

        Args:
            df: Raw DataFrame from the extraction step.

        Returns:
            Cleaned DataFrame with a reset index.

        Raises:
            ValueError: If the DataFrame is empty after cleaning.
        """
        original_len = len(df)
        logger.info("Clean started — input rows: %d", original_len)

        # Step 1: drop exact duplicates
        df = df.drop_duplicates()
        logger.info(
            "After deduplication: %d rows (removed %d)",
            len(df), original_len - len(df),
        )

        # Step 2: drop rows missing critical fields
        before = len(df)
        df = df.dropna(subset=self.CRITICAL_COLS)
        dropped = before - len(df)
        if dropped:
            logger.warning(
                "Dropped %d rows with null values in critical columns: %s",
                dropped, self.CRITICAL_COLS,
            )

        # Step 3: fill missing unit_price
        if df["unit_price"].isna().any():
            category_median = df.groupby("category")["unit_price"].transform("median")
            global_median = df["unit_price"].median()
            df["unit_price"] = (
                df["unit_price"]
                .fillna(category_median)
                .fillna(global_median)
            )
            logger.info("Filled missing unit_price with category/global median")

        # Step 4: remove invalid quantities
        before = len(df)
        df = df[df["quantity"] > 0]
        invalid = before - len(df)
        if invalid:
            logger.warning("Removed %d rows with quantity <= 0", invalid)

        # Step 5: enforce dtypes
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["unit_price"] = df["unit_price"].astype(float)
        df["quantity"] = df["quantity"].astype(int)

        if df.empty:
            raise ValueError("DataFrame is empty after cleaning — cannot continue.")

        logger.info(
            "Clean complete — output rows: %d (total removed: %d)",
            len(df), original_len - len(df),
        )
        return df.reset_index(drop=True)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer new features from the cleaned DataFrame.

        Adds: revenue, month, month_name, day_of_week, quarter.

        Args:
            df: Cleaned DataFrame.

        Returns:
            DataFrame with additional feature columns.
        """
        logger.info("Feature engineering started...")

        df = df.copy()
        df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
        df["month"] = df["order_date"].dt.month
        df["month_name"] = df["order_date"].dt.strftime("%b")
        df["day_of_week"] = df["order_date"].dt.dayofweek   # 0 = Monday
        df["quarter"] = df["order_date"].dt.quarter

        logger.info(
            "Added features: revenue, month, month_name, day_of_week, quarter"
        )
        return df

    def save_csv(self, df: pd.DataFrame) -> Path:
        """Persist the transformed DataFrame to a CSV file.

        Args:
            df: Transformed DataFrame.

        Returns:
            Path to the saved CSV file.
        """
        data_dir = Path(self.paths_cfg["data_dir"])
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / self.paths_cfg["csv_filename"]

        df.to_csv(csv_path, index=False)
        logger.info("Saved %d rows to %s", len(df), csv_path)
        return csv_path
