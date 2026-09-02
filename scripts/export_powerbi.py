"""Power BI export layer for maintenance intelligence reporting.

Business goal
-------------
Create Power BI-ready CSV datasets from the SQLite source of truth:
``data/database/maintenance.db``.

Power BI should not need heavy transformations. This script prepares curated
reporting tables with KPI, risk, reliability, and machine-level fields already
calculated.

Exports
-------
1. machine_dashboard_dataset.csv
   Purpose: Observation-level dashboard dataset for operational drilldown.
   Power BI use: Main fact table for machine-level visuals, slicers, failure
   analysis, risk views, and reliability score reporting.

2. kpi_summary.csv
   Purpose: Executive KPI scorecard dataset.
   Power BI use: KPI cards, scorecard tables, and leadership summary pages.

3. risk_summary.csv
   Purpose: Risk distribution summary by risk category.
   Power BI use: Risk distribution charts, action queues, and maintenance
   prioritization visuals.

4. machine_type_summary.csv
   Purpose: Machine type reliability and risk summary.
   Power BI use: Machine type comparison pages, matrix visuals, and segment
   prioritization views.

Column descriptions
-------------------
machine_dashboard_dataset.csv:
    Machine ID: Unique machine observation identifier.
    Machine Type: AI4I machine/product quality type.
    Product Type: Product identifier from the source dataset.
    Air Temperature: Ambient air temperature in Kelvin.
    Process Temperature: Process temperature in Kelvin.
    Temperature Difference: Process temperature minus air temperature.
    Rotational Speed: Machine rotational speed in RPM.
    Torque: Torque in Newton meters.
    Tool Wear: Tool wear duration in minutes.
    Mechanical Power: Engineered mechanical power estimate in watts.
    Operating Stress Score: Engineered operating stress score from 0 to 100.
    Failure Flag: Binary machine failure indicator.
    Failure Category: Primary failure mode.
    Failure Probability: Existing SQLite score if available; otherwise a
    rule-based maintenance risk probability proxy derived during export.
    Risk Category: Existing SQLite category if available; otherwise Low,
    Medium, or High Risk derived during export.
    Reliability Score: Existing SQLite score if available; otherwise a
    rule-based reliability score from 0 to 100 derived during export.

Risk score dependency behavior
------------------------------
If future SQLite tables contain persisted columns named ``failure_probability``,
``risk_category``, or ``reliability_score`` in ``machine_analytics``, the export
layer uses those values. If they do not exist, the script creates the fields
during export from available analytics fields: tool wear risk, operating stress,
torque, mechanical power, temperature difference, failure count, and failure
flag. This keeps Power BI exports usable even before a persisted scoring table
or serialized model output exists.

kpi_summary.csv:
    KPI Name: Executive KPI label.
    KPI Value: Formatted KPI value for reporting.
    Target Benchmark: Business benchmark used for scorecard status.
    Status: Good, Monitor, or Critical.
    Recommended Action: Maintenance action tied to the KPI.

risk_summary.csv:
    Risk Category: Low, Medium, or High Risk.
    Machine Count: Number of machine observations in the risk category.
    Percentage: Share of total machine observations.
    Recommended Action: Action guidance for the risk category.

machine_type_summary.csv:
    Machine Type: AI4I machine/product quality type.
    Failure Rate: Failure rate percentage by machine type.
    Average Tool Wear: Average tool wear in minutes.
    Average Operating Stress: Average operating stress score.
    Average Reliability Score: Average reliability score.
    Risk Category Distribution: Compact text summary of risk mix.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "maintenance.db"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "powerbi" / "data_exports"

LOGGER = logging.getLogger("powerbi_export")

REQUIRED_TABLES = ("machine_clean", "machine_analytics")


class PowerBIExportError(RuntimeError):
    """Raised when Power BI export generation fails."""


def configure_logging() -> None:
    """Configure structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def connect(database_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection with row-friendly settings."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def validate_database(database_path: Path) -> None:
    """Validate the SQLite database and required source tables."""
    if not database_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")
    if database_path.stat().st_size == 0:
        raise PowerBIExportError(f"SQLite database is empty: {database_path}")

    with connect(database_path) as connection:
        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view');"
            ).fetchall()
        }

        missing_tables = sorted(set(REQUIRED_TABLES) - existing_tables)
        if missing_tables:
            raise PowerBIExportError(f"Missing required source tables: {missing_tables}")

        for table_name in REQUIRED_TABLES:
            row_count = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name};").fetchone()[
                "row_count"
            ]
            if row_count == 0:
                raise PowerBIExportError(f"Required source table has no rows: {table_name}")


