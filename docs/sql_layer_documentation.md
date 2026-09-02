# SQL Analytics and KPI Layer Documentation

## Purpose

Layer 2 turns the validated SQLite database into a reusable analytics layer for business analysis, KPI reporting, and Power BI consumption.

The SQL layer is designed for SQLite and depends on these base tables:

- `machine_raw`
- `machine_clean`
- `machine_analytics`

Before running the query files, create the views:

```bash
sqlite3 data/database/maintenance.db < sql/views/analytics_views.sql
```

## SQL Assets

| File | Purpose |
|---|---|
| `sql/views/analytics_views.sql` | Creates reusable reporting and analytics views. |
| `sql/queries/business_queries.sql` | Contains business analysis queries for failure, reliability, stress, and burden analysis. |
| `sql/queries/kpi_queries.sql` | Contains KPI calculations for maintenance decision making. |

## Analytics Views

### `vw_machine_performance`

Business Purpose: Provides a machine-level performance view with operating bands, performance ratio, and quality flag.

SQL Logic: Selects from `machine_analytics`, adds speed band, torque band, stress band, performance ratio, and good observation flag.

Expected Output: One row per observation with core machine metrics and performance classifications.

Power BI Consumption: Used for operational pages showing speed, torque, stress, tool wear, and failure-free performance.

### `vw_failure_analysis`

Business Purpose: Standardizes failure categories and creates analysis-friendly failure driver labels.

SQL Logic: Uses failure mode flags to create normalized failure category, failure complexity, and failure driver group.

Expected Output: One row per observation with failure labels and driver groupings.

Power BI Consumption: Used for failure mode dashboards, root-cause pages, and slicers by failure category.

### `vw_maintenance_kpis`

Business Purpose: Creates single-row executive KPIs for maintenance performance.

SQL Logic: Calculates failure rate, MTBF proxy, MTTR proxy, availability, performance, quality, OEE, reliability score, and maintenance burden index.

Expected Output: One row containing portfolio-level KPI values.

Power BI Consumption: Used for KPI cards, executive summary tiles, and maintenance scorecards.

### `vw_risk_summary`

Business Purpose: Summarizes risk concentration by machine type, tool wear risk, and stress band.

SQL Logic: Groups machine analytics records and calculates observation counts, failure counts, failure rate, average wear, average temperature delta, average torque, power, and stress.

Expected Output: Aggregated risk groups with failure and operating-condition metrics.

Power BI Consumption: Used for heatmaps, matrix visuals, risk distribution charts, and maintenance prioritization pages.

### `vw_powerbi_dataset`

Business Purpose: Provides a denormalized dataset optimized for Power BI import.

SQL Logic: Joins machine performance and failure analysis views, then adds high-risk flag and repair-time proxy minutes.

Expected Output: One row per observation with machine metrics, failure labels, risk flags, and Power BI-ready dimensions.

Power BI Consumption: Main import table for interactive dashboards. It supports slicers by machine type, risk band, failure category, stress band, and tool wear risk.

## Business Queries

### 1. Failure Rate by Machine Type

Business Purpose: Compare reliability across machine/product quality types.

SQL Logic: Groups observations by `machine_type`, counts failures, and divides failures by total observations.

Expected Output: Machine type, total observations, failure count, and failure rate percent.

Business Interpretation: Machine types with higher failure rates should receive deeper root-cause analysis, more frequent condition monitoring, or tighter operating limits.

### 2. Failure Count by Failure Category

Business Purpose: Identify which failure categories create the largest reliability burden.

SQL Logic: Uses `vw_failure_analysis` to group failed observations by normalized failure category.

Expected Output: Failure category, failure count, and failure share percent.

Business Interpretation: The largest categories point to the maintenance programs likely to deliver the highest impact if improved first.

### 3. Average Tool Wear Before Failure

Business Purpose: Estimate the tool wear level typically observed when failures occur.

SQL Logic: Filters failed records and calculates average, minimum, and maximum tool wear by failure category.

Expected Output: Failure category, failed observations, average tool wear, minimum tool wear, and maximum tool wear.

Business Interpretation: Higher wear before failure supports preventive replacement thresholds and tool-life planning.

### 4. Average Torque for Failed vs Non-Failed Machines

Business Purpose: Evaluate whether torque differs between failed and healthy operating records.

SQL Logic: Groups records by failure status and calculates torque summary statistics.

Expected Output: Machine status, observation count, average torque, minimum torque, and maximum torque.

Business Interpretation: Large torque differences may indicate load-related stress, incorrect operating settings, or mechanical overload patterns.

### 5. Temperature Difference Impact Analysis

