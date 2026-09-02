PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS machine_raw (
    raw_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    udi TEXT NOT NULL,
    product_id TEXT NOT NULL,
    machine_type TEXT NOT NULL,
    air_temperature_k TEXT NOT NULL,
    process_temperature_k TEXT NOT NULL,
    rotational_speed_rpm TEXT NOT NULL,
    torque_nm TEXT NOT NULL,
    tool_wear_min TEXT NOT NULL,
    machine_failure TEXT NOT NULL,
    twf TEXT NOT NULL,
    hdf TEXT NOT NULL,
    pwf TEXT NOT NULL,
    osf TEXT NOT NULL,
    rnf TEXT NOT NULL,
    source_file TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    UNIQUE (udi, product_id, source_file)
);

CREATE TABLE IF NOT EXISTS machine_clean (
    observation_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL,
    machine_type TEXT NOT NULL CHECK (machine_type IN ('L', 'M', 'H')),
    air_temperature_k REAL NOT NULL CHECK (air_temperature_k > 0),
    process_temperature_k REAL NOT NULL CHECK (process_temperature_k > 0),
    rotational_speed_rpm INTEGER NOT NULL CHECK (rotational_speed_rpm > 0),
    torque_nm REAL NOT NULL CHECK (torque_nm >= 0),
    tool_wear_min INTEGER NOT NULL CHECK (tool_wear_min >= 0),
    machine_failure INTEGER NOT NULL CHECK (machine_failure IN (0, 1)),
    twf INTEGER NOT NULL CHECK (twf IN (0, 1)),
    hdf INTEGER NOT NULL CHECK (hdf IN (0, 1)),
    pwf INTEGER NOT NULL CHECK (pwf IN (0, 1)),
    osf INTEGER NOT NULL CHECK (osf IN (0, 1)),
    rnf INTEGER NOT NULL CHECK (rnf IN (0, 1)),
    source_file TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (product_id, source_file)
);

CREATE TABLE IF NOT EXISTS machine_analytics (
    analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    machine_type TEXT NOT NULL CHECK (machine_type IN ('L', 'M', 'H')),
    air_temperature_k REAL NOT NULL,
    process_temperature_k REAL NOT NULL,
    temperature_difference_k REAL NOT NULL,
    rotational_speed_rpm INTEGER NOT NULL,
    torque_nm REAL NOT NULL,
    mechanical_power_watts REAL NOT NULL,
    tool_wear_min INTEGER NOT NULL,
    tool_wear_risk_level TEXT NOT NULL CHECK (tool_wear_risk_level IN ('Low', 'Medium', 'High')),
    operating_stress_score REAL NOT NULL,
    machine_failure INTEGER NOT NULL CHECK (machine_failure IN (0, 1)),
    failure_mode_count INTEGER NOT NULL CHECK (failure_mode_count >= 0),
    primary_failure_mode TEXT NOT NULL,
    twf INTEGER NOT NULL CHECK (twf IN (0, 1)),
    hdf INTEGER NOT NULL CHECK (hdf IN (0, 1)),
    pwf INTEGER NOT NULL CHECK (pwf IN (0, 1)),
    osf INTEGER NOT NULL CHECK (osf IN (0, 1)),
    rnf INTEGER NOT NULL CHECK (rnf IN (0, 1)),
    source_file TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (observation_id) REFERENCES machine_clean (observation_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    UNIQUE (observation_id, source_file)
);

CREATE INDEX IF NOT EXISTS idx_machine_clean_machine_type
    ON machine_clean (machine_type);

CREATE INDEX IF NOT EXISTS idx_machine_clean_machine_failure
    ON machine_clean (machine_failure);

CREATE INDEX IF NOT EXISTS idx_machine_clean_product_id
    ON machine_clean (product_id);

CREATE INDEX IF NOT EXISTS idx_machine_analytics_failure_mode
    ON machine_analytics (primary_failure_mode);

CREATE INDEX IF NOT EXISTS idx_machine_analytics_risk
    ON machine_analytics (tool_wear_risk_level, operating_stress_score);