def read_sql(database_path: Path, query: str) -> pd.DataFrame:
    """Read a SQL query into a pandas dataframe."""
    with connect(database_path) as connection:
        return pd.read_sql_query(query, connection)


def get_table_columns(database_path: Path, table_name: str) -> set[str]:
    """Return column names for a SQLite table or view."""
    with connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table_name});").fetchall()
    return {row["name"] for row in rows}


def get_machine_base_dataset(database_path: Path) -> pd.DataFrame:
    """Create the base machine-level dataset from SQLite source tables."""
    analytics_columns = get_table_columns(database_path, "machine_analytics")
    optional_columns = {
        "failure_probability": "ma.failure_probability AS existing_failure_probability",
        "risk_category": "ma.risk_category AS existing_risk_category",
        "reliability_score": "ma.reliability_score AS existing_reliability_score",
    }
    optional_selects = [
        select_sql for column_name, select_sql in optional_columns.items() if column_name in analytics_columns
    ]
    optional_select_clause = ""
    if optional_selects:
        optional_select_clause = ",\n            " + ",\n            ".join(optional_selects)

    query = """
        SELECT
            mc.observation_id AS machine_id,
            mc.machine_type,
            mc.product_id AS product_type,
            ma.air_temperature_k AS air_temperature,
            ma.process_temperature_k AS process_temperature,
            ma.temperature_difference_k AS temperature_difference,
            ma.rotational_speed_rpm AS rotational_speed,
            ma.torque_nm AS torque,
            ma.tool_wear_min AS tool_wear,
            ma.mechanical_power_watts AS mechanical_power,
            ma.tool_wear_risk_level AS tool_wear_risk_category,
            ma.operating_stress_score,
            mc.machine_failure AS failure_flag,
            ma.primary_failure_mode AS failure_category,
            ma.failure_mode_count AS failure_count
            {optional_select_clause}
        FROM machine_clean AS mc
        INNER JOIN machine_analytics AS ma
            ON mc.observation_id = ma.observation_id;
    """.format(optional_select_clause=optional_select_clause)
    dataframe = read_sql(database_path, query)
    if dataframe.empty:
        raise PowerBIExportError("Base machine dataset query returned zero rows.")
    return dataframe


