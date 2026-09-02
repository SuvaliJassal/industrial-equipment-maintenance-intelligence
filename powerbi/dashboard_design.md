# Industrial Equipment Performance & Maintenance Intelligence Dashboard

## Business Goal

Design a professional Power BI dashboard for Operations Managers, Maintenance Managers, Reliability Engineers, and Plant Leadership.

The dashboard supports:

- Equipment performance monitoring
- Failure analysis
- KPI tracking
- Risk prioritization
- Maintenance recommendations

## Exported Datasets

| Dataset | Purpose |
|---|---|
| `machine_dashboard_dataset.csv` | Main machine-level reporting dataset with operating conditions, failure fields, risk score, risk category, and reliability score. |
| `kpi_summary.csv` | Executive KPI scorecard with KPI value, benchmark, status, and recommended action. |
| `risk_summary.csv` | Risk category counts, percentages, and maintenance actions. |
| `machine_type_summary.csv` | Machine type-level reliability, stress, wear, failure rate, and risk distribution summary. |

## Recommended Data Model

Use `machine_dashboard_dataset.csv` as the main fact table. The other datasets are summary tables used for scorecards and executive visuals.

Relationships are optional because the export files are already Power BI-ready. If relationships are needed:

| From | To | Relationship |
|---|---|---|
| `machine_dashboard_dataset[Machine Type]` | `machine_type_summary[Machine Type]` | Many-to-one |
| `machine_dashboard_dataset[Risk Category]` | `risk_summary[Risk Category]` | Many-to-one |

Keep cross-filter direction single unless a specific report page requires bidirectional filtering.

## DAX Measures

Create these measures in Power BI.

```DAX
Total Machines =
COUNTROWS('machine_dashboard_dataset')
```

```DAX
Total Failures =
SUM('machine_dashboard_dataset'[Failure Flag])
```

```DAX
Failure Rate % =
DIVIDE([Total Failures], [Total Machines], 0)
```

Format as percentage.

```DAX
Average Reliability Score =
AVERAGE('machine_dashboard_dataset'[Reliability Score])
```

```DAX
High Risk Machine Count =
CALCULATE(
    [Total Machines],
    'machine_dashboard_dataset'[Risk Category] = "High Risk"
)
```

```DAX
Average OEE Proxy =
AVERAGEX(
    FILTER('kpi_summary', 'kpi_summary'[KPI Name] = "OEE"),
    VALUE(SUBSTITUTE('kpi_summary'[KPI Value], "%", ""))
) / 100
```

Format as percentage.

```DAX
Average MTBF =
AVERAGEX(
    FILTER('kpi_summary', 'kpi_summary'[KPI Name] = "MTBF"),
    VALUE(LEFT('kpi_summary'[KPI Value], FIND(" ", 'kpi_summary'[KPI Value] & " ") - 1))
)
```

```DAX
Average MTTR =
AVERAGEX(
    FILTER('kpi_summary', 'kpi_summary'[KPI Name] = "MTTR"),
    VALUE(LEFT('kpi_summary'[KPI Value], FIND(" ", 'kpi_summary'[KPI Value] & " ") - 1))
)
```

## Page 1: Executive Overview

### Business Objective

Give plant leadership a concise view of reliability health, failure exposure, maintenance risk, and KPI status.

### Visuals

| Visual | Type | Dataset | Fields Used | Business Purpose |
|---|---|---|---|---|
| Total Machines | Card | `machine_dashboard_dataset` | `Machine ID` or measure `[Total Machines]` | Shows total equipment observations represented in the dashboard. |
| Total Failures | Card | `machine_dashboard_dataset` | `Failure Flag` or measure `[Total Failures]` | Shows total failure events in the current filter context. |
| Failure Rate | Card | `machine_dashboard_dataset` | Measure `[Failure Rate %]` | Shows the overall reliability baseline. |
| MTBF | Card | `kpi_summary` | Measure `[Average MTBF]` | Shows observation-based time-between-failure proxy. |
| MTTR | Card | `kpi_summary` | Measure `[Average MTTR]` | Shows assumed repair burden proxy. |
| OEE Proxy | Card | `kpi_summary` | Measure `[Average OEE Proxy]` | Shows executive equipment effectiveness proxy. |
| Average Reliability Score | Card | `machine_dashboard_dataset` | Measure `[Average Reliability Score]` | Shows overall machine reliability health on a 0-100 score. |
| Failure Rate by Machine Type | Clustered column chart | `machine_type_summary` | Axis: `Machine Type`; Values: `Failure Rate` | Identifies which machine type has the highest failure exposure. |
| Risk Category Distribution | Donut chart or stacked bar chart | `risk_summary` | Legend: `Risk Category`; Values: `Machine Count` or `Percentage` | Shows how the equipment population is distributed across Low, Medium, and High Risk. |
| KPI Scorecard Table | Table | `kpi_summary` | `KPI Name`, `KPI Value`, `Target Benchmark`, `Status`, `Recommended Action` | Gives executives a benchmarked KPI status view with next actions. |

