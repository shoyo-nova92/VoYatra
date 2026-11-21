"""
Replay a previously scraped flights CSV into Kafka.

Demo safety net: if Booking.com blocks the live scraper or changes its layout,
replay a saved CSV (from data/raw/flights/) and the rest of the pipeline
(Kafka -> local_monitor.py / Kafka UI) behaves exactly the same.

Usage:
    python replay_to_kafka.py                      # newest CSV in data/raw/flights
    python replay_to_kafka.py path/to/file.csv     # specific file
    python replay_to_kafka.py --delay 0.5          # seconds between messages (default 0.7)
"""

import argparse
import glob
import os
import sys
import time
from types import SimpleNamespace

import pandas as pd

from kafka_flight_producer import FlightKafkaProducer, KAFKA_BROKER, KAFKA_TOPIC

FIELDS = ["airline", "departure_time", "arrival_time", "duration", "price",
          "stops", "departure_city", "arrival_city", "scraped_at"]


def newest_csv():
    files = glob.glob(os.path.join("data", "raw", "flights", "*.csv"))
    return max(files, key=os.path.getmtime) if files else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="flights CSV (default: newest in data/raw/flights)")
    ap.add_argument("--delay", type=float, default=0.7, help="seconds between messages")
    args = ap.parse_args()

    path = args.csv or newest_csv()
    if not path or not os.path.exists(path):
        sys.exit("❌ No CSV found. Run flight_scraper.py once first, or pass a CSV path.")

    df = pd.read_csv(path, dtype=str).fillna("")
    print(f"📂 Replaying {len(df)} flights from {path}")
    print(f"📡 Target: {KAFKA_TOPIC} @ {KAFKA_BROKER}\n")

    sent = 0
    with FlightKafkaProducer() as producer:
        if not producer.connected:
            sys.exit("❌ Kafka not reachable. Is `docker compose up -d` running?")
        for _, row in df.iterrows():
            flight = SimpleNamespace(**{f: row.get(f, "") for f in FIELDS})
            if producer.send_flight(flight, flight.departure_city or "Unknown", flight.arrival_city or "Unknown"):
                sent += 1
            time.sleep(args.delay)

    print(f"\n✅ Replayed {sent}/{len(df)} flights")


if __name__ == "__main__":
    main()
