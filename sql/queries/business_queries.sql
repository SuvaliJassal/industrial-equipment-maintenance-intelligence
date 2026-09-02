/*
Layer 2: SQL Analytics and Business Query Layer
Database: data/database/maintenance.db
SQL dialect: SQLite only

Run sql/views/analytics_views.sql before executing these queries.
*/

/* 1. Failure Rate by Machine Type
Business Purpose:
Compare reliability across machine/product quality types.

SQL Logic:
Group observations by machine_type and divide failed observations by total observations.

Expected Output:
machine_type, total_observations, failure_count, failure_rate_percent.

Business Interpretation:
Machine types with higher failure rates should receive deeper root-cause analysis,
more frequent condition monitoring, or tighter operating limits.
*/
SELECT
    machine_type,
    COUNT(*) AS total_observations,
    SUM(machine_failure) AS failure_count,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent
FROM machine_analytics
GROUP BY machine_type
ORDER BY failure_rate_percent DESC;

/* 2. Failure Count by Failure Category
Business Purpose:
Identify which failure categories create the largest reliability burden.

SQL Logic:
Use the normalized failure category view and count failed observations by category.

Expected Output:
normalized_failure_category, failure_count, failure_share_percent.

Business Interpretation:
The largest categories point to the maintenance programs that will deliver the
highest impact if improved first.
*/
SELECT
    normalized_failure_category,
    COUNT(*) AS failure_count,
    ROUND(
        100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM vw_failure_analysis WHERE machine_failure = 1), 0),
        4
    ) AS failure_share_percent
FROM vw_failure_analysis
WHERE machine_failure = 1
GROUP BY normalized_failure_category
ORDER BY failure_count DESC;

/* 3. Average Tool Wear Before Failure
Business Purpose:
Estimate the tool wear level typically observed when failures occur.

SQL Logic:
Average tool_wear_min for failed machines and compare by failure category.

Expected Output:
normalized_failure_category, failed_observations, avg_tool_wear_min.

Business Interpretation:
Higher average wear before failure supports preventive replacement thresholds
and tool-life planning.
*/
SELECT
    normalized_failure_category,
    COUNT(*) AS failed_observations,
    ROUND(AVG(tool_wear_min), 4) AS avg_tool_wear_min,
    MIN(tool_wear_min) AS min_tool_wear_min,
    MAX(tool_wear_min) AS max_tool_wear_min
FROM vw_failure_analysis
WHERE machine_failure = 1
GROUP BY normalized_failure_category
ORDER BY avg_tool_wear_min DESC;

/* 4. Average Torque for Failed vs Non-Failed Machines
Business Purpose:
Evaluate whether torque differs between failed and healthy operating records.

SQL Logic:
Group by machine_failure and calculate torque summary statistics.

Expected Output:
machine_status, observation_count, avg_torque_nm, min_torque_nm, max_torque_nm.

Business Interpretation:
Large torque differences may indicate load-related stress, incorrect operating
settings, or mechanical overload patterns.
*/
SELECT
    CASE WHEN machine_failure = 1 THEN 'Failed' ELSE 'Non-Failed' END AS machine_status,
    COUNT(*) AS observation_count,
    ROUND(AVG(torque_nm), 4) AS avg_torque_nm,
    ROUND(MIN(torque_nm), 4) AS min_torque_nm,
    ROUND(MAX(torque_nm), 4) AS max_torque_nm
FROM machine_analytics
GROUP BY machine_failure
ORDER BY machine_failure DESC;

/* 5. Temperature Difference Impact Analysis
Business Purpose:
Understand how process-to-air temperature difference relates to failure behavior.

SQL Logic:
Bucket temperature_difference_k into bands and calculate failure rate per band.

Expected Output:
temperature_difference_band, observation_count, failure_count, failure_rate_percent.

Business Interpretation:
Higher failure rates in specific thermal bands indicate thermal operating
conditions that may need process controls or cooling improvements.
*/
WITH temperature_bands AS (
    SELECT
        CASE
            WHEN temperature_difference_k < 7 THEN 'Below 7 K'
            WHEN temperature_difference_k < 9 THEN '7 to <9 K'
            WHEN temperature_difference_k < 11 THEN '9 to <11 K'
            ELSE '11 K and Above'
        END AS temperature_difference_band,
        machine_failure
    FROM machine_analytics
)
SELECT
    temperature_difference_band,
    COUNT(*) AS observation_count,
    SUM(machine_failure) AS failure_count,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent
FROM temperature_bands
GROUP BY temperature_difference_band
ORDER BY failure_rate_percent DESC;

/* 6. Operating Stress Analysis
Business Purpose:
Measure how stress bands relate to failure concentration.

SQL Logic:
Use operating_stress_band from vw_machine_performance and calculate failure
rate, average tool wear, and average mechanical power.

Expected Output:
operating_stress_band, observations, failures, failure_rate_percent,
avg_tool_wear_min, avg_mechanical_power_watts.

Business Interpretation:
High stress bands with elevated failure rates should be prioritized for
operational limit review and preventive maintenance scheduling.
*/
SELECT
    operating_stress_band,
    COUNT(*) AS observations,
    SUM(machine_failure) AS failures,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent,
    ROUND(AVG(tool_wear_min), 4) AS avg_tool_wear_min,
    ROUND(AVG(mechanical_power_watts), 4) AS avg_mechanical_power_watts