### Slicers

- `Machine Type`
- `Risk Category`
- `Failure Category`

### Filters

- Default page filter can include all machine types and all risk categories.
- Add optional visual-level filter to KPI Scorecard Table to show `Status = Critical` first.

### Interactions

- Selecting a machine type should filter KPI cards, failure rate visuals, and risk distribution.
- Selecting High Risk should filter the failure and reliability cards to show high-risk exposure.
- Selecting a failure category should update failure count and machine-level risk views.

### Interpretation

Leadership should use this page to answer:

- Are failures concentrated in a specific machine type?
- Is the current risk population acceptable?
- Which KPIs require immediate management attention?

### Recommended Actions

- Review KPIs marked `Critical`.
- Prioritize machine types with the highest failure rate.
- Use High Risk counts as the starting point for maintenance planning discussions.

## Page 2: Operational Performance

### Business Objective

Help operations and maintenance teams understand which operating conditions are associated with failures and elevated risk.

### Visuals

| Visual | Type | Dataset | Fields Used | Business Purpose |
|---|---|---|---|---|
| Tool Wear Analysis | Box plot or column chart by risk category | `machine_dashboard_dataset` | Axis: `Risk Category`; Values: `Tool Wear`; Legend: `Failure Flag` | Shows whether tool wear is higher in failed or high-risk conditions. |
| Torque vs Failure | Scatter plot | `machine_dashboard_dataset` | X: `Torque`; Y: `Failure Probability`; Legend: `Failure Flag`; Size: `Operating Stress Score` | Reveals whether higher torque is associated with failure probability or stress. |
| Temperature Difference vs Failure | Scatter plot or clustered column chart | `machine_dashboard_dataset` | X: `Temperature Difference`; Y: `Failure Probability`; Legend: `Failure Flag` | Shows whether thermal difference is linked to failure risk. |
| Mechanical Power Distribution | Histogram or column chart using bins | `machine_dashboard_dataset` | Axis: `Mechanical Power`; Values: count of `Machine ID`; Legend: `Risk Category` | Shows whether high-power operating states are concentrated in riskier segments. |
| Operating Stress Score by Machine Type | Clustered bar chart | `machine_dashboard_dataset` | Axis: `Machine Type`; Values: average `Operating Stress Score`; Legend: `Risk Category` | Compares stress exposure across machine types. |
| Operational Detail Table | Table | `machine_dashboard_dataset` | `Machine ID`, `Machine Type`, `Torque`, `Tool Wear`, `Mechanical Power`, `Operating Stress Score`, `Failure Probability`, `Risk Category` | Enables supervisors to inspect specific machine observations. |

### Fields Used

- `Machine ID`
- `Machine Type`
- `Tool Wear`
- `Torque`
- `Temperature Difference`
- `Mechanical Power`
- `Operating Stress Score`
- `Failure Flag`
- `Failure Probability`
- `Risk Category`

### Filters/Slicers

- `Machine Type`
- `Risk Category`
- `Failure Flag`
- `Failure Category`

### Interactions

- Selecting a risk category should filter all operating condition visuals.
- Selecting a machine type should update stress, torque, power, and tool wear visuals.
- Scatter plot selections should filter the operational detail table.

### Interpretation

This page should reveal whether failures are associated with high wear, high torque, high temperature difference, high power, or elevated stress.

### Recommended Actions

- Review operating thresholds for high-risk torque, power, and stress patterns.
- Schedule inspections for machines with high tool wear and high failure probability.
- Use this page in daily or weekly maintenance review meetings.

