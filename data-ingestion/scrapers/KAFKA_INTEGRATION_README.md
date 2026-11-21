# VoYatra Kafka Integration Guide

## Overview
Real-time flight data scraping with Kafka integration. Data flows from local machine → Kafka (VM) → Storage (VM).

```
┌─────────────────────────────────────────┐
│ LOCAL MACHINE (VS Code)                 │
├─────────────────────────────────────────┤
│  flight_scraper.py                      │
│     ↓ (scrapes flights)                 │
│  kafka_flight_producer.py               │
│     ↓ (sends to Kafka)                  │
└─────────────────────────────────────────┘
              ↓
    Kafka: 10.7.1.120:9092
    Topic: flight-data
              ↓
┌─────────────────────────────────────────┐
│ VM (10.7.1.120)                         │
├─────────────────────────────────────────┤
│  Kafka Broker (port 9092)               │
│     ↓                                    │
│  Consumer (flight_consumer_local.py)    │
│     ↓                                    │
│  /home/cloudera/voyatra_data/           │
│  flights_YYYYMMDD_HHMMSS.json           │
└─────────────────────────────────────────┘
```

## VM Configuration

**VM Details:**
- IP Address: `10.7.1.120`
- Hostname: `quickstart`
- Username: `cloudera`
- Password: `cloudera`
- SSH: `ssh cloudera@10.7.1.120`

**Kafka Configuration:**
- Broker: `10.7.1.120:9092`
- Zookeeper: `10.7.1.120:2181`
- Topic: `flight-data`
- Partitions: 1
- Replication Factor: 1

**Data Storage:**
- Directory: `/home/cloudera/voyatra_data/`
- Format: Newline-Delimited JSON (NDJSON)
- Batch Size: 10 records per file
- Naming: `flights_YYYYMMDD_HHMMSS.json`

## Setup Instructions

### 1. Install Dependencies
```powershell
pip install kafka-python playwright pandas
playwright install chromium
```

### 2. Test Connectivity
```powershell
# Test network connection
Test-NetConnection -ComputerName 10.7.1.120 -Port 9092

# Test Kafka connection
python test_kafka_connection.py
```

Expected output:
```
✅ TEST MESSAGE SENT SUCCESSFULLY!
   Topic: flight-data
   Partition: 0
   Offset: XXX
```

## Usage

### Option 1: Scrape Flights (Main Workflow)

Run the interactive flight scraper:
```powershell
python flight_scraper.py
```

**What it does:**
1. Prompts for search parameters (from, to, date, class, etc.)
2. Opens Booking.com in browser
3. User fills search form manually
4. Scrapes flight results
5. **Sends each flight to Kafka in real-time**
6. Saves local CSV backup
7. Displays results in terminal

**Example interaction:**
```
📍 From city: Mumbai
📍 To city: Delhi
📅 Departure date: 1 (tomorrow)
✈️ Trip type: 1 (one-way)
👥 Number of adults: 1
💺 Cabin class: 1 (Economy)
🛫 Direct flights only: y

[Browser opens → User fills form → Press Enter]

✅ Found 16 flights
📡 Sending to Kafka...
✅ Sent 16/16 flights to Kafka
💾 VM will save to: /home/cloudera/voyatra_data/
```

### Option 2: Monitor Kafka Topic (Optional)

In a **separate terminal**, run the monitor:
```powershell
python local_monitor.py
```