Business Purpose: Understand how process-to-air temperature difference relates to failure behavior.

SQL Logic: Buckets temperature difference into bands and calculates failure rate per band.

Expected Output: Temperature difference band, observation count, failure count, and failure rate percent.

Business Interpretation: Higher failure rates in thermal bands indicate operating conditions that may need process controls or cooling improvements.

### 6. Operating Stress Analysis

Business Purpose: Measure how stress bands relate to failure concentration.

SQL Logic: Uses `operating_stress_band` from `vw_machine_performance` and calculates failure rate, average tool wear, and average mechanical power.

Expected Output: Stress band, observations, failures, failure rate, average tool wear, and average mechanical power.

Business Interpretation: High-stress bands with elevated failure rates should be prioritized for operational limit review and preventive maintenance scheduling.

### 7. High Risk Machine Identification

Business Purpose: Identify observations that should be prioritized for maintenance review.

SQL Logic: Selects records with observed failure, multiple failure signals, high tool wear, or critical operating stress.

Expected Output: Observation ID, product ID, machine type, risk reason, stress score, tool wear, failure flag, and primary failure mode.

Business Interpretation: These records represent urgent investigation targets and can feed maintenance watchlists.

### 8. Top Failure Drivers

Business Purpose: Rank operating and condition signals by observed failure rates.

SQL Logic: Creates driver categories from high tool wear, high temperature difference, high torque, high mechanical power, and critical stress.

Expected Output: Failure driver, observation count, failure count, and failure rate percent.

Business Interpretation: The highest-rate drivers help maintenance teams focus on the conditions most associated with failures.

### 9. Reliability Analysis by Product Type

Business Purpose: Compare reliability behavior across AI4I product quality types.

SQL Logic: Uses `machine_type` as product type and calculates failure rate, MTBF proxy, average stress, and average wear.

Expected Output: Product type, observations, failures, failure rate, MTBF proxy, average stress, and average tool wear.

Business Interpretation: Product types with lower MTBF and higher stress may need process-specific maintenance strategies.

### 10. Maintenance Burden Analysis

Business Purpose: Estimate which failure categories create the highest maintenance workload.

SQL Logic: Assigns repair-time proxy minutes by failure category and aggregates total and average burden.

Expected Output: Failure category, failure count, total repair-time proxy minutes, average repair-time proxy minutes, and burden share.

Business Interpretation: Categories with high total burden deserve priority because they consume the most maintenance capacity.

## KPI Queries and Maintenance Decision Support

### Failure Rate

Supports Decision Making: Establishes the overall reliability baseline and highlights whether the equipment population is becoming more failure-prone.

### Failure Rate by Machine Type

Supports Decision Making: Helps maintenance teams compare machine categories and allocate inspection effort to higher-risk types.

### MTBF

Supports Decision Making: Estimates reliability by showing how many observations occur between failures. Lower MTBF indicates more frequent breakdown exposure.

### MTTR

Supports Decision Making: Estimates average repair burden by failure type. Since AI4I has no repair duration field, this layer uses documented proxy minutes by failure category.

### Availability

Supports Decision Making: Indicates whether failure frequency and repair burden are reducing production readiness.

### Performance

Supports Decision Making: Shows whether machines are operating near the observed ideal rotational speed. Low performance can indicate speed losses or operating constraints.

### Quality

Supports Decision Making: Uses failure-free observations as the quality proxy. Lower quality indicates more exposure to failure-driven production disruption.

### OEE

Supports Decision Making: Combines availability, performance, and quality into one executive-level equipment effectiveness score.

### Machine Reliability Score

Supports Decision Making: Provides a weighted reliability index that combines failure rate, quality loss, performance loss, and maintenance burden into a single leadership metric.

### Maintenance Burden Index

Supports Decision Making: Estimates maintenance workload intensity per observation and helps teams understand how much maintenance effort the failure mix is likely to consume.

### Risk Distribution

Supports Decision Making: Shows whether the equipment population is concentrated in low-risk or high-risk operating states.

## Important Dataset Assumptions

The AI4I 2020 dataset does not include true production timestamps, repair start times, repair end times, downtime duration, unit output, or defect counts.

For this reason:

- MTBF is calculated as an observation-based proxy: `total observations / failures`.
- MTTR is calculated using repair-time proxy minutes by failure category.
- Availability uses the standard formula `MTBF / (MTBF + MTTR)` with the documented proxy values.
- Performance uses rotational speed relative to an observed maximum reference of `2861 RPM`.
- Quality uses failure-free observations as a proxy for good production output.
- OEE is a decision-support estimate, not a plant-certified OEE value.

These assumptions are intentionally explicit so the analytics layer remains transparent and defensible.

