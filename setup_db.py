"""
setup_db.py
One-time script to create the MySQL database, table, and populate it
with synthetic sales data — including intentional dirty records so the
transform step has real work to do.

Usage:
    python3 setup_db.py
"""
import logging
import random
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def generate_sample_data(n: int = 500) -> pd.DataFrame:
    """Generate synthetic sales rows with deliberate data quality issues.

    Dirty records introduced:
    - Every 20th row: quantity = -1 (invalid)
    - Every 30th row: unit_price = None (missing)
    - Every 50th row: product + category = None (missing critical fields)
    - First 10 rows duplicated at the end (duplicate records)

    Args:
        n: Number of base rows to generate before adding duplicates.

    Returns:
        DataFrame ready for insertion into MySQL.
    """
    np.random.seed(42)
    random.seed(42)

    # product -> (category, price_low, price_high)
    products = {
        "Laptop":     ("Electronics", 500,  2000),
        "Phone":      ("Electronics", 200,  1200),
        "Tablet":     ("Electronics", 150,  900),
        "Monitor":    ("Peripherals", 100,  700),
        "Keyboard":   ("Peripherals", 20,   150),
        "Mouse":      ("Peripherals", 10,   80),
        "Headphones": ("Audio",       30,   500),
    }
    regions = ["North", "South", "East", "West"]
    base_date = datetime(2023, 1, 1)

    rows = []
    for i in range(n):
        product_name = random.choice(list(products.keys()))
        category, low_price, high_price = products[product_name]
        quantity = int(np.random.randint(1, 20))
        unit_price = round(float(np.random.uniform(low_price, high_price)), 2)
        order_date = base_date + timedelta(days=int(np.random.randint(0, 364)))

        # --- introduce intentional dirty data ---
        if i % 20 == 0:
            quantity = -1        # invalid business value
        if i % 30 == 0:
            unit_price = None    # missing price
        if i % 50 == 0:
            product_name = None  # missing critical fields
            category = None

        rows.append({
            "order_id":    1000 + i + 1,
            "customer_id": int(np.random.randint(1, 100)),
            "product":     product_name,
            "category":    category,
            "quantity":    quantity,
            "unit_price":  unit_price,
            "order_date":  order_date.strftime("%Y-%m-%d"),
            "region":      random.choice(regions),
        })

    # Append exact duplicates of the first 10 rows
    rows.extend(rows[:10])
    logger.info(
        "Generated %d rows (%d base + 10 exact duplicates)", len(rows), n
    )
    return pd.DataFrame(rows)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{table}` (
    order_id    INT,
    customer_id INT          NOT NULL,
    product     VARCHAR(100),
    category    VARCHAR(100),
    quantity    INT,
    unit_price  DECIMAL(10, 2),
    order_date  DATE,
    region      VARCHAR(50)
)
"""


def setup_database(config: dict) -> None:
    """Create the database, (re)create the table, and load sample data.

    Args:
        config: Parsed config.yaml dictionary.
    """
    db = config["database"]

    # Step 1: create the database if it doesn't exist
    root_url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}"
    )
    try:
        root_engine = create_engine(root_url)
        with root_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db['database']}`"))
            conn.commit()
        root_engine.dispose()
        logger.info("Database '%s' is ready", db["database"])
    except SQLAlchemyError as exc:
        logger.error("Could not create database: %s", exc)
        sys.exit(1)

    # Step 2: connect to the target database and (re)create the table
    db_url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['database']}"
    )
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS `{db['table']}`"))
            conn.execute(
                text(CREATE_TABLE_SQL.format(table=db["table"]))
            )
            conn.commit()
        logger.info("Table '%s' created", db["table"])
    except SQLAlchemyError as exc:
        logger.error("Table setup failed: %s", exc)
        sys.exit(1)

    # Step 3: generate and insert sample data
    df = generate_sample_data()
    try:
        df.to_sql(db["table"], engine, if_exists="append", index=False)
        logger.info("Inserted %d rows into '%s'", len(df), db["table"])
    except SQLAlchemyError as exc:
        logger.error("Data insertion failed: %s", exc)
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    config = load_config()
    setup_database(config)
    logger.info("Database setup complete — ready to run the pipeline")
