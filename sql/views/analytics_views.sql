PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_machine_performance;
DROP VIEW IF EXISTS vw_failure_analysis;
DROP VIEW IF EXISTS vw_maintenance_kpis;
DROP VIEW IF EXISTS vw_risk_summary;
DROP VIEW IF EXISTS vw_powerbi_dataset;

CREATE VIEW vw_machine_performance AS
SELECT
    observation_id,
    product_id,
    machine_type,
    air_temperature_k,
    process_temperature_k,
    temperature_difference_k,
    rotational_speed_rpm,
    torque_nm,
    mechanical_power_watts,
    tool_wear_min,
    tool_wear_risk_level,
    operating_stress_score,
    machine_failure,
    failure_mode_count,
    primary_failure_mode,
    CASE
        WHEN rotational_speed_rpm >= 2500 THEN 'Very High Speed'
        WHEN rotational_speed_rpm >= 1800 THEN 'High Speed'
        WHEN rotational_speed_rpm >= 1200 THEN 'Standard Speed'
        ELSE 'Low Speed'
    END AS speed_band,
    CASE
        WHEN torque_nm >= 60 THEN 'Very High Torque'
        WHEN torque_nm >= 45 THEN 'High Torque'
        WHEN torque_nm >= 30 THEN 'Standard Torque'
        ELSE 'Low Torque'
    END AS torque_band,
    CASE
        WHEN operating_stress_score >= 75 THEN 'Critical Stress'
        WHEN operating_stress_score >= 50 THEN 'High Stress'
        WHEN operating_stress_score >= 25 THEN 'Moderate Stress'
        ELSE 'Low Stress'
    END AS operating_stress_band,
    ROUND(rotational_speed_rpm / 2861.0, 4) AS performance_ratio,
    CASE
        WHEN machine_failure = 1 THEN 0
        ELSE 1
    END AS good_observation_flag,
    source_file,
    ingestion_timestamp
FROM machine_analytics;

CREATE VIEW vw_failure_analysis AS
SELECT
    observation_id,
    product_id,
    machine_type,
    machine_failure,
    primary_failure_mode,
    failure_mode_count,
    twf,
    hdf,
    pwf,
    osf,
    rnf,
    tool_wear_min,
    tool_wear_risk_level,
    temperature_difference_k,
    rotational_speed_rpm,
    torque_nm,
    mechanical_power_watts,
    operating_stress_score,
    CASE
        WHEN twf = 1 THEN 'Tool Wear Failure'
        WHEN hdf = 1 THEN 'Heat Dissipation Failure'
        WHEN pwf = 1 THEN 'Power Failure'
        WHEN osf = 1 THEN 'Overstrain Failure'
        WHEN rnf = 1 THEN 'Random Failure'
        WHEN machine_failure = 1 THEN 'Unclassified Failure'
        ELSE 'No Failure'
    END AS normalized_failure_category,
    CASE
        WHEN machine_failure = 1 AND failure_mode_count > 1 THEN 'Multiple Failure Modes'
        WHEN machine_failure = 1 AND failure_mode_count = 1 THEN 'Single Failure Mode'
        WHEN machine_failure = 1 AND failure_mode_count = 0 THEN 'Unclassified Failure'
        ELSE 'No Failure'
    END AS failure_complexity,
    CASE
        WHEN machine_failure = 1 AND tool_wear_min >= 200 THEN 'Wear-Driven Failure'
        WHEN machine_failure = 1 AND temperature_difference_k >= 10 THEN 'Thermal Failure Pattern'
        WHEN machine_failure = 1 AND mechanical_power_watts >= 9000 THEN 'Power Load Failure Pattern'
        WHEN machine_failure = 1 AND operating_stress_score >= 75 THEN 'High Stress Failure Pattern'
        WHEN machine_failure = 1 THEN 'General Failure Pattern'
        ELSE 'No Failure'
    END AS failure_driver_group,
    source_file,
    ingestion_timestamp
FROM machine_analytics;

