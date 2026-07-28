-- ============================================================
-- Parcel Logistics Warehouse Operations Analytics
-- KPI query layer
--
-- "Operational date" convention: a parcel is attributed to the calendar
-- date of its inbound_time (the day it entered the building). Labor rows
-- are already stored at that same daily grain via work_date.
-- ============================================================


-- ============================================================
-- 1. DAILY OPERATIONS SUMMARY
-- ============================================================
-- Business question: "What happened across the business today?"
-- Description: one row per day with the core KPIs side by side -
-- order volume, labor hours/cost, productivity, exception rate, and
-- late shipment rate - so a manager can scan a single day's health
-- before drilling into any one metric.
-- ============================================================
WITH daily_parcels AS (
    SELECT
        inbound_time::date                                                AS operational_date,
        count(*)                                                          AS order_volume,
        sum(CASE WHEN is_exception THEN 1 ELSE 0 END)                     AS exception_count,
        count(*) FILTER (WHERE delivery_time IS NOT NULL)                 AS delivered_count,
        count(*) FILTER (WHERE delivery_time > committed_delivery_time)   AS late_count
    FROM parcels
    GROUP BY inbound_time::date
),
daily_labor AS (
    SELECT
        work_date AS operational_date,
        sum(labor_hours) AS labor_hours,
        sum(labor_cost)  AS labor_cost
    FROM labor
    GROUP BY work_date
)
SELECT
    p.operational_date,
    p.order_volume,
    l.labor_hours,
    l.labor_cost,
    round(p.order_volume / NULLIF(l.labor_hours, 0), 2)                   AS parcels_per_labor_hour,
    round(100.0 * p.exception_count / NULLIF(p.order_volume, 0), 2)       AS exception_rate_pct,
    round(100.0 * p.late_count / NULLIF(p.delivered_count, 0), 2)         AS late_shipment_rate_pct
FROM daily_parcels p
JOIN daily_labor l ON l.operational_date = p.operational_date
ORDER BY p.operational_date DESC;
-- Tip: append `WHERE p.operational_date = (SELECT max(work_date) FROM labor)`
-- to pin this to the most recent day only.


-- ============================================================
-- 2. PRODUCTIVITY BY WAREHOUSE (AND SHIFT)
-- ============================================================
-- Business question: "Which warehouse/shift is least efficient right now?"
-- Description: parcels processed per labor hour, broken out by warehouse
-- and shift. Shift is included because "which shift has the lowest
-- productivity" is one of the standing morning questions - sorted
-- ascending so the worst performer surfaces first.
-- ============================================================
WITH shift_volume AS (
    SELECT
        warehouse_id,
        shift_id,
        inbound_time::date AS operational_date,
        count(*)           AS parcels
    FROM parcels
    GROUP BY warehouse_id, shift_id, inbound_time::date
)
SELECT
    w.warehouse_name,
    s.shift_name,
    sum(sv.parcels)                                             AS total_parcels,
    sum(l.labor_hours)                                          AS total_labor_hours,
    round(sum(sv.parcels) / NULLIF(sum(l.labor_hours), 0), 2)   AS parcels_per_labor_hour
FROM shift_volume sv
JOIN labor l
    ON l.warehouse_id = sv.warehouse_id
   AND l.shift_id     = sv.shift_id
   AND l.work_date    = sv.operational_date
JOIN warehouses w ON w.warehouse_id = sv.warehouse_id
JOIN shifts s      ON s.shift_id    = sv.shift_id
GROUP BY w.warehouse_name, s.shift_name
ORDER BY parcels_per_labor_hour ASC;


