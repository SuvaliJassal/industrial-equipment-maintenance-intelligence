# Database Design

## Layer 1: Data Ingestion and Database Architecture

This layer creates the SQLite foundation for the Industrial Equipment Performance & Maintenance Intelligence Analytics Platform. It ingests the AI4I 2020 Predictive Maintenance Dataset, validates it, and stores it in a structured database named `maintenance.db`.

## Database

| Item | Design |
|---|---|
| Database engine | SQLite |
| Database file | `data/database/maintenance.db` |
| DDL script | `sql/ddl/create_tables.sql` |
| Ingestion script | `src/data_ingestion/ingest_data.py` |
| Database utility | `src/database/database_manager.py` |

## Source Dataset

The ingestion layer expects the AI4I 2020 Predictive Maintenance Dataset with the following source columns:

| Source Column | Description |
|---|---|
| UDI | Unique observation identifier. |
| Product ID | Product or machine identifier from the source dataset. |
| Type | Product quality or machine type category: `L`, `M`, or `H`. |
| Air temperature [K] | Ambient air temperature in Kelvin. |
| Process temperature [K] | Process temperature in Kelvin. |
| Rotational speed [rpm] | Machine rotational speed in revolutions per minute. |
| Torque [Nm] | Torque in Newton meters. |
| Tool wear [min] | Tool wear duration in minutes. |
| Machine failure | Binary target flag for machine failure. |
| TWF | Tool Wear Failure flag. |
| HDF | Heat Dissipation Failure flag. |
| PWF | Power Failure flag. |
| OSF | Overstrain Failure flag. |
| RNF | Random Failure flag. |

## Table Architecture

```mermaid
erDiagram
    machine_raw {
        INTEGER raw_record_id PK
        TEXT udi
        TEXT product_id
        TEXT machine_type
        TEXT air_temperature_k
        TEXT process_temperature_k
        TEXT rotational_speed_rpm
        TEXT torque_nm
        TEXT tool_wear_min
        TEXT machine_failure
        TEXT twf
        TEXT hdf
        TEXT pwf
        TEXT osf
        TEXT rnf
        TEXT source_file
        TEXT ingestion_timestamp
    }

    machine_clean {
        INTEGER observation_id PK
        TEXT product_id
        TEXT machine_type
        REAL air_temperature_k
        REAL process_temperature_k
        INTEGER rotational_speed_rpm
        REAL torque_nm
        INTEGER tool_wear_min
        INTEGER machine_failure
        INTEGER twf
        INTEGER hdf
        INTEGER pwf
        INTEGER osf
        INTEGER rnf
        TEXT source_file
        TEXT ingestion_timestamp
        TEXT created_at
    }

    machine_analytics {
        INTEGER analytics_id PK
        INTEGER observation_id FK
        TEXT product_id
        TEXT machine_type
        REAL air_temperature_k
        REAL process_temperature_k
        REAL temperature_difference_k
        INTEGER rotational_speed_rpm
        REAL torque_nm
        REAL mechanical_power_watts
        INTEGER tool_wear_min
        TEXT tool_wear_risk_level
        REAL operating_stress_score
        INTEGER machine_failure
        INTEGER failure_mode_count
        TEXT primary_failure_mode
        INTEGER twf
        INTEGER hdf
        INTEGER pwf
        INTEGER osf
        INTEGER rnf
        TEXT source_file
        TEXT ingestion_timestamp
        TEXT created_at
    }

    machine_clean ||--o| machine_analytics : "feeds"
```

## Why Each Table Exists

### `machine_raw`

`machine_raw` preserves the dataset as close to the incoming CSV as practical while using consistent database column names. All source measurement and flag fields are stored as text so the platform keeps a raw ingestion record before type conversion.

This table exists to support:

- Auditability of the original source data
- Reconciliation between raw CSV records and cleaned records
- Troubleshooting ingestion or transformation issues
- Evidence that validation and transformation were performed after landing the data

### `machine_clean`

`machine_clean` stores validated, typed, analysis-safe observations. It enforces core data quality rules through column types, primary keys, uniqueness rules, and check constraints.

This table exists to support:

- Reliable SQL analysis on clean numeric fields
- Consistent joins and filtering by observation, product, machine type, and failure flag
- Downstream feature engineering
- Power BI imports that need stable field names and types

### `machine_analytics`

`machine_analytics` stores derived features and reporting-ready maintenance intelligence fields. It includes engineered values such as temperature difference, mechanical power, tool wear risk, operating stress score, failure mode count, and primary failure mode.

This table exists to support:

- KPI calculation
- Exploratory analysis
- Power BI dashboarding
- Predictive maintenance feature preparation
- Business-friendly segmentation of maintenance risk

## Validation Controls

The ingestion layer performs the following checks before loading data:

| Validation | Purpose |
|---|---|
| CSV validation | Confirms the input exists, is a file, has a `.csv` extension, and is not empty. |
| Column validation | Confirms the source columns exactly match the expected AI4I 2020 schema. |
| Data type validation | Converts numeric fields and rejects non-numeric values in numeric columns. |
| Null validation | Rejects records with missing values. |
| Duplicate checks | Rejects duplicate full rows, duplicate `UDI`, and duplicate `Product ID` values. |
| Domain validation | Confirms machine type values are `L`, `M`, or `H`. |
| Binary flag validation | Confirms failure and failure-mode columns contain only `0` or `1`. |
| Range validation | Confirms temperatures, speed, torque, and tool wear values are within valid numeric ranges. |
| Failure consistency review | Logs rows where the aggregate `machine_failure` flag and detailed failure-mode flags do not align. These are not rejected because the AI4I dataset is known to contain some label inconsistencies that should remain available for analysis. |

## Transaction Management

All table loads are executed inside one explicit SQLite transaction. If any insert fails, the transaction is rolled back and no partial dataset is committed.

The database manager also enables:

- Foreign key enforcement
- Write-ahead logging through SQLite WAL mode
- Atomic replacement or append loading
- Centralized error handling for database failures

## Ingestion Flow

```mermaid
flowchart TD
    A["AI4I CSV File"] --> B["Validate CSV Path and File Type"]
    B --> C["Read CSV with Pandas"]
    C --> D["Validate Expected Columns"]
    D --> E["Run Duplicate Checks"]
    E --> F["Validate Data Types and Domains"]
    F --> G["Create machine_raw DataFrame"]
    F --> H["Create machine_clean DataFrame"]
    H --> I["Create machine_analytics DataFrame"]
    G --> J["Initialize SQLite Schema"]
    H --> J
    I --> J
    J --> K["Load All Tables in One Transaction"]
    K --> L["maintenance.db"]
```

## Operational Usage

After placing the AI4I CSV file in `data/raw`, run ingestion from the project root:

```bash
python src/data_ingestion/ingest_data.py --csv-path data/raw/ai4i2020.csv
```

By default, the script creates or updates:

```text
data/database/maintenance.db
```

To append instead of replacing existing table rows:

```bash
python src/data_ingestion/ingest_data.py --csv-path data/raw/ai4i2020.csv --append
```