## Page 3: Maintenance Risk Intelligence

### Business Objective

Provide a focused risk management page that identifies high-risk machines and explains where maintenance attention should go first.

### Visuals

| Visual | Type | Dataset | Fields Used | Business Purpose |
|---|---|---|---|---|
| High Risk Machines Table | Table | `machine_dashboard_dataset` | `Machine ID`, `Machine Type`, `Product Type`, `Failure Probability`, `Risk Category`, `Reliability Score`, `Operating Stress Score`, `Tool Wear`, `Failure Category` | Creates an actionable list for maintenance planning. |
| Failure Probability by Machine Type | Bar chart | `machine_dashboard_dataset` | Axis: `Machine Type`; Values: average `Failure Probability` | Shows which machine types carry the highest predicted risk. |
| Risk Category Breakdown | Stacked bar chart | `machine_dashboard_dataset` | Axis: `Machine Type`; Legend: `Risk Category`; Values: count of `Machine ID` | Shows how risk is distributed within each machine type. |
| Reliability Score Distribution | Histogram or column chart using bins | `machine_dashboard_dataset` | Axis: `Reliability Score`; Legend: `Risk Category`; Values: count of `Machine ID` | Shows whether the equipment population is healthy, moderate, or weak. |
| Maintenance Burden Index | Card | `kpi_summary` | Filter `KPI Name = Maintenance Burden Index`; Field: `KPI Value` | Shows the maintenance workload pressure indicator. |
| Risk Summary Table | Table | `risk_summary` | `Risk Category`, `Machine Count`, `Percentage`, `Recommended Action` | Converts risk distribution into action guidance. |

### Conditional Formatting Rules

Apply these rules in Power BI:

| Field | Rule |
|---|---|
| `Risk Category` | High Risk = red, Medium Risk = amber, Low Risk = green |
| `Failure Probability` | `>= 0.35` red, `0.15-0.3499` amber, `< 0.15` green |
| `Reliability Score` | `< 40` dark red, `40-59.99` red, `60-74.99` amber, `75-89.99` light green, `>= 90` green |
| `Operating Stress Score` | `>= 75` red, `50-74.99` amber, `< 50` green |
| `Status` in KPI table | Critical = red, Monitor = amber, Good = green |

### Fields Used

- `Machine ID`
- `Machine Type`
- `Product Type`
- `Failure Probability`
- `Risk Category`
- `Reliability Score`
- `Operating Stress Score`
- `Tool Wear`
- `Failure Category`
- `KPI Name`
- `KPI Value`

### Filters/Slicers

- `Risk Category`
- `Machine Type`
- `Failure Category`
- `Reliability Score` range slicer

### Interactions

- Selecting High Risk should filter all charts and tables to priority records.
- Selecting a machine type should update risk breakdown and high-risk machine table.
- Selecting a low reliability score range should show the machines most likely to need action.

### Interpretation

Maintenance leaders should use this page as the primary risk triage view. It identifies which machines need attention, why they are risky, and what action is recommended.

### Recommended Actions

- Review the High Risk Machines Table first.
- Assign preventive inspections to machines with high failure probability and low reliability score.
- Monitor Medium Risk records for repeated risk elevation.

## Page 4: Recommendations & Action Plan

### Business Objective

Translate dashboard findings into a practical maintenance action plan.

### Visuals

| Visual | Type | Dataset | Fields Used | Business Purpose |
|---|---|---|---|---|
| Top 5 High Risk Machine Segments | Table or ranked bar chart | `machine_dashboard_dataset` | `Machine Type`, `Risk Category`, average `Failure Probability`, average `Reliability Score`, count of `Machine ID` | Shows the highest-priority machine segments. |
| Maintenance Priority Matrix | Scatter plot | `machine_dashboard_dataset` | X: average `Operating Stress Score`; Y: average `Failure Probability`; Size: count of `Machine ID`; Legend: `Risk Category`; Details: `Machine Type` | Prioritizes segments by stress and probability. |
| Recommended Actions | Table | `risk_summary` and `kpi_summary` | `Risk Category`, `Recommended Action`, `KPI Name`, `Status` | Converts analysis into maintenance action guidance. |
| KPI Status Summary | Stacked column chart or donut chart | `kpi_summary` | Legend: `Status`; Values: count of `KPI Name` | Shows how many KPIs are Good, Monitor, or Critical. |
| Expected Business Impact | Table or text cards | Manual text or `kpi_summary[Recommended Action]` | Maintenance actions and expected impact statements | Communicates the operational value of acting on the dashboard. |

