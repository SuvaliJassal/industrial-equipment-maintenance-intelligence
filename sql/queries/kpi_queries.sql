/*
Layer 2: SQL KPI Query Layer
Database: data/database/maintenance.db
SQL dialect: SQLite only

Run sql/views/analytics_views.sql before executing these KPI queries.
*/

/* 1. Failure Rate
Business Purpose:
Measure the overall share of observations where machine failure occurred.

SQL Logic:
Total failed observations divided by total observations.

Expected Output:
total_observations, failure_count, failure_rate, failure_rate_percent.

Business Interpretation:
Failure rate is the baseline reliability indicator. A rising failure rate means
maintenance teams should investigate operating conditions, machine type, or
failure-mode concentration.
*/
SELECT
    COUNT(*) AS total_observations,
    SUM(machine_failure) AS failure_count,
    ROUND(1.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 6) AS failure_rate,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent
FROM machine_analytics;

/* 2. Failure Rate by Machine Type
Business Purpose:
Compare failure exposure across machine/product quality types.

SQL Logic:
Group by machine_type and calculate failure count divided by observation count.

Expected Output:
machine_type, total_observations, failure_count, failure_rate_percent.

Business Interpretation:
Types with high failure rates may need different maintenance intervals,
operating policies, or process controls.
*/
SELECT
    machine_type,
    COUNT(*) AS total_observations,
    SUM(machine_failure) AS failure_count,
    ROUND(1.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 6) AS failure_rate,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent
FROM machine_analytics
GROUP BY machine_type
ORDER BY failure_rate_percent DESC;

/* 3. MTBF
Business Purpose:
Estimate how many operating observations occur between failures.

SQL Logic:
Total observations divided by total failures. The AI4I dataset does not contain
true timestamped runtime, so this KPI is an observation-based MTBF proxy.

Expected Output:
total_observations, failure_count, mtbf_observations.

Business Interpretation:
Higher MTBF means the equipment population runs longer between failure events.
Lower MTBF identifies weaker reliability and higher maintenance exposure.
*/
SELECT
    COUNT(*) AS total_observations,
    SUM(machine_failure) AS failure_count,
    ROUND(1.0 * COUNT(*) / NULLIF(SUM(machine_failure), 0), 4) AS mtbf_observations
FROM machine_analytics;

/* 4. MTTR
Business Purpose:
Estimate average repair burden per failure.

SQL Logic:
Assign a repair-time proxy by failure category and divide total repair proxy
minutes by total failures. AI4I has no actual repair duration column.

Expected Output:
failure_count, total_repair_time_proxy_minutes, mttr_proxy_minutes.

Business Interpretation:
MTTR proxy helps rank failure categories by likely maintenance effort and
supports capacity planning when real downtime data is unavailable.
*/
WITH repair_proxy AS (
    SELECT
        CASE
            WHEN normalized_failure_category = 'Tool Wear Failure' THEN 90.0
            WHEN normalized_failure_category = 'Heat Dissipation Failure' THEN 75.0
            WHEN normalized_failure_category = 'Power Failure' THEN 60.0
            WHEN normalized_failure_category = 'Overstrain Failure' THEN 80.0
            WHEN normalized_failure_category = 'Random Failure' THEN 45.0
            WHEN normalized_failure_category = 'Unclassified Failure' THEN 60.0
            ELSE 0.0
        END AS repair_time_proxy_minutes
    FROM vw_failure_analysis
    WHERE machine_failure = 1
)
SELECT
    COUNT(*) AS failure_count,
    ROUND(SUM(repair_time_proxy_minutes), 4) AS total_repair_time_proxy_minutes,
    ROUND(SUM(repair_time_proxy_minutes) / NULLIF(COUNT(*), 0), 4) AS mttr_proxy_minutes
FROM repair_proxy;

/* 5. Availability
Business Purpose:
Estimate the proportion of potential operating capacity not consumed by repair burden.

SQL Logic:
Use the standard proxy formula MTBF / (MTBF + MTTR), where MTBF is measured in
observations and MTTR is a repair-time proxy.

Expected Output:
mtbf_observations, mttr_proxy_minutes, availability.

Business Interpretation:
Availability indicates whether failures and repair burden are reducing the
equipment population's ability to remain production-ready.
*/
WITH kpi AS (
    SELECT
        ROUND(1.0 * COUNT(*) / NULLIF(SUM(machine_failure), 0), 4) AS mtbf_observations
    FROM machine_analytics
),
repair_proxy AS (
    SELECT
        SUM(
            CASE
                WHEN normalized_failure_category = 'Tool Wear Failure' THEN 90.0
                WHEN normalized_failure_category = 'Heat Dissipation Failure' THEN 75.0
                WHEN normalized_failure_category = 'Power Failure' THEN 60.0
                WHEN normalized_failure_category = 'Overstrain Failure' THEN 80.0
                WHEN normalized_failure_category = 'Random Failure' THEN 45.0
                WHEN normalized_failure_category = 'Unclassified Failure' THEN 60.0
                ELSE 0.0
            END
        ) / NULLIF(COUNT(*), 0) AS mttr_proxy_minutes
    FROM vw_failure_analysis
    WHERE machine_failure = 1
)
SELECT
    kpi.mtbf_observations,
    ROUND(repair_proxy.mttr_proxy_minutes, 4) AS mttr_proxy_minutes,
    ROUND(
        kpi.mtbf_observations / NULLIF(kpi.mtbf_observations + repair_proxy.mttr_proxy_minutes, 0),
        6
    ) AS availability
