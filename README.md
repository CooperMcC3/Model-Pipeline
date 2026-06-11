<<<<<<< HEAD
# Model-Pipeline
Simple ETL pipeline that brings in data, transforms and cleans, before modelling and gaining insight for decision making 
=======
# Interview Pipeline

A lightweight sales ETL pipeline that extracts sales data from a MySQL database, cleans and enriches it, then performs exploratory data analysis and trains a regression model.

## Project structure

- `pipeline.py` - pipeline entrypoint for extract, transform, and analyse steps
- `setup_db.py` - creates sample MySQL database/table and loads synthetic sales data
- `run_pipeline.sh` - helper script to prepare the environment and run the pipeline
- `config.yaml` - connection details, runtime paths, and model settings
- `etl/` - extraction, transformation, and analysis modules
- `data/` - cleaned CSV output path
- `outputs/` - analysis artifacts, plots, and metrics
- `logs/` - pipeline execution logs

## Requirements

- Python 3.8+
- MySQL server accessible using credentials from `config.yaml`
- `pip` or a Python virtual environment manager

## Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to match your MySQL connection details and preferred runtime paths.

Example config values:

- `database.host`: MySQL hostname
- `database.port`: MySQL port
- `database.user`: MySQL username
- `database.password`: MySQL password
- `database.database`: target database name
- `database.table`: source table name
- `paths.data_dir`: folder for cleaned CSV
- `paths.output_dir`: folder for analysis outputs
- `paths.log_dir`: folder for pipeline logs
- `paths.csv_filename`: cleaned CSV filename
- `model.test_size`: test split size
- `model.random_state`: random seed for reproducibility
- `model.n_estimators`: Random Forest tree count

## Running the pipeline

### Option 1: Using the shell runner

Make the script executable and run it:

```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

This script:

1. validates Python 3.8+
2. creates/activates `.venv`
3. installs dependencies
4. creates runtime directories
5. sets up the MySQL sample database
6. runs `pipeline.py`

### Option 2: Running manually

```bash
source .venv/bin/activate
python3 setup_db.py
python3 pipeline.py
```

## What the pipeline does

1. Extracts raw sales rows from MySQL using `etl/extract.py`
2. Cleans and transforms the data in `etl/transform.py`
   - drops duplicates
   - removes rows missing critical fields
   - fills missing unit prices
   - removes invalid quantities
   - adds revenue and date-based features
3. Loads the cleaned CSV and runs analysis in `etl/analyse.py`
   - saves `summary.json`
   - saves `model_metrics.json`
   - writes plots to `outputs/`

## Outputs

- `data/sales_cleaned.csv` - cleaned, feature-engineered sales data
- `outputs/summary.json` - summary statistics
- `outputs/model_metrics.json` - regression model metrics
- `outputs/revenue_by_region.png`
- `outputs/monthly_trend.png`
- `outputs/revenue_by_category.png`
- `outputs/feature_importance.png`
- `logs/pipeline_*.log` - pipeline execution log files

## Notes

- The project uses `pandas`, `SQLAlchemy`, `scikit-learn`, `matplotlib`, and `seaborn`.
- `setup_db.py` generates synthetic sales data with intentional dirty rows to demonstrate cleaning logic.
- If your MySQL server requires authentication or a different host configuration, update `config.yaml` accordingly.
>>>>>>> 651bb86 (Initial commit)
