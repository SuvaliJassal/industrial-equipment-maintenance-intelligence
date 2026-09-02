"""Ingest the AI4I 2020 Predictive Maintenance dataset into SQLite."""

from __future__ import annotations

import argparse
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database_manager import DatabaseManager


LOGGER = logging.getLogger("maintenance_ingestion")

EXPECTED_COLUMNS = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

COLUMN_RENAME_MAP = {
    "UDI": "observation_id",
    "Product ID": "product_id",
    "Type": "machine_type",
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
    "TWF": "twf",
    "HDF": "hdf",
    "PWF": "pwf",
    "OSF": "osf",
    "RNF": "rnf",
}

INTEGER_COLUMNS = [
    "observation_id",
    "rotational_speed_rpm",
    "tool_wear_min",
    "machine_failure",
    "twf",
    "hdf",
    "pwf",
    "osf",
    "rnf",
]

FLOAT_COLUMNS = [
    "air_temperature_k",
    "process_temperature_k",
    "torque_nm",
]

BINARY_COLUMNS = [
    "machine_failure",
    "twf",
    "hdf",
    "pwf",
    "osf",
    "rnf",
]

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "maintenance.db"
DEFAULT_DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "create_tables.sql"


class DataValidationError(ValueError):
    """Raised when the source CSV fails ingestion validation."""


def configure_logging() -> None:
    """Configure console logging for ingestion runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def validate_csv_file(csv_path: Path) -> None:
    """Validate that the source path is a readable CSV file."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if not csv_path.is_file():
        raise DataValidationError(f"CSV path is not a file: {csv_path}")
    if csv_path.suffix.lower() != ".csv":
        raise DataValidationError(f"Expected a .csv file, received: {csv_path.name}")
    if csv_path.stat().st_size == 0:
        raise DataValidationError(f"CSV file is empty: {csv_path}")


def read_csv(csv_path: Path) -> pd.DataFrame:
    """Read the AI4I CSV file with parser-level error handling."""
    validate_csv_file(csv_path)
    try:
        dataframe = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError(f"CSV file contains no data: {csv_path}") from exc
    except pd.errors.ParserError as exc:
        raise DataValidationError(f"CSV parsing failed for {csv_path}: {exc}") from exc

    if dataframe.empty:
        raise DataValidationError("CSV loaded successfully but contains zero rows.")

    LOGGER.info("Loaded CSV with %d rows and %d columns.", len(dataframe), len(dataframe.columns))
    return dataframe


def validate_columns(dataframe: pd.DataFrame) -> None:
    """Validate the dataset has the exact AI4I 2020 expected schema."""
    actual_columns = list(dataframe.columns)
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in actual_columns]
    unexpected_columns = [column for column in actual_columns if column not in EXPECTED_COLUMNS]

    if missing_columns or unexpected_columns:
        raise DataValidationError(
            "CSV column validation failed. "
            f"Missing columns: {missing_columns}. "
            f"Unexpected columns: {unexpected_columns}."
        )

    if actual_columns != EXPECTED_COLUMNS:
        raise DataValidationError(
            "CSV columns are present but not in the expected order. "
            f"Expected: {EXPECTED_COLUMNS}. Actual: {actual_columns}."
        )


def validate_duplicates(dataframe: pd.DataFrame) -> None:
    """Detect duplicate records and duplicate business keys."""
    duplicate_row_count = int(dataframe.duplicated().sum())
    duplicate_udi_count = int(dataframe.duplicated(subset=["UDI"]).sum())
    duplicate_product_count = int(dataframe.duplicated(subset=["Product ID"]).sum())

    validation_messages = []
    if duplicate_row_count:
        validation_messages.append(f"duplicate full rows={duplicate_row_count}")
    if duplicate_udi_count:
        validation_messages.append(f"duplicate UDI values={duplicate_udi_count}")
    if duplicate_product_count:
        validation_messages.append(f"duplicate Product ID values={duplicate_product_count}")

    if validation_messages:
        raise DataValidationError("Duplicate validation failed: " + ", ".join(validation_messages))