**What it does:**
- Connects to Kafka topic `flight-data`
- Displays incoming flights in real-time
- Shows flight details, prices, times
- Read-only (doesn't save files)
- Press Ctrl+C to stop

**Example output:**
```
📨 Message #1 at 15:30:45
┌──────────────────────────────────────────────────────┐
│ AI847*               Air India                       │
├──────────────────────────────────────────────────────┤
│ Route:    Mumbai → Delhi
│ Time:     9:00 PM → 11:15 PM
│ Duration: 2h 15m              Stops: Non-stop
│ Price:    ₹7241
│ Date:     2025-11-21
└──────────────────────────────────────────────────────┘
```

## Data Format

### Scraped Flight Object
```python
@dataclass
class Flight:
    airline: str = ""              # "Air India", "IndiGo"
    departure_time: str = ""       # "9:00 PM"
    arrival_time: str = ""         # "11:15 PM"
    duration: str = ""             # "2h 15m"
    price: str = ""                # "INR7,241.92"
    stops: str = ""                # "Non-stop", "1 stop"
    departure_city: str = ""       # "Mumbai"
    arrival_city: str = ""         # "Delhi"
    scraped_at: str = ""           # ISO timestamp
```

### Kafka Message (JSON)
```json
{
  "flight_number": "AI847",
  "source": "Mumbai",
  "destination": "Delhi",
  "price": "7241",
  "airline": "Air India",
  "departure_time": "9:00 PM",
  "arrival_time": "11:15 PM",
  "duration": "2h 15m",
  "date": "2025-11-21",
  "stops": "Non-stop",
  "scraped_at": "2025-11-21T15:30:45.123456",
  "flight_number_generated": true
}
```

**Note:** Flight numbers are auto-generated using pattern `{airline_code}{random_3_digits}` (e.g., AI847, 6E392) since Booking.com doesn't display them.

### VM Storage Format (NDJSON)
```json
{"flight_number":"AI847","source":"Mumbai","destination":"Delhi","price":"7241"}
{"flight_number":"6E392","source":"Mumbai","destination":"Delhi","price":"8364"}
{"flight_number":"SG451","source":"Mumbai","destination":"Delhi","price":"7501"}
... (10 records per file)
```

## File Structure

```
data-ingestion/scrapers/
├── flight_scraper.py              # Main scraper (interactive)
├── kafka_flight_producer.py       # Kafka producer class
├── test_kafka_connection.py       # Connection test
├── local_monitor.py               # Real-time monitor
├── KAFKA_INTEGRATION_README.md    # This file
└── data/raw/flights/              # Local CSV backups
    └── mumbai_delhi_YYYYMMDD_HHMMSS.csv
```

## Troubleshooting

### "Kafka connection failed"
```powershell
# 1. Check VM is reachable
ping 10.7.1.120

# 2. Check Kafka port
Test-NetConnection -ComputerName 10.7.1.120 -Port 9092

# 3. SSH to VM and check Kafka
ssh cloudera@10.7.1.120
jps | grep Kafka
```

### "No flights found"
- Ensure search results are fully loaded in browser
- Wait for page to stabilize before pressing Enter
- Check if Booking.com changed their HTML structure

### "Monitor shows no messages"
- Monitor only shows **new** messages (auto_offset_reset='latest')
- Run scraper in another terminal to generate new messages
- Or modify monitor to read from 'earliest' offset

### Check VM data files
```bash
ssh cloudera@10.7.1.120
ls -lh /home/cloudera/voyatra_data/
cat /home/cloudera/voyatra_data/flights_*.json | jq .
```

## Workflow Examples

### Full Workflow (Terminal 1)
```powershell
# Terminal 1: Run scraper
cd d:\VoYatra\data-ingestion\scrapers
python flight_scraper.py
# [Follow prompts → scrape → data sent to Kafka]
```

### With Monitoring (Terminal 1 + 2)
```powershell
# Terminal 1: Monitor Kafka
cd d:\VoYatra\data-ingestion\scrapers
python local_monitor.py
# [Watching for new messages...]

# Terminal 2: Run scraper
cd d:\VoYatra\data-ingestion\scrapers
python flight_scraper.py
# [Data appears in Terminal 1 in real-time!]
```

## Kafka Producer Features

**FlightKafkaProducer class:**
- ✅ Auto-connect to VM Kafka
- ✅ Generate flight numbers from airline codes
- ✅ Transform Flight dataclass to Kafka JSON format
- ✅ Send flights one-by-one (real-time) or in batches
- ✅ Compression (gzip) for network efficiency
- ✅ Retry logic (3 attempts)
- ✅ Error handling (graceful degradation if Kafka unavailable)
- ✅ Context manager support (`with` statement)
- ✅ Logging of all operations

## Next Steps

1. ✅ Scraper working
2. ✅ Kafka integration complete
3. ✅ Monitor script ready
4. 🔄 Test with real searches
5. 📊 Verify data on VM
6. 🚀 Production deployment

## Support

For issues or questions:
1. Check logs in scraper output
2. Run `test_kafka_connection.py` to verify connectivity
3. SSH to VM to check consumer logs
4. Review Kafka logs on VM: `/var/log/kafka/server.log`

---

**Status:** ✅ Ready for production use
**Last Updated:** 2025-11-21
**Author:** VoYatra Team
