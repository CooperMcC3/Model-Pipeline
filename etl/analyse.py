"""
etl/analyse.py
Loads the cleaned CSV, runs exploratory data analysis, trains a
Random Forest regression model, and saves all outputs to disk.
"""
import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # Non-interactive backend — safe for scripts
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)


class DataAnalyser:
    """Performs EDA and predictive modelling on the cleaned sales data."""

    def __init__(self, config: dict) -> None:
        self.paths_cfg = config["paths"]
        self.model_cfg = config["model"]
        self.output_dir = Path(config["paths"]["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="muted")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_csv(self) -> pd.DataFrame:
        """Load the cleaned CSV produced by the transform step.

        Returns:
            DataFrame with order_date parsed as datetime.

        Raises:
            FileNotFoundError: If the CSV does not exist on disk.
        """
        csv_path = (
            Path(self.paths_cfg["data_dir"]) / self.paths_cfg["csv_filename"]
        )
        if not csv_path.exists():
            raise FileNotFoundError(f"Cleaned CSV not found: {csv_path}")

        df = pd.read_csv(csv_path, parse_dates=["order_date"])
        logger.info("Loaded %d rows from %s", len(df), csv_path)
        return df

    # ------------------------------------------------------------------
    # EDA
    # ------------------------------------------------------------------

    def generate_summary(self, df: pd.DataFrame) -> None:
        """Compute high-level statistics and save to summary.json."""
        summary = {
            "total_rows": int(len(df)),
            "total_revenue": round(float(df["revenue"].sum()), 2),
            "avg_order_value": round(float(df["revenue"].mean()), 2),
            "date_range": {
                "start": df["order_date"].min().strftime("%Y-%m-%d"),
                "end": df["order_date"].max().strftime("%Y-%m-%d"),
            },
            "revenue_by_region": (
                df.groupby("region")["revenue"].sum().round(2).to_dict()
            ),
            "revenue_by_category": (
                df.groupby("category")["revenue"].sum().round(2).to_dict()
            ),
            "top_5_products": (
                df.groupby("product")["revenue"]
                .sum()
                .nlargest(5)
                .round(2)
                .to_dict()
            ),
        }

        out_path = self.output_dir / "summary.json"
        with open(out_path, "w") as fh:
            json.dump(summary, fh, indent=2)
        logger.info("Summary statistics saved to %s", out_path)

    def plot_revenue_by_region(self, df: pd.DataFrame) -> None:
        """Bar chart — total revenue per region."""
        region_rev = (
            df.groupby("region")["revenue"].sum().sort_values(ascending=False)
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        region_rev.plot(
            kind="bar",
            ax=ax,
            color=sns.color_palette("muted", len(region_rev)),
        )
        ax.set_title("Total Revenue by Region", fontsize=14, fontweight="bold")
        ax.set_xlabel("Region")
        ax.set_ylabel("Revenue ($)")
        ax.tick_params(axis="x", rotation=0)
        plt.tight_layout()
        self._save_figure(fig, "revenue_by_region.png")

    def plot_monthly_trend(self, df: pd.DataFrame) -> None:
        """Line chart — monthly revenue over the full date range."""
        monthly = (
            df.groupby(df["order_date"].dt.to_period("M"))["revenue"]
            .sum()
            .reset_index()
        )
        monthly["order_date"] = monthly["order_date"].dt.to_timestamp()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(monthly["order_date"], monthly["revenue"], marker="o", linewidth=2)
        ax.fill_between(monthly["order_date"], monthly["revenue"], alpha=0.15)
        ax.set_title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
        ax.set_xlabel("Month")
        ax.set_ylabel("Revenue ($)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        self._save_figure(fig, "monthly_trend.png")

    def plot_category_breakdown(self, df: pd.DataFrame) -> None:
        """Horizontal bar chart — revenue by product category."""
        cat_rev = df.groupby("category")["revenue"].sum().sort_values()
        fig, ax = plt.subplots(figsize=(8, 4))
        cat_rev.plot(
            kind="barh",
            ax=ax,
            color=sns.color_palette("muted", len(cat_rev)),
        )
        ax.set_title("Revenue by Category", fontsize=14, fontweight="bold")
        ax.set_xlabel("Revenue ($)")
        ax.set_ylabel("Category")
        plt.tight_layout()
        self._save_figure(fig, "revenue_by_category.png")

    # ------------------------------------------------------------------
    # Modelling
    # ------------------------------------------------------------------

    def train_model(self, df: pd.DataFrame) -> None:
        """Train a Random Forest regressor to predict order revenue.

        Features: quantity, unit_price, month, day_of_week, quarter,
                  region (label-encoded), category (label-encoded).
        Target:   revenue

        Saves model_metrics.json and a feature importance plot.
        """
        logger.info("Preparing features for modelling...")
        df = df.copy()

        le_region = LabelEncoder()
        le_category = LabelEncoder()
        df["region_enc"] = le_region.fit_transform(df["region"])
        df["category_enc"] = le_category.fit_transform(df["category"])

        features = [
            "quantity", "unit_price", "month",
            "day_of_week", "quarter", "region_enc", "category_enc",
        ]
        target = "revenue"

        X, y = df[features], df[target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.model_cfg["test_size"],
            random_state=self.model_cfg["random_state"],
        )
        logger.info(
            "Train / test split: %d / %d samples", len(X_train), len(X_test)
        )

        model = RandomForestRegressor(
            n_estimators=self.model_cfg["n_estimators"],
            random_state=self.model_cfg["random_state"],
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = r2_score(y_test, y_pred)

        logger.info(
            "Model results — MAE: %.2f | RMSE: %.2f | R²: %.4f", mae, rmse, r2
        )

        metrics = {
            "model": "RandomForestRegressor",
            "features": features,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
        }
        metrics_path = self.output_dir / "model_metrics.json"
        with open(metrics_path, "w") as fh:
            json.dump(metrics, fh, indent=2)
        logger.info("Model metrics saved to %s", metrics_path)

        self._plot_feature_importance(model.feature_importances_, features)

    def _plot_feature_importance(
        self, importances: np.ndarray, feature_names: list
    ) -> None:
        """Horizontal bar chart — Random Forest feature importances."""
        series = (
            pd.Series(importances, index=feature_names).sort_values()
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        series.plot(
            kind="barh",
            ax=ax,
            color=sns.color_palette("Blues_r", len(series)),
        )
        ax.set_title(
            "Feature Importance (Random Forest)", fontsize=14, fontweight="bold"
        )
        ax.set_xlabel("Importance")
        plt.tight_layout()
        self._save_figure(fig, "feature_importance.png")

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run_analysis(self, df: pd.DataFrame) -> None:
        """Run the full EDA and modelling suite."""
        self.generate_summary(df)
        self.plot_revenue_by_region(df)
        self.plot_monthly_trend(df)
        self.plot_category_breakdown(df)
        self.train_model(df)
        logger.info("All analysis and modelling steps complete")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_figure(self, fig: plt.Figure, filename: str) -> None:
        """Save a matplotlib figure and close it."""
        out_path = self.output_dir / filename
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        logger.info("Saved plot: %s", out_path)
