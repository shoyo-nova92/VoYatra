# VoYatra technical specification

VoYatra turns flight search results into local CSV exports and Kafka events. An operator can inspect events in a terminal or Kafka UI and replay a previous CSV when a live search is unavailable. A separate hotel workflow exports listing data locally. The Scrapy hotels-and-reviews spider generates synthetic records for experimentation.

This specification describes how to reconstruct the checked-in project and identifies improvements that would change its current behavior. See [the showcase recap](plan.md), [agent responsibilities](agent.md), and [maintenance procedures](skills.md).

## System layout

| Component | Responsibility |
| --- | --- |
| `data-ingestion/docker-compose.yml` | Single-node Kafka in KRaft mode and Kafka UI |
| `scrapers/flight_scraper.py` | Interactive search or saved HTML input, shared parser, CSV export and Kafka submission |
| `scrapers/kafka_flight_producer.py` | Adapter from extraction rows to UTF-8 JSON Kafka events |
| `scrapers/replay_to_kafka.py` | Replay explicit or latest CSV through the same producer |
| `scrapers/local_monitor.py` | Subscribe to the configured topic and display decoded messages |
| `scrapers/test_kafka_connection.py` | Send one synthetic `TEST001` smoke event and print delivery metadata |
| `scrapers/booking_hotel_scraper.py` | Extract hotel listing cards and export CSV and Excel |
| `scrapers/production_hotel_scraper.py` | Compose the hotel scraper into a multi-city run or a custom city search |
| `scrapers/travel_scrapers/` | Separate Scrapy settings, item definitions, pipelines and synthetic hotel/review spider |

Paths beginning with `scrapers/` in this document are relative to `data-ingestion/`. Raw exports are relative to the process working directory. Run scraper commands from `data-ingestion/scrapers` so exports and CSV discovery agree.

## Rebuild and run locally

1. Create `data-ingestion/scrapers` and `data-ingestion/config` beneath the project root. Add the Compose definition and Python dependencies. Keep virtual environments, local environment files, logs and raw exports out of Git.
2. Install Python, Docker with Compose, and Playwright Chromium. These commands assume a PowerShell session at the root.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r data-ingestion/requirements.txt
   .\.venv\Scripts\python.exe -m playwright install chromium
   docker compose -f data-ingestion/docker-compose.yml config --quiet
   docker compose -f data-ingestion/docker-compose.yml up -d
   docker compose -f data-ingestion/docker-compose.yml ps
   ```

3. Define one Kafka broker/controller with `apache/kafka:3.9.0`. Advertise `localhost:9092` to host clients and `kafka:29092` to Docker clients. Use a separate controller listener on `9093`. Configure one default partition, replication factors of one for internal topics, minimum transaction ISR of one, and automatic topic creation. Configure `provectuslabs/kafka-ui:v0.7.2` on host port `8080` with the Docker listener as its bootstrap server. Check container logs if the UI starts before Kafka is ready.
4. Implement the extraction, producer and monitor contracts below. Start the monitor in one shell before running a producer in another. Set the same environment variables in both.

   ```powershell
   Set-Location data-ingestion/scrapers
   $env:KAFKA_BROKER = 'localhost:9092'
   $env:KAFKA_TOPIC = 'flight-data-rebuild'
   ..\..\.venv\Scripts\python.exe local_monitor.py
   ```

   In the producer shell, repeat the directory and environment setup, then run one of these commands.

   ```powershell
   ..\..\.venv\Scripts\python.exe test_kafka_connection.py
   ..\..\.venv\Scripts\python.exe flight_scraper.py --html 'C:\path\flight-results.html'
   ..\..\.venv\Scripts\python.exe replay_to_kafka.py 'data/raw/flights/example.csv' --delay 0.7
   ```

5. Inspect the topic in Kafka UI at `http://localhost:8080`. Match its partition and offset to producer or monitor output. After the run, stop the consumer with Ctrl+C and stop the stack with `docker compose stop` from `data-ingestion`. The Compose file declares no named Kafka volume. Treat the container's data as disposable if containers are removed or recreated.

## Flight acquisition and extraction

- **Interactive mode.** Running `flight_scraper.py` without arguments prompts for origin, destination, departure date, trip type, optional return date, adults, children, cabin and direct-only preference. The script opens headed Chromium. The operator applies those choices in the browser manually and presses Enter in the terminal once results load. Scan open pages newest-first for a visible flight card or results summary, allowing up to 20 seconds. A summary can confirm navigation before cards are present. Stop if a results page never appears.
- **Saved HTML mode.** Read a UTF-8 or UTF-8 BOM HTML file from `--html`. A browser provenance comment identifying the Booking.com flight search form triggers a CLI error. Files without the comment still need inspection for rendered cards. Prompt for both cities and load the HTML in an offline Chromium context with JavaScript disabled. Use the same parser as live mode. The supplied cities label the output. Verify them against the page before extracting.
- **Selectors and extraction.** Try flight-card test IDs, then class-based and broader result selectors. For each candidate use visible text. Derive the first two time values from 12-hour patterns when available, otherwise use 24-hour patterns. Look for a recognizable airline token, a price, duration and stop text. The first selector that yields accepted records wins. A card is currently accepted if airline, price or departure time is populated. Remaining string fields can be empty. The broader fallback pairs up to five prices with time matches from the body and may combine unrelated text. Treat those rows as low-confidence and check the original cards before downstream use.
- **Local output.** Export the extracted rows with pandas to `data/raw/flights/<from>_<to>_<YYYYMMDD_HHMMSS>.csv`, without a dataframe index. Columns in order are `airline,departure_time,arrival_time,duration,price,stops,departure_city,arrival_city,scraped_at`. Dates and times retain their observed text except `scraped_at`, which is the local ISO extraction timestamp. Empty results produce no CSV and no Kafka send. A nonempty run attempts Kafka first and writes its CSV after the producer step returns, including when the broker could not initialize.