FROM kpi
CROSS JOIN repair_proxy;

/* 6. Performance
Business Purpose:
Measure how close machines operate to the observed ideal rotational speed.

SQL Logic:
Average performance_ratio from vw_machine_performance, where ratio equals
rotational_speed_rpm divided by 2861 RPM, the AI4I maximum observed reference.

Expected Output:
avg_performance, avg_performance_percent.

Business Interpretation:
Lower performance can indicate speed losses, under-utilization, or operating
constraints that reduce equipment output.
*/
SELECT
    ROUND(AVG(performance_ratio), 6) AS avg_performance,
    ROUND(100.0 * AVG(performance_ratio), 4) AS avg_performance_percent
FROM vw_machine_performance;

/* 7. Quality
Business Purpose:
Estimate the share of observations that did not experience machine failure.

SQL Logic:
Non-failed observations divided by total observations.

Expected Output:
good_observations, total_observations, quality, quality_percent.

Business Interpretation:
Quality represents failure-free operation in this dataset. Lower quality means
more production exposure to machine failure and potential scrap or rework risk.
*/
SELECT
    SUM(good_observation_flag) AS good_observations,
    COUNT(*) AS total_observations,
    ROUND(1.0 * SUM(good_observation_flag) / NULLIF(COUNT(*), 0), 6) AS quality,
    ROUND(100.0 * SUM(good_observation_flag) / NULLIF(COUNT(*), 0), 4) AS quality_percent
FROM vw_machine_performance;

/* 8. OEE
Business Purpose:
Combine availability, performance, and quality into a single equipment
effectiveness indicator.

SQL Logic:
Read the calculated OEE from vw_maintenance_kpis.

Expected Output:
availability, performance, quality, oee, oee_percent.

Business Interpretation:
OEE helps leaders identify whether losses are driven by downtime, speed loss,
or failure-free quality performance.
*/
SELECT
    availability,
    performance,
    quality,
    oee,
    ROUND(100.0 * oee, 4) AS oee_percent
FROM vw_maintenance_kpis;

/* 9. Machine Reliability Score
Business Purpose:
Create a single reliability score that can be monitored by leadership.

SQL Logic:
Use weighted penalties for failure rate, quality loss, performance loss, and
maintenance burden.

Expected Output:
machine_reliability_score.

Business Interpretation:
Higher scores indicate healthier equipment performance. Lower scores identify
areas where failures, repair burden, and operating losses are combining.
*/
SELECT
    ROUND(machine_reliability_score, 4) AS machine_reliability_score
FROM vw_maintenance_kpis;

/* 10. Maintenance Burden Index
Business Purpose:
Estimate maintenance workload intensity per observation.

SQL Logic:
Total repair-time proxy minutes divided by total observations.

Expected Output:
maintenance_burden_index.

Business Interpretation:
Higher burden means maintenance capacity is being consumed more heavily by the
current failure mix.
*/
SELECT
    maintenance_burden_index
FROM vw_maintenance_kpis;

/* 11. Risk Distribution
Business Purpose:
Understand how observations are distributed across risk bands.

SQL Logic:
Aggregate vw_risk_summary across machine type and risk dimensions.

Expected Output:
risk_band, observation_count, failure_count, failure_rate_percent,
observation_share_percent.

Business Interpretation:
Risk distribution helps maintenance leaders understand whether the population
is concentrated in low-risk operation or drifting toward high-risk states.
*/
WITH totals AS (
    SELECT SUM(observation_count) AS all_observations
    FROM vw_risk_summary
)
SELECT
    risk_band,
    SUM(observation_count) AS observation_count,
    SUM(failure_count) AS failure_count,
    ROUND(100.0 * SUM(failure_count) / NULLIF(SUM(observation_count), 0), 4) AS failure_rate_percent,
    ROUND(100.0 * SUM(observation_count) / NULLIF(totals.all_observations, 0), 4) AS observation_share_percent
FROM vw_risk_summary
CROSS JOIN totals
GROUP BY risk_band
ORDER BY
    CASE risk_band
        WHEN 'Critical Risk' THEN 1
        WHEN 'High Risk' THEN 2
        WHEN 'Moderate Risk' THEN 3
        ELSE 4
    END;

