-- ============================================================
-- Parcel Logistics Warehouse Operations Analytics
-- Schema: dimension tables + fact tables (star schema, analytics-oriented)
-- ============================================================

-- ---------- DIMENSION TABLES ----------

-- Facilities being compared across KPIs ("which warehouse...")
CREATE TABLE warehouses (
    warehouse_id   SERIAL PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL UNIQUE,
    city           VARCHAR(100),
    region         VARCHAR(100)
);

-- Shift types; kept as a small lookup table to avoid free-text drift (e.g. "Morning" vs "morning")
CREATE TABLE shifts (
    shift_id   SERIAL PRIMARY KEY,
    shift_name VARCHAR(20) NOT NULL UNIQUE,
    start_time TIME NOT NULL,
    end_time   TIME NOT NULL
);

-- External carriers responsible for pickup and final-mile delivery
CREATE TABLE carriers (
    carrier_id   SERIAL PRIMARY KEY,
    carrier_name VARCHAR(100) NOT NULL UNIQUE
);

-- Sorting equipment, scoped to a single warehouse
CREATE TABLE machines (
    machine_id   SERIAL PRIMARY KEY,
    warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
    machine_name VARCHAR(100) NOT NULL,
    machine_type VARCHAR(50)
);

-- ---------- FACT TABLES ----------

-- Core operational fact table: one row per parcel, timestamped at each workflow stage.
-- Drives Order Volume, Exception Rate, Late Shipment Rate, Carrier Performance,
-- and the volume side of Productivity (joined against labor).
CREATE TABLE parcels (
    parcel_id               BIGSERIAL PRIMARY KEY,
    warehouse_id            INT NOT NULL REFERENCES warehouses(warehouse_id),
    shift_id                INT NOT NULL REFERENCES shifts(shift_id),
    carrier_id              INT REFERENCES carriers(carrier_id),  -- NULL until Carrier Pickup stage

    inbound_time             TIMESTAMP NOT NULL,
    sort_time                TIMESTAMP,
    outbound_time             TIMESTAMP,
    pickup_time               TIMESTAMP,
    delivery_time              TIMESTAMP,
    committed_delivery_time    TIMESTAMP NOT NULL,

    is_exception             BOOLEAN NOT NULL DEFAULT FALSE,
    exception_type            VARCHAR(50),

    CHECK (exception_type IS NULL OR is_exception = TRUE)
);

-- Aggregated daily labor hours/cost, grained by warehouse + shift + date (not per-employee).
-- Drives Labor Hours and Labor Cost directly; joined with parcels for Productivity.
CREATE TABLE labor (
    labor_id     SERIAL PRIMARY KEY,
    warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
    shift_id     INT NOT NULL REFERENCES shifts(shift_id),
    work_date    DATE NOT NULL,
    labor_hours  NUMERIC(6,2) NOT NULL CHECK (labor_hours >= 0),
    labor_cost   NUMERIC(10,2) NOT NULL CHECK (labor_cost >= 0),

    UNIQUE (warehouse_id, shift_id, work_date)
);

-- One row per downtime event on a sorting machine.
-- Drives Machine Downtime, and is correlated against parcels/labor by warehouse + date
-- to answer "did downtime contribute to today's delays."
CREATE TABLE machine_downtime (
    downtime_id  SERIAL PRIMARY KEY,
    machine_id   INT NOT NULL REFERENCES machines(machine_id),
    start_time   TIMESTAMP NOT NULL,
    end_time     TIMESTAMP NOT NULL,
    reason       VARCHAR(100),

    CHECK (end_time > start_time)
);