FROM vw_machine_performance
GROUP BY operating_stress_band
ORDER BY failure_rate_percent DESC;

/* 7. High Risk Machine Identification
Business Purpose:
Identify observations that should be prioritized for maintenance review.

SQL Logic:
Flag high-risk records using failure status, high tool wear, critical operating
stress, or multiple failure mode indicators.

Expected Output:
observation_id, product_id, machine_type, risk_reason, operating_stress_score,
tool_wear_min, machine_failure.

Business Interpretation:
These records represent the most urgent maintenance investigation targets.
*/
SELECT
    observation_id,
    product_id,
    machine_type,
    CASE
        WHEN machine_failure = 1 THEN 'Observed Failure'
        WHEN failure_mode_count > 1 THEN 'Multiple Failure Signals'
        WHEN tool_wear_risk_level = 'High' THEN 'High Tool Wear'
        WHEN operating_stress_score >= 75 THEN 'Critical Operating Stress'
        ELSE 'Elevated Risk'
    END AS risk_reason,
    ROUND(operating_stress_score, 4) AS operating_stress_score,
    tool_wear_min,
    tool_wear_risk_level,
    machine_failure,
    primary_failure_mode
FROM machine_analytics
WHERE machine_failure = 1
   OR failure_mode_count > 1
   OR tool_wear_risk_level = 'High'
   OR operating_stress_score >= 75
ORDER BY
    machine_failure DESC,
    operating_stress_score DESC,
    tool_wear_min DESC;

/* 8. Top Failure Drivers
Business Purpose:
Rank operating and condition signals by their observed failure rates.

SQL Logic:
Create driver categories from tool wear, thermal difference, torque, mechanical
power, and operating stress, then aggregate failure rate by driver.

Expected Output:
failure_driver, observation_count, failure_count, failure_rate_percent.

Business Interpretation:
The highest-rate drivers help maintenance teams focus on the conditions most
associated with failures.
*/
WITH driver_flags AS (
    SELECT 'High Tool Wear' AS failure_driver, machine_failure
    FROM machine_analytics
    WHERE tool_wear_risk_level = 'High'
    UNION ALL
    SELECT 'High Temperature Difference' AS failure_driver, machine_failure
    FROM machine_analytics
    WHERE temperature_difference_k >= 10
    UNION ALL
    SELECT 'High Torque' AS failure_driver, machine_failure
    FROM machine_analytics
    WHERE torque_nm >= 45
    UNION ALL
    SELECT 'High Mechanical Power' AS failure_driver, machine_failure
    FROM machine_analytics
    WHERE mechanical_power_watts >= 9000
    UNION ALL
    SELECT 'Critical Operating Stress' AS failure_driver, machine_failure
    FROM machine_analytics
    WHERE operating_stress_score >= 75
)
SELECT
    failure_driver,
    COUNT(*) AS observation_count,
    SUM(machine_failure) AS failure_count,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent
FROM driver_flags
GROUP BY failure_driver
ORDER BY failure_rate_percent DESC, failure_count DESC;

/* 9. Reliability Analysis by Product Type
Business Purpose:
Compare reliability behavior across AI4I product quality types.

SQL Logic:
Use machine_type as the product type and calculate failure rate, MTBF proxy,
average stress, and average wear.

Expected Output:
product_type, total_observations, failure_count, failure_rate_percent,
mtbf_observations, avg_operating_stress_score, avg_tool_wear_min.

Business Interpretation:
Product types with lower MTBF and higher stress should be monitored more
closely and may need process-specific maintenance strategies.
*/
SELECT
    machine_type AS product_type,
    COUNT(*) AS total_observations,
    SUM(machine_failure) AS failure_count,
    ROUND(100.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 4) AS failure_rate_percent,
    ROUND(1.0 * COUNT(*) / NULLIF(SUM(machine_failure), 0), 4) AS mtbf_observations,
    ROUND(AVG(operating_stress_score), 4) AS avg_operating_stress_score,
    ROUND(AVG(tool_wear_min), 4) AS avg_tool_wear_min
FROM machine_analytics
GROUP BY machine_type
ORDER BY failure_rate_percent DESC;

/* 10. Maintenance Burden Analysis
Business Purpose:
Estimate which failure categories create the highest maintenance workload.

SQL Logic:
Use repair-time proxy minutes by failure category and aggregate total and
average burden.

Expected Output:
normalized_failure_category, failure_count, total_repair_time_proxy_minutes,
avg_repair_time_proxy_minutes, maintenance_burden_share_percent.

Business Interpretation:
Categories with high total burden deserve priority because they consume the
most maintenance capacity.
*/
WITH failure_burden AS (
    SELECT
        normalized_failure_category,
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
    normalized_failure_category,
    COUNT(*) AS failure_count,
    ROUND(SUM(repair_time_proxy_minutes), 4) AS total_repair_time_proxy_minutes,
    ROUND(AVG(repair_time_proxy_minutes), 4) AS avg_repair_time_proxy_minutes,
    ROUND(
        100.0 * SUM(repair_time_proxy_minutes)
        / NULLIF((SELECT SUM(repair_time_proxy_minutes) FROM failure_burden), 0),
        4
    ) AS maintenance_burden_share_percent
FROM failure_burden
GROUP BY normalized_failure_category
ORDER BY total_repair_time_proxy_minutes DESC;

