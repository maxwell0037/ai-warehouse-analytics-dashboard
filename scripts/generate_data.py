"""
Synthetic data generator for the parcel logistics analytics project.

Generates CSVs (data/*.csv) that get loaded into Postgres via sql/02_load_data.sql.
Encodes deliberate operational stories rather than pure randomness:

  - Warehouse B has recurring machine downtime on Mondays -> lower productivity,
    higher labor cost, higher exception rate that day.
  - Carrier C has occasional ("bad day") pickup delays -> late shipments.
  - Friday has the highest parcel volume of the week; weekends are lowest.
  - Night shift runs ~15% less productive than Morning/Afternoon.
  - The last 3 days of each month see a volume surge; labor hours/cost scale
    up with it (overtime pay), but productivity holds steady because extra
    staff is scheduled for it.

Run: python3 scripts/generate_data.py
"""

import csv
import calendar
import os
import random
from datetime import date, datetime, time, timedelta

SEED = 42
random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

END_DATE = date.today() - timedelta(days=1)
START_DATE = END_DATE - timedelta(days=59)  # 60-day window
NUM_DAYS = (END_DATE - START_DATE).days + 1

# ---------- Dimensions ----------

WAREHOUSES = [
    {"warehouse_id": 1, "warehouse_name": "Warehouse A", "city": "Dallas", "region": "South",
     "base_wage": 19.00, "base_daily_volume": 280},
    {"warehouse_id": 2, "warehouse_name": "Warehouse B", "city": "Chicago", "region": "Midwest",
     "base_wage": 23.00, "base_daily_volume": 320},
    {"warehouse_id": 3, "warehouse_name": "Warehouse C", "city": "Atlanta", "region": "Southeast",
     "base_wage": 18.00, "base_daily_volume": 260},
]

SHIFTS = [
    {"shift_id": 1, "shift_name": "Morning", "start_time": "06:00", "end_time": "14:00",
     "duration_hours": 8, "volume_share": 0.40, "target_productivity": 12.0, "night_diff": 0.0},
    {"shift_id": 2, "shift_name": "Afternoon", "start_time": "14:00", "end_time": "22:00",
     "duration_hours": 8, "volume_share": 0.40, "target_productivity": 12.0, "night_diff": 0.0},
    {"shift_id": 3, "shift_name": "Night", "start_time": "22:00", "end_time": "06:00",
     "duration_hours": 8, "volume_share": 0.20, "target_productivity": 10.2, "night_diff": 1.5},
]

CARRIERS = [
    {"carrier_id": 1, "carrier_name": "Carrier A"},
    {"carrier_id": 2, "carrier_name": "Carrier B"},
    {"carrier_id": 3, "carrier_name": "Carrier C"},  # the occasionally-poor performer
    {"carrier_id": 4, "carrier_name": "Carrier D"},
]
BAD_CARRIER_ID = 3
BAD_CARRIER_DAY_RATE = 0.18  # ~18% of days are "bad days" for Carrier C

MACHINES = []
machine_id = 1
for wh in WAREHOUSES:
    code = wh["warehouse_name"].split()[-1]  # A, B, C
    for n in (1, 2):
        MACHINES.append({
            "machine_id": machine_id,
            "warehouse_id": wh["warehouse_id"],
            "machine_name": f"WH-{code} Sorter {n}",
            "machine_type": "Automated Sorter",
        })
        machine_id += 1

DOWNTIME_REASONS = ["Belt Jam", "Sensor Fault", "Software Reboot", "Mechanical Failure", "Power Interruption"]
EXCEPTION_TYPES = ["Damaged", "Mislabeled", "Misrouted", "Lost"]
EXCEPTION_WEIGHTS = [0.35, 0.35, 0.20, 0.10]

# Day-of-week volume multipliers (Mon=0 ... Sun=6)
DOW_MULTIPLIER = {0: 0.85, 1: 0.80, 2: 0.95, 3: 1.00, 4: 1.25, 5: 0.65, 6: 0.55}

MONTH_END_VOLUME_MULT = 1.5
MONTH_END_OT_WAGE_MULT = 1.25

DOWNTIME_PRODUCTIVITY_PENALTY = 0.80  # 20% productivity loss on a downtime day
DOWNTIME_OT_WAGE_MULT = 1.10
BASE_EXCEPTION_RATE = 0.025
DOWNTIME_EXCEPTION_RATE = 0.09