def validate_and_clean_types(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate AI4I data types and return a strongly typed clean dataframe."""
    clean = dataframe.rename(columns=COLUMN_RENAME_MAP).copy()

    if clean.isna().any().any():
        null_counts = clean.isna().sum()
        failing_columns = null_counts[null_counts > 0].to_dict()
        raise DataValidationError(f"Null value validation failed: {failing_columns}")

    clean["product_id"] = clean["product_id"].astype(str).str.strip()
    clean["machine_type"] = clean["machine_type"].astype(str).str.strip()

    if (clean["product_id"] == "").any():
        raise DataValidationError("Product ID contains blank values.")

    invalid_machine_types = sorted(set(clean.loc[~clean["machine_type"].isin(["L", "M", "H"]), "machine_type"]))
    if invalid_machine_types:
        raise DataValidationError(f"Invalid machine Type values: {invalid_machine_types}")

    for column in INTEGER_COLUMNS + FLOAT_COLUMNS:
        converted = pd.to_numeric(clean[column], errors="coerce")
        if converted.isna().any():
            invalid_count = int(converted.isna().sum())
            raise DataValidationError(f"Column {column} contains {invalid_count} non-numeric value(s).")
        clean[column] = converted

    for column in INTEGER_COLUMNS:
        non_integer_mask = clean[column] % 1 != 0
        if non_integer_mask.any():
            raise DataValidationError(f"Column {column} contains non-integer numeric values.")
        clean[column] = clean[column].astype("int64")

    for column in FLOAT_COLUMNS:
        clean[column] = clean[column].astype("float64")

    validate_value_ranges(clean)
    return clean


def validate_value_ranges(clean: pd.DataFrame) -> None:
    """Validate domain ranges for sensor, operating, and target fields."""
    checks = {
        "observation_id must be positive": clean["observation_id"] > 0,
        "air_temperature_k must be positive": clean["air_temperature_k"] > 0,
        "process_temperature_k must be positive": clean["process_temperature_k"] > 0,
        "rotational_speed_rpm must be positive": clean["rotational_speed_rpm"] > 0,
        "torque_nm must be non-negative": clean["torque_nm"] >= 0,
        "tool_wear_min must be non-negative": clean["tool_wear_min"] >= 0,
    }

    failures = [message for message, mask in checks.items() if not bool(mask.all())]
    if failures:
        raise DataValidationError("Value range validation failed: " + "; ".join(failures))

    for column in BINARY_COLUMNS:
        invalid_values = sorted(set(clean.loc[~clean[column].isin([0, 1]), column].tolist()))
        if invalid_values:
            raise DataValidationError(f"Column {column} must contain only 0 or 1. Found: {invalid_values}")

    failure_mode_sum = clean[["twf", "hdf", "pwf", "osf", "rnf"]].sum(axis=1)
    aggregate_without_mode = int(((clean["machine_failure"] == 1) & (failure_mode_sum == 0)).sum())
    mode_without_aggregate = int(((clean["machine_failure"] == 0) & (failure_mode_sum > 0)).sum())
    if aggregate_without_mode or mode_without_aggregate:
        LOGGER.warning(
            "Failure label consistency warning: %d row(s) have machine_failure=1 with no failure mode; "
            "%d row(s) have failure mode flags with machine_failure=0.",
            aggregate_without_mode,
            mode_without_aggregate,
        )


def build_raw_table(dataframe: pd.DataFrame, source_file: str, ingestion_timestamp: str) -> pd.DataFrame:
    """Build source-preserving raw records for machine_raw."""
    raw = dataframe.rename(columns=COLUMN_RENAME_MAP).copy()
    raw.insert(0, "udi", raw.pop("observation_id").astype(str))

    for column in [
        "air_temperature_k",
        "process_temperature_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
        "machine_failure",
        "twf",
        "hdf",
        "pwf",
        "osf",
        "rnf",
    ]:
        raw[column] = raw[column].astype(str)

    raw["source_file"] = source_file
    raw["ingestion_timestamp"] = ingestion_timestamp
    return raw[
        [
            "udi",
            "product_id",
            "machine_type",
            "air_temperature_k",
            "process_temperature_k",
            "rotational_speed_rpm",
            "torque_nm",
            "tool_wear_min",
            "machine_failure",
            "twf",
            "hdf",
            "pwf",
            "osf",
            "rnf",
            "source_file",
            "ingestion_timestamp",
        ]
    ]


def build_clean_table(clean: pd.DataFrame, source_file: str, ingestion_timestamp: str) -> pd.DataFrame:
    """Build validated and typed records for machine_clean."""
    clean_table = clean.copy()
    clean_table["source_file"] = source_file
    clean_table["ingestion_timestamp"] = ingestion_timestamp
    return clean_table[
        [
            "observation_id",
            "product_id",
            "machine_type",
            "air_temperature_k",
            "process_temperature_k",
            "rotational_speed_rpm",
            "torque_nm",
            "tool_wear_min",
            "machine_failure",
            "twf",
            "hdf",
            "pwf",
            "osf",
            "rnf",
            "source_file",
            "ingestion_timestamp",
        ]
    ]


def build_analytics_table(clean: pd.DataFrame, source_file: str, ingestion_timestamp: str) -> pd.DataFrame:
    """Build analytics-ready records with derived maintenance intelligence fields."""
    analytics = clean.copy()
    analytics["temperature_difference_k"] = (
        analytics["process_temperature_k"] - analytics["air_temperature_k"]
    ).round(4)
    analytics["mechanical_power_watts"] = (
        analytics["torque_nm"] * analytics["rotational_speed_rpm"] * (2 * math.pi / 60)
    ).round(4)
    analytics["tool_wear_risk_level"] = analytics["tool_wear_min"].apply(classify_tool_wear_risk)
    analytics["failure_mode_count"] = analytics[["twf", "hdf", "pwf", "osf", "rnf"]].sum(axis=1).astype("int64")
    analytics["primary_failure_mode"] = analytics.apply(resolve_primary_failure_mode, axis=1)
    analytics["operating_stress_score"] = calculate_operating_stress_score(analytics)
    analytics["source_file"] = source_file
    analytics["ingestion_timestamp"] = ingestion_timestamp

    return analytics[
        [
            "observation_id",
            "product_id",
            "machine_type",
            "air_temperature_k",
            "process_temperature_k",
            "temperature_difference_k",
            "rotational_speed_rpm",
            "torque_nm",
            "mechanical_power_watts",
            "tool_wear_min",
            "tool_wear_risk_level",
            "operating_stress_score",
            "machine_failure",
            "failure_mode_count",
            "primary_failure_mode",
            "twf",
            "hdf",
            "pwf",
            "osf",
            "rnf",
            "source_file",
            "ingestion_timestamp",
        ]
    ]


def classify_tool_wear_risk(tool_wear_min: int) -> str:
    """Classify tool wear into maintenance risk bands."""
    if tool_wear_min >= 200:
        return "High"
    if tool_wear_min >= 120:
        return "Medium"
    return "Low"


def resolve_primary_failure_mode(row: pd.Series) -> str:
    """Resolve the first active AI4I failure mode for reporting."""
    failure_modes = [
        ("twf", "Tool Wear Failure"),
        ("hdf", "Heat Dissipation Failure"),
        ("pwf", "Power Failure"),
        ("osf", "Overstrain Failure"),
        ("rnf", "Random Failure"),
    ]
    for column, label in failure_modes:
        if int(row[column]) == 1:
            return label
    return "No Failure"


def calculate_operating_stress_score(dataframe: pd.DataFrame) -> pd.Series:
    """Create a normalized operating stress score from key machine signals."""
    stress_inputs = pd.DataFrame(
        {
            "temperature_difference_k": dataframe["process_temperature_k"] - dataframe["air_temperature_k"],
            "torque_nm": dataframe["torque_nm"],
            "tool_wear_min": dataframe["tool_wear_min"],
            "mechanical_power_watts": dataframe["torque_nm"]
            * dataframe["rotational_speed_rpm"]
            * (2 * math.pi / 60),
        }
    )

    normalized_parts = []
    for column in stress_inputs.columns:
        minimum = stress_inputs[column].min()
        maximum = stress_inputs[column].max()
        if maximum == minimum:
            normalized_parts.append(pd.Series(0.0, index=stress_inputs.index))
        else:
            normalized_parts.append((stress_inputs[column] - minimum) / (maximum - minimum))

    score = sum(normalized_parts) / len(normalized_parts)
    return (score * 100).round(4)


def ingest_dataset(
    csv_path: Path,
    database_path: Path = DEFAULT_DATABASE_PATH,
    ddl_path: Path = DEFAULT_DDL_PATH,
    replace_existing: bool = True,
) -> None:
    """Validate, transform, and load the AI4I dataset into SQLite."""
    LOGGER.info("Starting AI4I ingestion.")
    source_file = csv_path.name
    ingestion_timestamp = datetime.now(timezone.utc).isoformat()

    source_dataframe = read_csv(csv_path)
    validate_columns(source_dataframe)
    validate_duplicates(source_dataframe)
    clean_dataframe = validate_and_clean_types(source_dataframe)

    raw_table = build_raw_table(source_dataframe, source_file, ingestion_timestamp)
    clean_table = build_clean_table(clean_dataframe, source_file, ingestion_timestamp)
    analytics_table = build_analytics_table(clean_dataframe, source_file, ingestion_timestamp)

    database_manager = DatabaseManager(database_path)
    database_manager.initialize_schema(ddl_path)
    database_manager.load_dataframes(
        {
            "machine_raw": raw_table,
            "machine_clean": clean_table,
            "machine_analytics": analytics_table,
        },
        replace_existing=replace_existing,
    )

    LOGGER.info("Ingestion complete. Database: %s", database_path)
    LOGGER.info("machine_raw rows: %d", database_manager.get_row_count("machine_raw"))
    LOGGER.info("machine_clean rows: %d", database_manager.get_row_count("machine_clean"))
    LOGGER.info("machine_analytics rows: %d", database_manager.get_row_count("machine_analytics"))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest the AI4I 2020 Predictive Maintenance Dataset into SQLite."
    )
    parser.add_argument(
        "--csv-path",
        required=True,
        type=Path,
        help="Path to the AI4I 2020 Predictive Maintenance CSV file.",
    )
    parser.add_argument(
        "--database-path",
        default=DEFAULT_DATABASE_PATH,
        type=Path,
        help="Output SQLite database path. Defaults to data/database/maintenance.db.",
    )
    parser.add_argument(
        "--ddl-path",
        default=DEFAULT_DDL_PATH,
        type=Path,
        help="Path to the SQL DDL script.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing tables instead of replacing current rows.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    configure_logging()
    args = parse_args()

    try:
        ingest_dataset(
            csv_path=args.csv_path,
            database_path=args.database_path,
            ddl_path=args.ddl_path,
            replace_existing=not args.append,
        )
    except Exception as exc:
        LOGGER.exception("Ingestion failed.")
        raise SystemExit(f"Ingestion failed: {exc}") from exc


if __name__ == "__main__":
    main()
