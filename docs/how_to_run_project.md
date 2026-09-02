# How to Run the Project

## Industrial Equipment Performance & Maintenance Intelligence Analytics Platform

This guide explains how to run the project from dataset ingestion to Power BI export.

## 1. Prerequisites

Install:

- Python 3.10 or above
- Jupyter Notebook or JupyterLab
- SQLite command-line tool or any SQLite viewer
- Power BI Desktop

## 2. Open the Project Folder

From a terminal:

```bash
cd "C:\Users\Lavanya\Documents\Data analytics\Industrial Equipment Performance & Maintenance Intelligence Analytics Platform"
```

If cloned from GitHub:

```bash
git clone <your-github-repository-url>
cd "Industrial Equipment Performance & Maintenance Intelligence Analytics Platform"
```

## 3. Create a Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS or Linux:

```bash
python -m venv venv
source venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Add the Dataset

Download the AI4I 2020 Predictive Maintenance Dataset and place the CSV file in:

```text
data/raw/
```

Recommended file name:

```text
ai4i2020.csv
```

Expected path:

```text
data/raw/ai4i2020.csv
```

## 6. Run Data Ingestion

Run:

```bash
python src/data_ingestion/ingest_data.py --csv-path data/raw/ai4i2020.csv
```

This validates the dataset and creates:

```text
data/database/maintenance.db
```

The ingestion process creates and loads:

- `machine_raw`
- `machine_clean`
- `machine_analytics`

## 7. Create SQL Views

Run the analytics views script against the SQLite database.

If SQLite CLI is installed:

```bash
sqlite3 data/database/maintenance.db < sql/views/analytics_views.sql
```

If using a SQLite viewer:

1. Open `data/database/maintenance.db`.
2. Open `sql/views/analytics_views.sql`.
3. Run the full script.

This creates:

- `vw_machine_performance`
- `vw_failure_analysis`
- `vw_maintenance_kpis`
- `vw_risk_summary`
- `vw_powerbi_dataset`

## 8. Run Analysis Notebooks

Open Jupyter:

```bash
jupyter notebook
```

Run the notebooks in this order:

```text
notebooks/01_data_cleaning.ipynb
notebooks/02_business_eda.ipynb
notebooks/03_kpi_analysis.ipynb
notebooks/04_risk_scoring.ipynb
```

Notebook purpose:

| Notebook | Purpose |
|---|---|
| `01_data_cleaning.ipynb` | Data quality checks, validation, feature engineering, and clean table creation |
| `02_business_eda.ipynb` | Business-focused failure and maintenance analysis |
| `03_kpi_analysis.ipynb` | Executive maintenance KPI framework |
| `04_risk_scoring.ipynb` | Logistic Regression failure risk scoring engine |

## 9. Export Power BI Datasets

Run:

```bash
python scripts/export_powerbi.py
```

This creates Power BI-ready CSV files in:

```text
powerbi/data_exports/
```

Generated files:

```text
machine_dashboard_dataset.csv
kpi_summary.csv
risk_summary.csv
machine_type_summary.csv
```

## 10. Load Data into Power BI

Open Power BI Desktop.

Import these CSV files:

- `powerbi/data_exports/machine_dashboard_dataset.csv`
- `powerbi/data_exports/kpi_summary.csv`
- `powerbi/data_exports/risk_summary.csv`
- `powerbi/data_exports/machine_type_summary.csv`

Recommended table names:

- `machine_dashboard_dataset`
- `kpi_summary`
- `risk_summary`
- `machine_type_summary`

## 11. Build or Refresh the Dashboard

Use the dashboard specification:

```text
powerbi/dashboard_design.md
```

Dashboard pages:

1. Executive Overview
2. Operational Performance
3. Maintenance Risk Intelligence
4. Recommendations & Action Plan

If the Power BI dashboard is already built, click:

```text
Home > Refresh
```

after running:

```bash
python scripts/export_powerbi.py
```

## 12. Dashboard Screenshots

Saved dashboard visuals are available in:

```text
artifacts/visuals/dashboard_page1.png
artifacts/visuals/dashboard_page2.png
```

These can be used in GitHub README, portfolio pages, and interview presentations.

## 13. Common Issues and Fixes

### Dataset Not Found

Error:

```text
CSV file not found
```

Fix:

Make sure the dataset is saved as:

```text
data/raw/ai4i2020.csv
```

or pass the correct path:

```bash
python src/data_ingestion/ingest_data.py --csv-path path/to/your/file.csv
```

### SQLite Command Not Recognized

If this command fails:

```bash
sqlite3 data/database/maintenance.db < sql/views/analytics_views.sql
```

Use a SQLite viewer instead, or install SQLite CLI.

### Power BI Files Not Found

Run:

```bash
python scripts/export_powerbi.py
```

Then check:

```text
powerbi/data_exports/
```

### Notebook Cannot Find Database

Run ingestion first:

```bash
python src/data_ingestion/ingest_data.py --csv-path data/raw/ai4i2020.csv
```

Then rerun the notebook.

## 14. Recommended Full Run Order

Use this order for a clean full project run:

```bash
pip install -r requirements.txt
python src/data_ingestion/ingest_data.py --csv-path data/raw/ai4i2020.csv
sqlite3 data/database/maintenance.db < sql/views/analytics_views.sql
jupyter notebook
python scripts/export_powerbi.py
```

Then open Power BI and refresh the dashboard.

## 15. Important Notes

- `maintenance.db` is generated locally and should not be committed to GitHub.
- Raw CSV files should not be committed to GitHub unless the dataset license allows it.
- Power BI export CSVs are generated outputs and can be recreated by running `scripts/export_powerbi.py`.
- Dashboard screenshots are useful for GitHub and portfolio presentation.