SLA_HOURS = 48  # committed delivery = inbound + 48h (2-day ground service level)


def is_month_end(d: date) -> bool:
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    return d.day > days_in_month - 3


def trend_factor(day_index: int) -> float:
    return 0.95 + (day_index / max(NUM_DAYS - 1, 1)) * 0.15


def random_time_in_shift(d: date, shift: dict) -> datetime:
    start_h, start_m = map(int, shift["start_time"].split(":"))
    start_dt = datetime.combine(d, time(start_h, start_m))
    offset_seconds = random.uniform(0, shift["duration_hours"] * 3600)
    return start_dt + timedelta(seconds=offset_seconds)


def build_downtime_events():
    """Return list of downtime event rows, and a set of (warehouse_id, date) flagged as downtime days."""
    events = []
    downtime_days = set()
    machines_by_wh = {}
    for m in MACHINES:
        machines_by_wh.setdefault(m["warehouse_id"], []).append(m)

    for i in range(NUM_DAYS):
        d = START_DATE + timedelta(days=i)
        for wh in WAREHOUSES:
            if wh["warehouse_name"] == "Warehouse B" and d.weekday() == 0:  # Monday
                prob = 0.70
            else:
                prob = 0.08
            if random.random() < prob:
                machine = random.choice(machines_by_wh[wh["warehouse_id"]])
                start_dt = datetime.combine(d, time(random.randint(6, 20), random.choice([0, 15, 30, 45])))
                duration_min = random.randint(45, 180)
                end_dt = start_dt + timedelta(minutes=duration_min)
                events.append({
                    "machine_id": machine["machine_id"],
                    "start_time": start_dt.isoformat(sep=" "),
                    "end_time": end_dt.isoformat(sep=" "),
                    "reason": random.choice(DOWNTIME_REASONS),
                })
                downtime_days.add((wh["warehouse_id"], d))
    return events, downtime_days


def build_bad_carrier_days():
    bad_days = set()
    for i in range(NUM_DAYS):
        d = START_DATE + timedelta(days=i)
        if random.random() < BAD_CARRIER_DAY_RATE:
            bad_days.add(d)
    return bad_days