-- ============================================================
-- 3. LABOR COST TREND
-- ============================================================
-- Business question: "Is labor cost trending up, and where?"
-- Description: daily labor cost per warehouse alongside a trailing
-- 7-day moving average, so a single noisy day can be told apart from
-- a genuine upward trend.
-- ============================================================
WITH daily_cost AS (
    SELECT
        warehouse_id,
        work_date,
        sum(labor_cost) AS daily_labor_cost
    FROM labor
    GROUP BY warehouse_id, work_date
)
SELECT
    w.warehouse_name,
    dc.work_date,
    dc.daily_labor_cost,
    round(
        avg(dc.daily_labor_cost) OVER (
            PARTITION BY dc.warehouse_id
            ORDER BY dc.work_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_7day_avg_cost
FROM daily_cost dc
JOIN warehouses w ON w.warehouse_id = dc.warehouse_id
ORDER BY w.warehouse_name, dc.work_date;


-- ============================================================
-- 4. CARRIER PERFORMANCE RANKING
-- ============================================================
-- Business question: "Which carrier has the worst on-time pickup
-- performance?"
-- Description: average pickup delay and late-delivery rate per
-- carrier, ranked worst-to-best so underperforming carriers are
-- immediately visible.
-- ============================================================
WITH carrier_stats AS (
    SELECT
        c.carrier_name,
        count(*)                                                                       AS delivered_parcels,
        round(avg(extract(epoch FROM (p.pickup_time - p.outbound_time)) / 3600)::numeric, 2)
                                                                                         AS avg_pickup_delay_hrs,
        count(*) FILTER (WHERE p.delivery_time > p.committed_delivery_time)             AS late_count
    FROM parcels p
    JOIN carriers c ON c.carrier_id = p.carrier_id
    WHERE p.delivery_time IS NOT NULL
    GROUP BY c.carrier_name
)
SELECT
    carrier_name,
    delivered_parcels,
    avg_pickup_delay_hrs,
    round(100.0 * late_count / NULLIF(delivered_parcels, 0), 2)               AS late_shipment_rate_pct,
    rank() OVER (ORDER BY 100.0 * late_count / NULLIF(delivered_parcels, 0) DESC) AS worst_performance_rank
FROM carrier_stats
ORDER BY worst_performance_rank;


-- ============================================================
-- 5. EXCEPTION RATE BY WAREHOUSE
-- ============================================================
-- Business question: "Which warehouse had the highest exception rate?"
-- Description: share of parcels flagged as an exception (damaged,
-- mislabeled, misrouted, lost), by warehouse.
-- ============================================================
WITH warehouse_exceptions AS (
    SELECT
        warehouse_id,
        count(*)                                      AS total_parcels,
        sum(CASE WHEN is_exception THEN 1 ELSE 0 END) AS exception_count
    FROM parcels
    GROUP BY warehouse_id
)
SELECT
    w.warehouse_name,
    we.total_parcels,
    we.exception_count,
    round(100.0 * we.exception_count / NULLIF(we.total_parcels, 0), 2) AS exception_rate_pct
FROM warehouse_exceptions we
JOIN warehouses w ON w.warehouse_id = we.warehouse_id
ORDER BY exception_rate_pct DESC;


-- ============================================================
-- 6. MACHINE DOWNTIME SUMMARY
-- ============================================================
-- Business question: "Did machine downtime contribute to today's
-- delays?"
-- Description: downtime events and total/average downtime minutes by
-- warehouse and day of week, which is what exposes the Warehouse B /
-- Monday recurring-downtime pattern.
-- ============================================================
WITH downtime_detail AS (
    SELECT
        m.warehouse_id,
        md.start_time,
        extract(epoch FROM (md.end_time - md.start_time)) / 60 AS downtime_minutes
    FROM machine_downtime md
    JOIN machines m ON m.machine_id = md.machine_id
)
SELECT
    w.warehouse_name,
    to_char(dd.start_time, 'Day')      AS weekday,
    count(*)                            AS downtime_events,
    round(sum(dd.downtime_minutes), 0)  AS total_downtime_minutes,
    round(avg(dd.downtime_minutes), 0)  AS avg_downtime_minutes
FROM downtime_detail dd
JOIN warehouses w ON w.warehouse_id = dd.warehouse_id
GROUP BY w.warehouse_name, weekday, extract(dow FROM dd.start_time)
ORDER BY w.warehouse_name, extract(dow FROM dd.start_time);


-- ============================================================
-- 7. LATE SHIPMENT RATE
-- ============================================================
-- Business question: "Are we hitting our delivery commitments, and is
-- it getting better or worse?"
-- Description: weekly late-shipment rate per warehouse (delivered
-- parcels where delivery_time exceeded committed_delivery_time),
-- to distinguish a one-off bad day from a worsening trend.
-- ============================================================
WITH delivered AS (
    SELECT
        warehouse_id,
        date_trunc('week', inbound_time)::date                                AS week_start,
        count(*)                                                              AS delivered_parcels,
        count(*) FILTER (WHERE delivery_time > committed_delivery_time)       AS late_parcels
    FROM parcels
    WHERE delivery_time IS NOT NULL
    GROUP BY warehouse_id, date_trunc('week', inbound_time)
)
SELECT
    w.warehouse_name,
    d.week_start,
    d.delivered_parcels,
    d.late_parcels,
    round(100.0 * d.late_parcels / NULLIF(d.delivered_parcels, 0), 2) AS late_shipment_rate_pct
FROM delivered d
JOIN warehouses w ON w.warehouse_id = d.warehouse_id
ORDER BY w.warehouse_name, d.week_start;


-- ============================================================
-- 8. ROOT CAUSE ANALYSIS FOR LABOR COST INCREASE
-- ============================================================
-- Business question: "Why did labor cost increase today?"
-- Description: compares each warehouse/day's labor cost against its
-- own trailing 7-day baseline (excluding the day itself), flags
-- whether machine downtime or a month-end volume surge occurred that
-- day, and assigns a likely root cause. Sorted by the largest cost
-- increase first, so the top rows are the days most worth explaining.
-- ============================================================
WITH daily_labor AS (
    -- Pre-aggregate labor to warehouse+date *before* joining, so it never
    -- gets fanned out by the per-parcel grain of the parcels table below.
    SELECT
        warehouse_id,
        work_date,
        sum(labor_hours) AS labor_hours,
        sum(labor_cost)  AS labor_cost
    FROM labor
    GROUP BY warehouse_id, work_date
),
daily_parcel_volume AS (
    -- Pre-aggregate parcels to the same warehouse+date grain for the same reason.
    SELECT
        warehouse_id,
        inbound_time::date AS work_date,
        count(*)           AS order_volume
    FROM parcels
    GROUP BY warehouse_id, inbound_time::date
),
daily_metrics AS (
    SELECT
        dl.warehouse_id,
        dl.work_date,
        dl.labor_hours,
        dl.labor_cost,
        coalesce(dv.order_volume, 0) AS order_volume
    FROM daily_labor dl
    LEFT JOIN daily_parcel_volume dv
        ON dv.warehouse_id = dl.warehouse_id
       AND dv.work_date    = dl.work_date
),
downtime_flag AS (
    SELECT DISTINCT
        m.warehouse_id,
        md.start_time::date AS downtime_date
    FROM machine_downtime md
    JOIN machines m ON m.machine_id = md.machine_id
),
flagged_metrics AS (
    SELECT
        dm.*,
        (df.downtime_date IS NOT NULL) AS had_downtime,
        dm.work_date > (
            date_trunc('month', dm.work_date) + interval '1 month' - interval '1 day'
        )::date - 3                    AS is_month_end
    FROM daily_metrics dm
    LEFT JOIN downtime_flag df
        ON df.warehouse_id = dm.warehouse_id
       AND df.downtime_date = dm.work_date
),
metrics_with_baseline AS (
    SELECT
        fm.*,
        round(
            avg(fm.labor_cost) OVER (
                PARTITION BY fm.warehouse_id
                ORDER BY fm.work_date
                ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
            ), 2
        ) AS baseline_7day_avg_cost
    FROM flagged_metrics fm
)
SELECT
    w.warehouse_name,
    mwb.work_date,
    mwb.order_volume,
    mwb.labor_hours,
    mwb.labor_cost,
    mwb.baseline_7day_avg_cost,
    round(mwb.labor_cost - mwb.baseline_7day_avg_cost, 2) AS cost_variance_vs_baseline,
    mwb.had_downtime,
    mwb.is_month_end,
    CASE
        WHEN mwb.had_downtime AND mwb.is_month_end THEN 'Downtime + Month-End Surge'
        WHEN mwb.had_downtime                      THEN 'Machine Downtime'
        WHEN mwb.is_month_end                       THEN 'Month-End Volume Surge'
        ELSE 'Other / Volume Variance'
    END AS likely_root_cause
FROM metrics_with_baseline mwb
JOIN warehouses w ON w.warehouse_id = mwb.warehouse_id
WHERE mwb.baseline_7day_avg_cost IS NOT NULL
ORDER BY cost_variance_vs_baseline DESC
LIMIT 20;