### Fields Used

- `Machine Type`
- `Risk Category`
- `Failure Probability`
- `Reliability Score`
- `Operating Stress Score`
- `Machine ID`
- `KPI Name`
- `KPI Value`
- `Status`
- `Recommended Action`

### Filters/Slicers

- `Machine Type`
- `Risk Category`
- `Status`

### Interactions

- Selecting Critical status should filter recommended actions to urgent KPI issues.
- Selecting High Risk should update the priority matrix and top segments.
- Selecting a machine type should show segment-specific actions.

### Interpretation

This page should answer:

- Where should maintenance teams focus first?
- Which segments carry the highest risk?
- Which KPI gaps require management action?
- What operational benefit should leadership expect?

### Recommended Actions

- Prioritize High Risk segments with low reliability scores.
- Convert Critical KPI rows into maintenance action items.
- Review the action plan weekly with operations and maintenance leaders.

### Expected Business Impact

- Reduced unplanned downtime exposure
- Better preventive maintenance prioritization
- Faster identification of risky operating profiles
- Improved leadership visibility into maintenance performance
- Stronger alignment between operations, reliability, and maintenance teams

## Power BI Setup Steps

### 1. Load CSV Exports into Power BI

1. Run the export script:

```bash
python scripts/export_powerbi.py
```

2. Open Power BI Desktop.
3. Select **Get Data > Text/CSV**.
4. Import these files from `powerbi/data_exports`:
   - `machine_dashboard_dataset.csv`
   - `kpi_summary.csv`
   - `risk_summary.csv`
   - `machine_type_summary.csv`
5. Rename tables in Power BI to:
   - `machine_dashboard_dataset`
   - `kpi_summary`
   - `risk_summary`
   - `machine_type_summary`

### 2. Create Relationships If Needed

The exports are already dashboard-ready, so relationships are not strictly required. If interactive filtering across summary tables is desired, create:

- `machine_dashboard_dataset[Machine Type]` to `machine_type_summary[Machine Type]`
- `machine_dashboard_dataset[Risk Category]` to `risk_summary[Risk Category]`

Use many-to-one relationships from the machine-level dataset to summary datasets.

### 3. Create Calculated Measures

Create the DAX measures listed in the **DAX Measures** section. Format percentage measures as percentages with two decimal places.

Recommended measure table:

- Create a blank table called `Measures`.
- Store all DAX measures there for easier report maintenance.

### 4. Refresh Data After Running `export_powerbi.py`

1. Run:

```bash
python scripts/export_powerbi.py
```

2. Open Power BI Desktop.
3. Click **Refresh**.
4. Confirm that row counts and KPI cards update.
5. Publish the updated report if using Power BI Service.

For scheduled refresh, store CSV exports in a stable folder path and configure gateway access if required.

### 5. Format the Dashboard Professionally

Use a clean industrial operations style:

- Background: light gray or white
- Primary accent: dark blue or steel blue
- Risk colors:
  - High Risk: red
  - Medium Risk: amber
  - Low Risk: green
- KPI status colors:
  - Good: green
  - Monitor: amber
  - Critical: red
- Use consistent card formatting across all pages.
- Keep page headers short and operational.
- Avoid decorative visuals that do not support decisions.
- Use tables for action lists and scorecards.
- Use scatter plots for risk and operating-condition relationships.
- Use bar charts for machine type comparisons.
- Use conditional formatting on all risk, status, and reliability fields.

## Dashboard Navigation

Recommended page order:

1. Executive Overview
2. Operational Performance
3. Maintenance Risk Intelligence
4. Recommendations & Action Plan

Add page navigation buttons at the top right of each page. Use consistent slicer placement across pages so users can move through the dashboard without relearning the layout.

## Final Design Notes

This dashboard should behave like a maintenance command center. The first page tells leaders what is happening, the second page explains operating conditions, the third page identifies risk, and the fourth page turns insights into action.

