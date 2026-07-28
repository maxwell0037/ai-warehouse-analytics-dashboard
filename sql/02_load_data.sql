-- ============================================================
-- Load generated CSVs into the schema created by 01_schema.sql
-- Run from the project root with: psql -d <database> -f sql/02_load_data.sql
-- (uses \copy, a psql client-side command, so relative paths resolve
--  against the directory you run psql from)
-- ============================================================

\copy warehouses(warehouse_id, warehouse_name, city, region) FROM 'data/warehouses.csv' WITH (FORMAT csv, HEADER true)
\copy shifts(shift_id, shift_name, start_time, end_time) FROM 'data/shifts.csv' WITH (FORMAT csv, HEADER true)
\copy carriers(carrier_id, carrier_name) FROM 'data/carriers.csv' WITH (FORMAT csv, HEADER true)
\copy machines(machine_id, warehouse_id, machine_name, machine_type) FROM 'data/machines.csv' WITH (FORMAT csv, HEADER true)

\copy parcels(warehouse_id, shift_id, carrier_id, inbound_time, sort_time, outbound_time, pickup_time, delivery_time, committed_delivery_time, is_exception, exception_type) FROM 'data/parcels.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy labor(warehouse_id, shift_id, work_date, labor_hours, labor_cost) FROM 'data/labor.csv' WITH (FORMAT csv, HEADER true)
\copy machine_downtime(machine_id, start_time, end_time, reason) FROM 'data/machine_downtime.csv' WITH (FORMAT csv, HEADER true)

-- Dimension IDs were loaded explicitly from CSV, so their SERIAL sequences
-- need to be advanced past the max loaded value before any future manual insert.
SELECT setval(pg_get_serial_sequence('warehouses', 'warehouse_id'), (SELECT MAX(warehouse_id) FROM warehouses));
SELECT setval(pg_get_serial_sequence('shifts', 'shift_id'), (SELECT MAX(shift_id) FROM shifts));
SELECT setval(pg_get_serial_sequence('carriers', 'carrier_id'), (SELECT MAX(carrier_id) FROM carriers));
SELECT setval(pg_get_serial_sequence('machines', 'machine_id'), (SELECT MAX(machine_id) FROM machines));