## Kafka event contract

Host flight tools read `KAFKA_BROKER` and `KAFKA_TOPIC` at module import after loading dotenv. Defaults are `localhost:9092` and `flight-data`. Set variables in the shell before starting Python. Legacy configs and Scrapy producers have their own defaults and should be traced separately.

| Event fields | Current transformation |
| --- | --- |
| `source`, `destination` | Supplied city labels. Replay uses CSV cities with an `Unknown` fallback. |
| `flight_number`, `flight_number_generated` | Airline code or prefix plus a random three-digit suffix, or `UNKNOWN000` for a blank airline. Generated flag is always true. |
| `price` | First integer-like substring without grouping commas, serialized as a string. Defaults to `"0"`. Currency and cents are lost in the event. |
| `airline` | Original extracted string or `Unknown`. |
| `departure_time`, `arrival_time`, `duration`, `stops` | Display strings with `N/A` fallbacks. |
| `date`, `scraped_at` | Producer's local calendar date and source extraction timestamp, with producer time as fallback. The event date represents publish day. |

Use kafka-python with JSON serialization, gzip, `acks=all`, three retries and a five-second delivery wait per row. Count successful acknowledgements individually. The normal producer logs offsets. The smoke sender provides explicit partition and offset. Acknowledgement proves broker acceptance and consumer receipt requires separate evidence.

Replay reads CSV columns as strings, replaces nulls with empty values, sends rows through the same adapter and sleeps between sends. If no path is given, use the newest matching CSV by modification time. Multiple runs append events, potentially with different generated flight numbers. There is no stable event key or transactional link between file export and broker delivery. Missing columns become blanks, so validate headers and route data before replaying unfamiliar exports.

The terminal monitor uses group `flight-monitor-local`, auto-commit and `latest` when no committed offset exists. Consumer construction alone provides insufficient evidence of assignment or receipt. A new consumer group starting after a send can skip that message, while a reused group can resume older data from its committed offset.

## Hotel workflows

- **Observed hotel listings.** Recreate the Playwright `BookingHotelScraper` around destination, check-in/out, occupancy and result limit. Build a search URL, wait for listing cards, and map each card to the `Hotel` dataclass. Columns cover name, location, nightly price in source text and numeric form, original price, discount, rating text and numeric score, review description/count, distance from center, amenities, property type, listing URL, image URL and free cancellation. Export via pandas to UTF-8 CSV and openpyxl Excel under `data/raw/hotels`. Use `test_booking.py` for a live smoke check and compare a row to a source card. Its output depends on site availability.
- **Synthetic hotels and reviews.** Register `hotels_reviews` under the Scrapy project described by `scrapy.cfg`. Keep synthetic hotel and review dictionaries linked by hotel ID, including generated ratings and sentiment. Preserve their synthetic provenance whenever exporting or demonstrating the data. Kafka publishing is commented out in the spider settings. Inspect effective pipelines before any Scrapy run that is expected to be local-only.
- **Legacy files.** `run_spider.py` imports the absent `simple_flight_spider`. The HDFS uploader, standalone producer and scraping starter under `scripts/` are empty, as are several config modules. Redis, Hadoop and other VM-era dependencies are outside the local showcase execution path.

## Acceptance for a clean rebuild

- A hand-authored HTML fixture with two distinct cards yields two CSV rows in header order. Verify the route, times, fare, duration and stops against each card. Include a sparse card and assert the intended meaning of blank fields.
- A search-form fixture with the provenance marker is rejected. A page with no usable cards produces no CSV and no send. Test multiple tabs separately so the results tab is chosen over the form.
- With Kafka unavailable, a nonempty extraction still writes a CSV after the failed connection attempt. With Kafka available, verify that an acknowledged event is visible at the expected topic/partition/offset.
- Replaying the same checked CSV to a disposable topic preserves the route and event schema. Report producer success count and observed message count separately. Account for repeated rows and repeated runs.
- A hotel fixture yields one listing per valid card. Check both export formats, including missing prices or ratings. Keep synthetic Scrapy output traceable to its generated hotel identifiers.

For a later production design, make currency and dates typed, introduce a stable event identity tied to source data, validate headers before publishing, track extraction confidence, and define recovery for partial sends. Each would require an explicit contract change and compatibility tests.
