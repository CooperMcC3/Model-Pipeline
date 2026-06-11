"""
pipeline.py
Entry point for the Sales ETL pipeline.

Flow:
    [Extract]  MySQL -> raw DataFrame
    [Transform] clean + feature-engineer -> CSV
    [Analyse]  CSV -> EDA plots + ML model -> outputs/

Usage:
    python3 pipeline.py
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from etl.extract import MySQLExtractor
from etl.transform import DataTransformer
from etl.analyse import DataAnalyser


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Path) -> None:
    """Configure root logger to write to both file and stdout."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger(__name__).info(
        "Logging initialised — file: %s", log_file
    )


def load_config(path: str = "config.yaml") -> dict:
    """Load and return the YAML configuration file."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def create_directories(config: dict) -> None:
    """Ensure all runtime directories defined in config exist."""
    paths = config["paths"]
    for key in ("data_dir", "output_dir", "log_dir"):
        Path(paths[key]).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def run_extract(config: dict):
    """Step 1 — Connect to MySQL and return the raw DataFrame."""
    extractor = MySQLExtractor(config)
    try:
        extractor.connect()
        return extractor.extract()
    except Exception:
        raise
    finally:
        extractor.close()


def run_transform(config: dict, raw_df):
    """Step 2 — Clean, transform, and save to CSV. Returns the CSV path."""
    transformer = DataTransformer(config)
    cleaned_df = transformer.clean(raw_df)
    transformed_df = transformer.transform(cleaned_df)
    return transformer.save_csv(transformed_df)


def run_analyse(config: dict) -> None:
    """Step 3 — Load CSV, run EDA, train model, save all outputs."""
    analyser = DataAnalyser(config)
    df = analyser.load_csv()
    analyser.run_analysis(df)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    """Orchestrate the full ETL pipeline."""
    config = load_config()
    log_dir = Path(config["paths"]["log_dir"])
    setup_logging(log_dir)
    logger = logging.getLogger(__name__)

    create_directories(config)

    logger.info("=" * 60)
    logger.info("ETL Pipeline started")
    logger.info("=" * 60)

    # ---- EXTRACT ----
    logger.info("[STEP 1/3] EXTRACT")
    try:
        raw_df = run_extract(config)
    except Exception as exc:
        logger.critical("Extraction failed: %s", exc, exc_info=True)
        sys.exit(1)

    # ---- TRANSFORM ----
    logger.info("[STEP 2/3] TRANSFORM")
    try:
        csv_path = run_transform(config, raw_df)
        logger.info("Transformed data written to: %s", csv_path)
    except Exception as exc:
        logger.critical("Transform failed: %s", exc, exc_info=True)
        sys.exit(1)

    # ---- ANALYSE ----
    logger.info("[STEP 3/3] ANALYSE")
    try:
        run_analyse(config)
    except Exception as exc:
        logger.critical("Analysis failed: %s", exc, exc_info=True)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Pipeline completed successfully")
    logger.info("Outputs saved to: %s/", config["paths"]["output_dir"])
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
