# Assumptions and Limitations

## Industrial Equipment Performance & Maintenance Intelligence Analytics Platform

This document explains the assumptions and limitations used in the project. It is written in simple English so it can also be used for interview preparation.

## Why This Document Matters

In real analytics projects, every dataset has limitations. A good analyst does not hide those limitations. A good analyst explains them clearly and uses reasonable assumptions only when needed.

This project uses the AI4I 2020 Predictive Maintenance Dataset. It is useful for equipment failure analytics, but it does not contain every field that a real manufacturing plant would have.

Because of this, some KPIs are calculated as **analytical proxies**.

An analytical proxy means:

```text
A practical estimate used when the exact real-world measurement is not available.
```

These proxy KPIs are useful for learning, analysis, dashboard design, and decision-support thinking. They should not be presented as certified plant measurements.

## Dataset Used

Dataset:

```text
AI4I 2020 Predictive Maintenance Dataset
```

The dataset includes:

- Machine type
- Air temperature
- Process temperature
- Rotational speed
- Torque
- Tool wear
- Machine failure flag
- Failure categories

The dataset supports:

- Failure analysis
- Tool wear analysis
- Operating stress analysis
- Maintenance KPI framework
- Failure risk scoring
- Power BI dashboarding

## Main Dataset Limitations

The dataset does **not** include:

- Real timestamps
- Actual operating hours
- Downtime duration
- Repair start time
- Repair end time
- Technician work hours
- Work order history
- Maintenance cost
- Spare parts usage
- Production output
- Defect count
- Scrap or rework data
- Real-time sensor history

Because these fields are missing, some manufacturing KPIs cannot be calculated as real plant KPIs. They are calculated as documented proxies.

## Important Assumption Summary

| Area | What Is Missing | Assumption Used |
|---|---|---|
| MTBF | Actual runtime or timestamps | Each observation is treated as one normalized operating cycle |
| MTTR | Actual repair duration | Repair-time assumptions are assigned by failure category |
| Availability | Actual downtime | Calculated using MTBF proxy and MTTR proxy |
| Performance | Actual production output and ideal cycle time | Estimated using speed, mechanical power, and operating stress |
| Quality | Defect count or good units | Estimated using failure-free observations |
| OEE | True availability, performance, and quality data | Calculated as a decision-support proxy |
| Risk Scoring | Real-time production history | Uses available operating condition fields |

## MTBF Assumption

MTBF means **Mean Time Between Failures**.

In a real plant, MTBF is usually calculated using actual operating time:

```text
MTBF = Total Operating Time / Number of Failures
```

### Limitation

The AI4I dataset does not include actual operating hours or timestamps.

### Assumption Used

Each row is treated as one normalized operating observation.

So the project uses:

```text
MTBF Proxy = Total Observations / Total Failures
```

### How to Explain in an Interview

"The dataset does not have real runtime hours, so I did not claim true MTBF. I calculated an observation-based MTBF proxy to compare reliability patterns within the dataset."

### Business Meaning

The MTBF proxy helps understand how frequently failures appear in the dataset. A higher value means failures are less frequent.

## MTTR Assumption

MTTR means **Mean Time To Repair**.

In a real plant, MTTR is calculated as:

```text
MTTR = Total Repair Time / Number of Repairs
```

### Limitation

The AI4I dataset does not include actual repair time.

### Assumption Used

The project assigns assumed repair hours by failure category.

| Failure Category | Assumed Repair Hours | Reason |
|---|---:|---|
| Tool Wear Failure | 3.0 hours | Tool replacement, inspection, and restart checks may take more time |
| Heat Dissipation Failure | 2.5 hours | Cooling and thermal issues need inspection and stabilization |
| Power Failure | 2.0 hours | Power/load issues may need electrical or load review |
| Overstrain Failure | 3.5 hours | Mechanical stress issues can take longer to inspect |
| Random Failure | 1.5 hours | General troubleshooting assumed to be shorter |
| Unclassified Failure | 2.0 hours | Default assumption when exact category is unclear |

The project uses:

```text
MTTR Proxy = Total Assumed Repair Hours / Total Failures
```

### How to Explain in an Interview

"The dataset does not include repair duration, so I created a documented repair-time assumption model. I clearly marked MTTR as a proxy and did not present it as actual repair time."

### Business Meaning

The MTTR proxy helps estimate maintenance burden. It gives an idea of which failure categories may consume more maintenance effort.

## Availability Assumption

Availability shows how ready equipment is for operation.

Real-world formula:

```text
Availability = Operating Time / Planned Production Time
```

Another common formula is:

```text
Availability = MTBF / (MTBF + MTTR)
```

### Limitation

The dataset does not contain planned production time or downtime.

### Assumption Used

The project calculates Availability using:

```text
Availability Proxy = MTBF Proxy / (MTBF Proxy + MTTR Proxy)
```

### How to Explain in an Interview

"Because actual downtime is not available, I calculated availability as a proxy using MTBF and MTTR assumptions. I documented this clearly so the metric is not misunderstood."

### Business Meaning

The Availability proxy gives a decision-support estimate of equipment readiness.

## Performance Assumption

Performance usually measures whether equipment is producing at the expected speed or output.

Real-world formula:

```text
Performance = Actual Output / Ideal Output
```

### Limitation

The dataset does not include production output or ideal cycle time.

### Assumption Used

The project estimates performance using:

- Rotational speed
- Mechanical power
- Operating stress score

The idea is:

```text
Higher speed and stable power are good,
but very high stress can reduce performance quality.
```

### How to Explain in an Interview