def add_risk_and_reliability_fields(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add Power BI-ready failure probability, risk category, and reliability score.

    If machine_analytics already contains persisted scoring columns, those
    values are used. Otherwise, this export layer uses a deterministic
    scorecard-style risk proxy so exports remain reproducible without requiring
    a serialized model artifact. It reuses existing machine_analytics fields and
    does not recreate engineered features.
    """
    output = dataframe.copy()

    if "existing_failure_probability" in output.columns:
        output["Failure Probability"] = pd.to_numeric(
            output["existing_failure_probability"], errors="coerce"
        ).clip(lower=0, upper=1)
        LOGGER.info("Using persisted failure_probability from machine_analytics.")
    else:
        LOGGER.info("Persisted failure_probability not found; deriving it during export.")
        output["Failure Probability"] = derive_failure_probability(output)

    if "existing_risk_category" in output.columns:
        output["Risk Category"] = output["existing_risk_category"].astype(str)
        LOGGER.info("Using persisted risk_category from machine_analytics.")
    else:
        LOGGER.info("Persisted risk_category not found; deriving it during export.")
        output["Risk Category"] = derive_risk_category(output["Failure Probability"])

    if "existing_reliability_score" in output.columns:
        output["Reliability Score"] = pd.to_numeric(
            output["existing_reliability_score"], errors="coerce"
        ).clip(lower=0, upper=100)
        LOGGER.info("Using persisted reliability_score from machine_analytics.")
    else:
        LOGGER.info("Persisted reliability_score not found; deriving it during export.")
        output["Reliability Score"] = derive_reliability_score(output)

    if output[["Failure Probability", "Reliability Score"]].isna().any().any():
        raise PowerBIExportError(
            "Risk scoring fields contain null values after using persisted values or derivation."
        )

    return output


def derive_failure_probability(dataframe: pd.DataFrame) -> pd.Series:
    """Derive a rule-based failure probability proxy from analytics fields."""
    normalized_stress = (dataframe["operating_stress_score"].clip(lower=0, upper=100) / 100).fillna(0)
    normalized_tool_wear = safe_min_max(dataframe["tool_wear"])
    normalized_torque = safe_min_max(dataframe["torque"])
    normalized_power = safe_min_max(dataframe["mechanical_power"])
    normalized_temp_diff = safe_min_max(dataframe["temperature_difference"])

    wear_risk_boost = dataframe["tool_wear_risk_category"].map({"Low": 0.00, "Medium": 0.08, "High": 0.18}).fillna(0)
    failure_signal_boost = dataframe["failure_count"].clip(lower=0, upper=5) * 0.04
    observed_failure_boost = dataframe["failure_flag"].astype(float) * 0.20

    return (
        0.22 * normalized_stress
        + 0.18 * normalized_tool_wear
        + 0.16 * normalized_torque
        + 0.16 * normalized_power
        + 0.10 * normalized_temp_diff
        + wear_risk_boost
        + failure_signal_boost
        + observed_failure_boost
    ).clip(lower=0, upper=1)


def derive_risk_category(failure_probability: pd.Series) -> pd.Series:
    """Derive Low, Medium, or High risk category from failure probability."""
    return pd.Series(
        np.select(
            [
                failure_probability >= 0.35,
                failure_probability >= 0.15,
            ],
            ["High Risk", "Medium Risk"],
            default="Low Risk",
        ),
        index=failure_probability.index,
    )


def derive_reliability_score(dataframe: pd.DataFrame) -> pd.Series:
    """Derive a rule-based reliability score from analytics fields."""
    wear_penalty = dataframe["tool_wear_risk_category"].map({"Low": 0, "Medium": 10, "High": 20}).fillna(0)
    return (
        100
        - dataframe["failure_flag"].astype(float) * 35
        - wear_penalty
        - dataframe["operating_stress_score"].astype(float) * 0.25
        - dataframe["failure_count"].astype(float) * 5
    ).clip(lower=0, upper=100)


def safe_min_max(series: pd.Series) -> pd.Series:
    """Min-max normalize a numeric series and handle constant input safely."""
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    minimum = numeric.min()
    maximum = numeric.max()
    if maximum == minimum:
        return pd.Series(0.0, index=series.index)
    return (numeric - minimum) / (maximum - minimum)


def build_machine_dashboard_dataset(machine_df: pd.DataFrame) -> pd.DataFrame:
    """Build the observation-level Power BI dashboard dataset."""
    export_df = machine_df[
        [
            "machine_id",
            "machine_type",
            "product_type",
            "air_temperature",
            "process_temperature",
            "temperature_difference",
            "rotational_speed",
            "torque",
            "tool_wear",
            "mechanical_power",
            "operating_stress_score",
            "failure_flag",
            "failure_category",
            "Failure Probability",
            "Risk Category",
            "Reliability Score",
        ]
    ].copy()

    export_df.columns = [
        "Machine ID",
        "Machine Type",
        "Product Type",
        "Air Temperature",
        "Process Temperature",
        "Temperature Difference",
        "Rotational Speed",
        "Torque",
        "Tool Wear",
        "Mechanical Power",
        "Operating Stress Score",
        "Failure Flag",
        "Failure Category",
        "Failure Probability",
        "Risk Category",
        "Reliability Score",
    ]

    numeric_columns = [
        "Air Temperature",
        "Process Temperature",
        "Temperature Difference",
        "Torque",
        "Mechanical Power",
        "Operating Stress Score",
        "Failure Probability",
        "Reliability Score",
    ]
    export_df[numeric_columns] = export_df[numeric_columns].round(4)
    return export_df


def build_kpi_summary(machine_df: pd.DataFrame) -> pd.DataFrame:
    """Build the executive KPI summary export."""
    total_observations = len(machine_df)
    total_failures = int(machine_df["failure_flag"].sum())
    failure_rate = total_failures / total_observations
    mtbf = total_observations / total_failures if total_failures else np.nan

    repair_hours = machine_df.loc[machine_df["failure_flag"] == 1, "failure_category"].map(
        {
            "Tool Wear Failure": 3.0,
            "Heat Dissipation Failure": 2.5,
            "Power Failure": 2.0,
            "Overstrain Failure": 3.5,
            "Random Failure": 1.5,
            "No Failure": 0.0,
        }
    ).fillna(2.0)
    mttr = repair_hours.mean() if not repair_hours.empty else 0.0
    availability = mtbf / (mtbf + mttr) if total_failures and (mtbf + mttr) else np.nan

    speed_ratio = machine_df["rotational_speed"] / machine_df["rotational_speed"].max()
    power_ratio = machine_df["mechanical_power"] / machine_df["mechanical_power"].max()
    stress_efficiency = 1 - machine_df["operating_stress_score"] / 100
    performance = (0.40 * speed_ratio + 0.40 * power_ratio + 0.20 * stress_efficiency).mean()

    quality = (machine_df["failure_flag"] == 0).mean()
    oee = availability * performance * quality if not np.isnan(availability) else np.nan
    reliability_score = machine_df["Reliability Score"].mean()
    maintenance_burden_index = failure_rate * 40 + mttr * 10 + machine_df["operating_stress_score"].mean() * 0.30

    rows = [
        kpi_row(
            "Failure Rate",
            failure_rate * 100,
            "{:.2f}%",
            "<= 3.00%",
            status_for_lower_better(failure_rate * 100, good=3.0, monitor=5.0),
            "Investigate machine types and risk segments above the baseline failure rate.",
        ),
        kpi_row(
            "MTBF",
            mtbf,
            "{:.1f} cycles/failure",
            ">= 300 normalized cycles",
            status_for_higher_better(mtbf, good=300, monitor=150),
            "Use as an observation-based reliability proxy until runtime logs are available.",
        ),
        kpi_row(
            "MTTR",
            mttr,
            "{:.2f} assumed hours",
            "<= 2.00 assumed hours",
            status_for_lower_better(mttr, good=2.0, monitor=3.0),
            "Validate assumed repair hours with maintenance work-order history.",
        ),
        kpi_row(
            "Availability",
            availability * 100,
            "{:.2f}%",
            ">= 95.00%",
            status_for_higher_better(availability * 100, good=95, monitor=90),
            "Capture downtime data to replace proxy availability.",
        ),
        kpi_row(
            "Performance",
            performance * 100,
            "{:.2f}%",
            ">= 80.00%",
            status_for_higher_better(performance * 100, good=80, monitor=65),
            "Review low-performance operating segments for speed loss, load imbalance, and stress.",
        ),
        kpi_row(
            "Quality",
            quality * 100,
            "{:.2f}%",
            ">= 97.00% failure-free",
            status_for_higher_better(quality * 100, good=97, monitor=95),
            "Add defect and production output data to calculate true manufacturing quality.",
        ),
        kpi_row(
            "OEE",
            oee * 100,
            "{:.2f}%",
            ">= 75.00% proxy target",
            status_for_higher_better(oee * 100, good=75, monitor=60),
            "Use as decision-support OEE until production, downtime, and defect data are available.",
        ),
        kpi_row(
            "Reliability Score",
            reliability_score,
            "{:.2f} / 100",
            ">= 85.00",
            status_for_higher_better(reliability_score, good=85, monitor=70),
            "Use low reliability records as a preventive maintenance watchlist.",
        ),
        kpi_row(
            "Maintenance Burden Index",
            maintenance_burden_index,
            "{:.2f}",
            "<= 35.00 index points",
            status_for_lower_better(maintenance_burden_index, good=35, monitor=50),
            "Reduce the largest burden contributor first: failures, repair burden, or stress.",
        ),
    ]

    return pd.DataFrame(rows)


def kpi_row(
    name: str,
    value: float,
    value_format: str,
    benchmark: str,
    status: str,
    action: str,
) -> dict[str, str]:
    """Format one KPI scorecard row."""
    if pd.isna(value):
        formatted_value = "Not Available"
        status = "Monitor"
    else:
        formatted_value = value_format.format(value)

    return {
        "KPI Name": name,
        "KPI Value": formatted_value,
        "Target Benchmark": benchmark,
        "Status": status,
        "Recommended Action": action,
    }


def status_for_higher_better(value: float, good: float, monitor: float) -> str:
    """Return scorecard status where higher KPI values are better."""
    if pd.isna(value):
        return "Monitor"
    if value >= good:
        return "Good"
    if value >= monitor:
        return "Monitor"
    return "Critical"


def status_for_lower_better(value: float, good: float, monitor: float) -> str:
    """Return scorecard status where lower KPI values are better."""
    if pd.isna(value):
        return "Monitor"
    if value <= good:
        return "Good"
    if value <= monitor:
        return "Monitor"
    return "Critical"


def build_risk_summary(machine_df: pd.DataFrame) -> pd.DataFrame:
    """Build risk category summary export."""
    actions = {
        "Low Risk": "Continue standard monitoring and routine maintenance cadence.",
        "Medium Risk": "Monitor closely and schedule inspection if elevated risk persists.",
        "High Risk": "Prioritize preventive maintenance inspection and immediate operating review.",
    }

    summary = (
        machine_df.groupby("Risk Category", as_index=False)
        .agg(**{"Machine Count": ("machine_id", "count")})
        .sort_values(
            "Risk Category",
            key=lambda values: values.map({"High Risk": 1, "Medium Risk": 2, "Low Risk": 3}),
        )
    )
    summary["Percentage"] = (100 * summary["Machine Count"] / len(machine_df)).round(4)
    summary["Recommended Action"] = summary["Risk Category"].map(actions)
    return summary[["Risk Category", "Machine Count", "Percentage", "Recommended Action"]]


def build_machine_type_summary(machine_df: pd.DataFrame) -> pd.DataFrame:
    """Build machine type summary export."""
    grouped = (
        machine_df.groupby("machine_type", as_index=False)
        .agg(
            total_observations=("machine_id", "count"),
            failures=("failure_flag", "sum"),
            average_tool_wear=("tool_wear", "mean"),
            average_operating_stress=("operating_stress_score", "mean"),
            average_reliability_score=("Reliability Score", "mean"),
        )
    )
    grouped["Failure Rate"] = (100 * grouped["failures"] / grouped["total_observations"]).round(4)
    grouped["Average Tool Wear"] = grouped["average_tool_wear"].round(4)
    grouped["Average Operating Stress"] = grouped["average_operating_stress"].round(4)
    grouped["Average Reliability Score"] = grouped["average_reliability_score"].round(4)

    risk_distribution = (
        machine_df.groupby(["machine_type", "Risk Category"], as_index=False)
        .agg(risk_count=("machine_id", "count"))
        .sort_values(["machine_type", "Risk Category"])
    )
    total_by_type = machine_df.groupby("machine_type")["machine_id"].count().to_dict()
    risk_distribution["risk_percent"] = risk_distribution.apply(
        lambda row: 100 * row["risk_count"] / total_by_type[row["machine_type"]],
        axis=1,
    )

    distribution_text = (
        risk_distribution.assign(
            risk_text=lambda df: df["Risk Category"]
            + ": "
            + df["risk_count"].astype(str)
            + " ("
            + df["risk_percent"].round(2).astype(str)
            + "%)"
        )
        .groupby("machine_type")["risk_text"]
        .apply("; ".join)
        .reset_index(name="Risk Category Distribution")
    )

    output = grouped.merge(distribution_text, on="machine_type", how="left")
    output = output.rename(columns={"machine_type": "Machine Type"})
    return output[
        [
            "Machine Type",
            "Failure Rate",
            "Average Tool Wear",
            "Average Operating Stress",
            "Average Reliability Score",
            "Risk Category Distribution",
        ]
    ].sort_values("Failure Rate", ascending=False)


def validate_export_dataframe(dataframe: pd.DataFrame, required_columns: Iterable[str], export_name: str) -> None:
    """Validate one export dataframe before writing it."""
    if dataframe.empty:
        raise PowerBIExportError(f"{export_name} export dataframe is empty.")

    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise PowerBIExportError(f"{export_name} is missing required columns: {missing_columns}")

    if dataframe[required_columns].isna().any().any():
        null_counts = dataframe[required_columns].isna().sum()
        failing_columns = null_counts[null_counts > 0].to_dict()
        raise PowerBIExportError(f"{export_name} contains null values in required columns: {failing_columns}")


def export_csv(dataframe: pd.DataFrame, export_path: Path) -> None:
    """Write a dataframe to CSV with consistent encoding."""
    dataframe.to_csv(export_path, index=False, encoding="utf-8-sig")
    LOGGER.info("Exported %s rows to %s", f"{len(dataframe):,}", export_path)


def generate_powerbi_exports(database_path: Path, export_dir: Path) -> dict[str, Path]:
    """Generate all Power BI-ready CSV exports."""
    validate_database(database_path)
    export_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Reading machine data from %s", database_path)
    machine_df = get_machine_base_dataset(database_path)
    machine_df = add_risk_and_reliability_fields(machine_df)

    exports = {
        "machine_dashboard_dataset.csv": build_machine_dashboard_dataset(machine_df),
        "kpi_summary.csv": build_kpi_summary(machine_df),
        "risk_summary.csv": build_risk_summary(machine_df),
        "machine_type_summary.csv": build_machine_type_summary(machine_df),
    }

    required_columns = {
        "machine_dashboard_dataset.csv": [
            "Machine ID",
            "Machine Type",
            "Product Type",
            "Air Temperature",
            "Process Temperature",
            "Temperature Difference",
            "Rotational Speed",
            "Torque",
            "Tool Wear",
            "Mechanical Power",
            "Operating Stress Score",
            "Failure Flag",
            "Failure Category",
            "Failure Probability",
            "Risk Category",
            "Reliability Score",
        ],
        "kpi_summary.csv": [
            "KPI Name",
            "KPI Value",
            "Target Benchmark",
            "Status",
            "Recommended Action",
        ],
        "risk_summary.csv": [
            "Risk Category",
            "Machine Count",
            "Percentage",
            "Recommended Action",
        ],
        "machine_type_summary.csv": [
            "Machine Type",
            "Failure Rate",
            "Average Tool Wear",
            "Average Operating Stress",
            "Average Reliability Score",
            "Risk Category Distribution",
        ],
    }

    output_paths: dict[str, Path] = {}
    for filename, dataframe in exports.items():
        validate_export_dataframe(dataframe, required_columns[filename], filename)
        export_path = export_dir / filename
        export_csv(dataframe, export_path)
        output_paths[filename] = export_path

    LOGGER.info("Power BI export layer completed successfully.")
    return output_paths


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export Power BI-ready maintenance intelligence datasets from SQLite."
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="Path to maintenance.db. Defaults to data/database/maintenance.db.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Directory where CSV exports will be written. Defaults to powerbi/data_exports.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    configure_logging()
    args = parse_args()

    try:
        output_paths = generate_powerbi_exports(args.database_path, args.export_dir)
    except Exception as exc:
        LOGGER.exception("Power BI export failed.")
        raise SystemExit(f"Power BI export failed: {exc}") from exc

    LOGGER.info("Generated exports:")
    for name, path in output_paths.items():
        LOGGER.info("  %s -> %s", name, path)


if __name__ == "__main__":
    main()