CREATE VIEW vw_maintenance_kpis AS
WITH base AS (
    SELECT
        COUNT(*) AS total_observations,
        SUM(machine_failure) AS total_failures,
        SUM(CASE WHEN machine_failure = 0 THEN 1 ELSE 0 END) AS non_failed_observations,
        AVG(performance_ratio) AS avg_performance_ratio,
        AVG(good_observation_flag) AS quality_ratio,
        AVG(
            CASE
                WHEN machine_failure = 1 THEN
                    CASE
                        WHEN primary_failure_mode = 'Tool Wear Failure' THEN 90.0
                        WHEN primary_failure_mode = 'Heat Dissipation Failure' THEN 75.0
                        WHEN primary_failure_mode = 'Power Failure' THEN 60.0
                        WHEN primary_failure_mode = 'Overstrain Failure' THEN 80.0
                        WHEN primary_failure_mode = 'Random Failure' THEN 45.0
                        ELSE 60.0
                    END
                ELSE 0.0
            END
        ) AS avg_repair_time_proxy_minutes,
        SUM(
            CASE
                WHEN machine_failure = 1 THEN
                    CASE
                        WHEN primary_failure_mode = 'Tool Wear Failure' THEN 90.0
                        WHEN primary_failure_mode = 'Heat Dissipation Failure' THEN 75.0
                        WHEN primary_failure_mode = 'Power Failure' THEN 60.0
                        WHEN primary_failure_mode = 'Overstrain Failure' THEN 80.0
                        WHEN primary_failure_mode = 'Random Failure' THEN 45.0
                        ELSE 60.0
                    END
                ELSE 0.0
            END
        ) AS total_repair_time_proxy_minutes
    FROM vw_machine_performance
),
calculated AS (
    SELECT
        total_observations,
        total_failures,
        non_failed_observations,
        ROUND(1.0 * total_failures / NULLIF(total_observations, 0), 6) AS failure_rate,
        ROUND(1.0 * total_observations / NULLIF(total_failures, 0), 4) AS mtbf_observations,
        ROUND(total_repair_time_proxy_minutes / NULLIF(total_failures, 0), 4) AS mttr_proxy_minutes,
        ROUND(avg_performance_ratio, 6) AS performance,
        ROUND(quality_ratio, 6) AS quality,
        ROUND(total_repair_time_proxy_minutes, 4) AS total_repair_time_proxy_minutes
    FROM base
)
SELECT
    total_observations,
    total_failures,
    failure_rate,
    mtbf_observations,
    mttr_proxy_minutes,
    ROUND(mtbf_observations / NULLIF(mtbf_observations + mttr_proxy_minutes, 0), 6) AS availability,
    performance,
    quality,
    ROUND(
        (mtbf_observations / NULLIF(mtbf_observations + mttr_proxy_minutes, 0))
        * performance
        * quality,
        6
    ) AS oee,
    ROUND(
        100
        - (failure_rate * 45)
        - ((1.0 - quality) * 25)
        - ((1.0 - performance) * 20)
        - (total_repair_time_proxy_minutes / NULLIF(total_observations, 0) * 10),
        4
    ) AS machine_reliability_score,
    ROUND(total_repair_time_proxy_minutes / NULLIF(total_observations, 0), 4) AS maintenance_burden_index
FROM calculated;

CREATE VIEW vw_risk_summary AS
SELECT
    machine_type,
    tool_wear_risk_level,
    CASE
        WHEN operating_stress_score >= 75 THEN 'Critical Risk'
        WHEN operating_stress_score >= 50 THEN 'High Risk'
        WHEN operating_stress_score >= 25 THEN 'Moderate Risk'
        ELSE 'Low Risk'
    END AS risk_band,
    COUNT(*) AS observation_count,
    SUM(machine_failure) AS failure_count,
    ROUND(1.0 * SUM(machine_failure) / NULLIF(COUNT(*), 0), 6) AS failure_rate,
    ROUND(AVG(tool_wear_min), 4) AS avg_tool_wear_min,
    ROUND(AVG(temperature_difference_k), 4) AS avg_temperature_difference_k,
    ROUND(AVG(torque_nm), 4) AS avg_torque_nm,
    ROUND(AVG(mechanical_power_watts), 4) AS avg_mechanical_power_watts,
    ROUND(AVG(operating_stress_score), 4) AS avg_operating_stress_score
FROM machine_analytics
GROUP BY
    machine_type,
    tool_wear_risk_level,
    risk_band;

CREATE VIEW vw_powerbi_dataset AS
SELECT
    mp.observation_id,
    mp.product_id,
    mp.machine_type,
    mp.air_temperature_k,
    mp.process_temperature_k,
    mp.temperature_difference_k,
    mp.rotational_speed_rpm,
    mp.speed_band,
    mp.torque_nm,
    mp.torque_band,
    mp.mechanical_power_watts,
    mp.tool_wear_min,
    mp.tool_wear_risk_level,
    mp.operating_stress_score,
    mp.operating_stress_band,
    mp.performance_ratio,
    mp.good_observation_flag,
    fa.machine_failure,
    fa.normalized_failure_category,
    fa.failure_complexity,
    fa.failure_driver_group,
    fa.failure_mode_count,
    fa.twf,
    fa.hdf,
    fa.pwf,
    fa.osf,
    fa.rnf,
    CASE
        WHEN mp.machine_failure = 1 THEN
            CASE
                WHEN fa.normalized_failure_category = 'Tool Wear Failure' THEN 90.0
                WHEN fa.normalized_failure_category = 'Heat Dissipation Failure' THEN 75.0
                WHEN fa.normalized_failure_category = 'Power Failure' THEN 60.0
                WHEN fa.normalized_failure_category = 'Overstrain Failure' THEN 80.0
                WHEN fa.normalized_failure_category = 'Random Failure' THEN 45.0
                ELSE 60.0
            END
        ELSE 0.0
    END AS repair_time_proxy_minutes,
    CASE
        WHEN mp.machine_failure = 1
          OR mp.tool_wear_risk_level = 'High'
          OR mp.operating_stress_score >= 75 THEN 1
        ELSE 0
    END AS high_risk_flag,
    mp.source_file,
    mp.ingestion_timestamp
FROM vw_machine_performance AS mp
INNER JOIN vw_failure_analysis AS fa
    ON mp.observation_id = fa.observation_id;