def generate():
    os.makedirs(DATA_DIR, exist_ok=True)
    downtime_events, downtime_days = build_downtime_events()
    bad_carrier_days = build_bad_carrier_days()

    parcel_rows = []
    labor_rows = []

    for i in range(NUM_DAYS):
        d = START_DATE + timedelta(days=i)
        dow_mult = DOW_MULTIPLIER[d.weekday()]
        month_end = is_month_end(d)
        trend = trend_factor(i)

        for wh in WAREHOUSES:
            wh_downtime_today = (wh["warehouse_id"], d) in downtime_days
            day_volume = wh["base_daily_volume"] * dow_mult * trend
            if month_end:
                day_volume *= MONTH_END_VOLUME_MULT

            for shift in SHIFTS:
                noise = random.uniform(0.90, 1.10)
                shift_volume = max(0, round(day_volume * shift["volume_share"] * noise))

                # ---- parcels ----
                exception_rate = DOWNTIME_EXCEPTION_RATE if wh_downtime_today else BASE_EXCEPTION_RATE
                for _ in range(shift_volume):
                    inbound_dt = random_time_in_shift(d, shift)

                    sort_delay_h = random.uniform(2.0, 6.0) if wh_downtime_today else random.uniform(0.5, 3.0)
                    sort_dt = inbound_dt + timedelta(hours=sort_delay_h)
                    outbound_dt = sort_dt + timedelta(hours=random.uniform(0.5, 2.0))

                    carrier = random.choice(CARRIERS)
                    pickup_date = outbound_dt.date()
                    if carrier["carrier_id"] == BAD_CARRIER_ID and pickup_date in bad_carrier_days:
                        pickup_delay_h = random.uniform(10.0, 20.0)
                    elif random.random() < 0.05:
                        pickup_delay_h = random.uniform(6.0, 12.0)
                    else:
                        pickup_delay_h = random.uniform(0.5, 4.0)
                    pickup_dt = outbound_dt + timedelta(hours=pickup_delay_h)

                    delivery_dt = pickup_dt + timedelta(hours=random.uniform(20.0, 40.0))
                    committed_dt = inbound_dt + timedelta(hours=SLA_HOURS)

                    is_exception = random.random() < exception_rate
                    exception_type = ""
                    if is_exception:
                        exception_type = random.choices(EXCEPTION_TYPES, weights=EXCEPTION_WEIGHTS, k=1)[0]
                        if exception_type == "Lost":
                            delivery_dt = None

                    parcel_rows.append({
                        "warehouse_id": wh["warehouse_id"],
                        "shift_id": shift["shift_id"],
                        "carrier_id": carrier["carrier_id"],
                        "inbound_time": inbound_dt.isoformat(sep=" "),
                        "sort_time": sort_dt.isoformat(sep=" "),
                        "outbound_time": outbound_dt.isoformat(sep=" "),
                        "pickup_time": pickup_dt.isoformat(sep=" "),
                        "delivery_time": delivery_dt.isoformat(sep=" ") if delivery_dt else "",
                        "committed_delivery_time": committed_dt.isoformat(sep=" "),
                        "is_exception": "true" if is_exception else "false",
                        "exception_type": exception_type,
                    })

                # ---- labor ----
                target_productivity = shift["target_productivity"]
                wage = wh["base_wage"] + shift["night_diff"]

                if wh_downtime_today:
                    effective_productivity = target_productivity * DOWNTIME_PRODUCTIVITY_PENALTY
                    wage *= DOWNTIME_OT_WAGE_MULT
                else:
                    effective_productivity = target_productivity

                if month_end:
                    wage *= MONTH_END_OT_WAGE_MULT
                    # productivity intentionally NOT penalized: extra staff is scheduled for the surge

                hours_noise = random.uniform(0.95, 1.05)
                labor_hours = round((shift_volume / effective_productivity) * hours_noise, 2)
                labor_cost = round(labor_hours * wage * random.uniform(0.98, 1.02), 2)

                labor_rows.append({
                    "warehouse_id": wh["warehouse_id"],
                    "shift_id": shift["shift_id"],
                    "work_date": d.isoformat(),
                    "labor_hours": labor_hours,
                    "labor_cost": labor_cost,
                })

    write_csv("warehouses.csv", WAREHOUSES,
              ["warehouse_id", "warehouse_name", "city", "region"])
    write_csv("shifts.csv", SHIFTS,
              ["shift_id", "shift_name", "start_time", "end_time"])
    write_csv("carriers.csv", CARRIERS,
              ["carrier_id", "carrier_name"])
    write_csv("machines.csv", MACHINES,
              ["machine_id", "warehouse_id", "machine_name", "machine_type"])
    write_csv("machine_downtime.csv", downtime_events,
              ["machine_id", "start_time", "end_time", "reason"])
    write_csv("parcels.csv", parcel_rows,
              ["warehouse_id", "shift_id", "carrier_id", "inbound_time", "sort_time",
               "outbound_time", "pickup_time", "delivery_time", "committed_delivery_time",
               "is_exception", "exception_type"])
    write_csv("labor.csv", labor_rows,
              ["warehouse_id", "shift_id", "work_date", "labor_hours", "labor_cost"])

    print(f"Date range: {START_DATE} to {END_DATE} ({NUM_DAYS} days)")
    print(f"Parcels:          {len(parcel_rows):,}")
    print(f"Labor rows:       {len(labor_rows):,}")
    print(f"Downtime events:  {len(downtime_events):,}")
    wh_b_id = next(w["warehouse_id"] for w in WAREHOUSES if w["warehouse_name"] == "Warehouse B")
    monday_downtimes = sum(1 for (wh_id, d) in downtime_days if wh_id == wh_b_id and d.weekday() == 0)
    other_downtimes = sum(1 for (wh_id, d) in downtime_days if not (wh_id == wh_b_id and d.weekday() == 0))
    print(f"Warehouse B Monday downtime days: {monday_downtimes}")
    print(f"All other downtime days:         {other_downtimes}")
    print(f"Carrier C bad days: {len(bad_carrier_days)} / {NUM_DAYS}")


def write_csv(filename, rows, fieldnames):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


if __name__ == "__main__":
    generate()