"The dataset does not have actual production output, so I created a performance index using machine operating signals such as speed, mechanical power, and stress. I treated it as an analytical proxy."

### Business Meaning

The Performance proxy helps identify machines that may be operating inefficiently or under stress.

## Quality Assumption

Quality usually measures good production output.

Real-world formula:

```text
Quality = Good Units / Total Units Produced
```

### Limitation

The dataset does not include good units, defective units, scrap, or rework.

### Assumption Used

The project uses failure-free observations as a quality proxy:

```text
Quality Proxy = Non-Failure Observations / Total Observations
```

### How to Explain in an Interview

"Since the dataset does not have defect data, I used failure-free observations as a quality proxy. I made it clear that this is not the same as true manufacturing quality."

### Business Meaning

The Quality proxy shows how often machine observations are free from failure.

## OEE Assumption

OEE means **Overall Equipment Effectiveness**.

Real-world formula:

```text
OEE = Availability x Performance x Quality
```

### Limitation

True OEE requires:

- Actual downtime
- Actual production output
- Ideal cycle time
- Good units
- Defective units

The AI4I dataset does not include these fields.

### Assumption Used

The project calculates:

```text
OEE Proxy = Availability Proxy x Performance Proxy x Quality Proxy
```

### How to Explain in an Interview

"I included OEE because it is an important manufacturing KPI, but I clearly called it an OEE proxy. Since the dataset does not contain real production and downtime data, it should be used only for decision-support demonstration."

### Business Meaning

The OEE proxy helps show how availability, performance, and quality concepts can be combined in a dashboard.

## Reliability Score Assumption

Reliability Score is a custom project KPI.

It combines:

- Failure history
- Tool wear risk
- Operating stress score
- Failure signals

The score is scaled from 0 to 100.

### Assumption Used

A higher score means better machine health. A lower score means the machine should be reviewed.

### How to Explain in an Interview

"Reliability Score is a custom score I created to help rank machine health. It combines failure status, tool wear risk, operating stress, and failure signals into one easy-to-read score."

### Business Meaning

It helps maintenance teams prioritize machines for inspection.

## Maintenance Burden Index Assumption

Maintenance Burden Index is a custom KPI.

It combines:

- Failure frequency
- Assumed repair burden
- Operating stress

### Limitation

The dataset does not include actual labor hours or maintenance cost.

### Assumption Used

The index estimates workload pressure using available data and repair-time assumptions.

### How to Explain in an Interview

"The Maintenance Burden Index is not actual maintenance cost. It is a decision-support index that estimates which conditions may create more maintenance workload."

### Business Meaning

It helps leaders understand where maintenance resources may be under pressure.

## Risk Scoring Assumptions

The risk scoring engine predicts `machine_failure`.

Features used:

- Air temperature
- Process temperature
- Temperature difference
- Rotational speed
- Torque
- Tool wear
- Mechanical power
- Operating stress score
- Machine type

### Limitation

The dataset does not include live sensor streams or time-based failure history.

### Assumption Used

The model treats each row as an independent operating observation.

### Risk Categories

| Risk Category | Meaning |
|---|---|
| Low Risk | Continue standard monitoring |
| Medium Risk | Monitor closely and review if risk persists |
| High Risk | Prioritize preventive maintenance review |

### How to Explain in an Interview

"The risk score is used for maintenance prioritization. It is not meant to replace engineering judgment. It helps identify which machines or operating conditions deserve attention first."

## Power BI Reporting Assumptions

Power BI uses exported CSV files created from SQLite.

### Assumption Used

Most business logic is prepared before Power BI export, so Power BI does not need heavy transformations.

### Why This Matters

This makes the dashboard easier to maintain and reduces the chance of inconsistent calculations.

### How to Explain in an Interview

"I prepared Power BI-ready exports so the dashboard focuses on reporting, not heavy data transformation. This is a cleaner reporting architecture."

## What Would Be Needed in a Real Production System

To make this project production-ready, the following data should be added:

- Real machine IDs
- Timestamped sensor readings
- Actual runtime hours
- Downtime logs
- Repair start and end times
- Work order history
- Technician labor hours
- Maintenance cost
- Spare parts usage
- Production output
- Good units and defective units
- Quality inspection results
- Real-time IoT data

With these fields, the proxy KPIs could be replaced with measured plant KPIs.

## What I Would Say If Asked About Limitations

Use this answer in interviews:

"The main limitation is that the AI4I dataset does not include real downtime, repair duration, production output, or defect data. Because of that, I clearly documented MTBF, MTTR, Availability, Performance, Quality, and OEE as proxy metrics. I did not present them as actual plant measurements. This was an important decision because good analytics should be transparent about assumptions."

## What I Would Improve If Scaling to Production

If this project were implemented in a real plant, I would:

- Connect to live sensor data
- Integrate CMMS maintenance work orders
- Add downtime logs
- Add repair duration
- Add production output
- Add defect and scrap data
- Store risk scores directly in the database
- Automate Power BI refresh
- Add alerting for High Risk machines
- Validate KPI assumptions with plant engineers
- Replace proxy KPIs with real operational KPIs

## Final Interview Summary

This project uses proxy metrics because the dataset does not contain all real plant fields. However, every assumption is documented clearly. The project still demonstrates a complete industrial analytics workflow: data ingestion, database design, SQL analytics, data quality, KPI reporting, risk scoring, Power BI exports, dashboard design, and executive reporting.

The most important point is:

```text
I did not hide the limitations. I documented them and created reasonable analytical proxies for decision-support.
```

That is what makes the project professional and defensible.

