"""Database Insertion Script

Loads cleaned trip data and zone lookup into SQLite database.
Inserts data in 50,000-row chunks to manage memory efficiently.
"""

import pandas as pd
import sys
import os

# Get the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from backend.database import get_connection, create_tables

# First create the tables if they don't exist
create_tables()

conn = get_connection()

# Drop trips table to recreate with proper schema including id column
conn.execute("DROP TABLE IF EXISTS trips")
conn.commit()

# Recreate trips table with id column
conn.executescript("""
    CREATE TABLE trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pickup_datetime TEXT,
        dropoff_datetime TEXT,
        passenger_count INTEGER,
        trip_distance REAL,
        pu_location_id INTEGER,
        do_location_id INTEGER,
        fare_amount REAL,
        tip_amount REAL,
        total_amount REAL,
        payment_type INTEGER,
        trip_duration_minutes REAL,
        speed_mph REAL,
        fare_per_mile REAL,
        pickup_hour INTEGER,
        time_of_day TEXT,
        is_weekend INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_pickup_datetime ON trips(pickup_datetime);
    CREATE INDEX IF NOT EXISTS idx_pu_location ON trips(pu_location_id);
    CREATE INDEX IF NOT EXISTS idx_do_location ON trips(do_location_id);
    CREATE INDEX IF NOT EXISTS idx_time_of_day ON trips(time_of_day);
""")
conn.commit()

data_dir = os.path.join(project_root, "backend", "data")

# Load the zone lookup data - this is our dimension table
zones = pd.read_csv(os.path.join(data_dir, "taxi_zone_lookup.csv"))
zones.columns = ["location_id", "borough", "zone_name", "service_zone"]
zones.to_sql("zones", conn, if_exists="replace", index=False)
print(f"Loaded {len(zones)} zones")

# Now load the cleaned trip data - this is our fact table
trips = pd.read_parquet(os.path.join(data_dir, "cleaned_trips.parquet"))

# Select only the columns we need for the database
cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", "trip_distance",
        "PULocationID", "DOLocationID", "fare_amount", "tip_amount", "total_amount",
        "payment_type", "trip_duration_minutes", "speed_mph", "fare_per_mile",
        "pickup_hour", "time_of_day", "is_weekend"]

trips = trips[cols]

# Rename columns to match our database schema
trips.columns = ["pickup_datetime", "dropoff_datetime", "passenger_count", "trip_distance",
                 "pu_location_id", "do_location_id", "fare_amount", "tip_amount", "total_amount",
                 "payment_type", "trip_duration_minutes", "speed_mph", "fare_per_mile",
                 "pickup_hour", "time_of_day", "is_weekend"]

# Insert data in chunks to avoid memory issues with large datasets
chunk_size = 50000
for i in range(0, len(trips), chunk_size):
    chunk = trips.iloc[i:i+chunk_size]
    chunk.to_sql("trips", conn, if_exists="append", index=False)
    print(f"Inserted {min(i+chunk_size, len(trips))}/{len(trips)}")

conn.close()
print("Done!")
