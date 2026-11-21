# VoYatra maintenance procedures

These procedures can be run manually or used as task instructions for a project agent. Start with the [build and setup instructions](specs.md#rebuild-and-run-locally) and work from `data-ingestion/scrapers` for the Python entry points. Commands below assume the root virtual environment and PowerShell. Use the current configured interpreter if your environment differs.

## Inspect and extract saved flight results

1. Verify the route and source provenance. A file captured before flights render can contain the search form or an empty application shell. A browser-generated source URL is useful evidence when present. Check for actual card markup and visible text before relying on it.
2. Decide whether the run may send events. The saved-page CLI attempts Kafka publication when it finds rows. For extraction-only diagnostics, call `scrape_flight_results(page, params)` directly from a local fixture harness and avoid `publish_flights`. For an end-to-end run, set the approved topic first and then invoke the CLI.

   ```powershell
   ..\..\.venv\Scripts\python.exe flight_scraper.py --html 'C:\path\flight-results.html'
   ```

3. Compare results to the page. For each sampled card record the observed fare string, two times, stops and duration. Identify fields copied from user input and those derived from card text. Inspect broad-body fallback rows individually because prices and times may come from unrelated page elements.
4. Check CSV headers against the nine-field schema. Count blank values by column and confirm one record per expected card. Treat recurring route, times, price and stops as a possible duplicate signature. Distinct fares or itineraries can share those fields, so retain rows unless a documented rule resolves the ambiguity.
5. Report the filename, route, matched-card count, accepted row count, skips or duplicates with reasons, checked examples, and any Kafka activity. Ask for a better artifact if the capture cannot support the conclusions.

## Verify Kafka locally

1. From `data-ingestion`, run `docker compose config --quiet`, `docker compose ps` and, if needed, `docker compose logs --tail 50 kafka kafka-ui`. Start the stack with `docker compose up -d` when needed. Use the host listener from Python and the Docker listener from within Compose.
2. In each Python terminal set `$env:KAFKA_BROKER = 'localhost:9092'` and set `KAFKA_TOPIC` to the same approved topic. Confirm the UI is using the same Kafka cluster. If a fresh topic is needed, create it explicitly in Kafka UI or allow topic auto-creation and inspect where the consumer starts. Use a separate smoke topic to keep the showcase topic clean.
3. Start `local_monitor.py` before sending. A waiting terminal can still be assigning partitions. If receipt appears absent, inspect the topic directly in Kafka UI and check the group's committed offsets. The monitoring script reuses a named group with auto-commit.
4. Run `test_kafka_connection.py` only when sending the synthetic `TEST001` event is in scope. Capture partition and offset, then match those values and payload in Kafka UI or terminal output. A successful TCP check alone does not establish correct advertised listener configuration or successful JSON delivery.
5. Stop the monitor with Ctrl+C after observing the result. Record what was published and where. Use `docker compose stop` when a temporary stack should be stopped without removing its containers.

## Replay a known CSV

1. Choose an explicit CSV path whenever possible. The default selects the newest file by modification time, which may belong to another route.
2. Verify header names, city labels and row count. The replay tool treats missing cells and columns as empty, and can produce `Unknown` or placeholder values. Check missing currency or airline information before demonstrating the output.
3. Start monitoring the intended topic, then run the replay.

   ```powershell
   ..\..\.venv\Scripts\python.exe replay_to_kafka.py 'data/raw/flights/example.csv' --delay 0.7
   ```

4. Compare CSV rows, attempted sends, acknowledged sends and observed records. Inspect a sample JSON payload with its offset. A whole-file retry after partial success can add duplicates. Record the source row and observed acknowledgements before deciding whether a retry is appropriate.

## Diagnose a broken live or offline run

| Symptom | First evidence to collect |
| --- | --- |
| Piped or redirected Python output raises a UnicodeEncodeError | Python stdout encoding. Run the same command with python -X utf8 to support the scripts' emoji output. |
| Import or browser launch fails | Actual Python executable, installed dependency, Chromium installation and exact exception |
| Live search appears to finish but no page is detected | Open tab titles, whether results opened in a new tab, and whether cards or summary are visible |
| Saved HTML gives no rows | Encoding, provenance comment, card markup, then visible text with JavaScript disabled |
| Captured rows have blank or incorrect fields | Exact card text with sensitive details removed, selected selector and regex matches |
| CSV cannot be found | Working directory, returned output path and the CSV discovery directory |
| Producer fails despite an open port | Broker metadata listener, topic, timeout and client configuration |
| Producer reports success but the monitor sees nothing | Topic/partition/offset, group assignment, committed offsets and UI receipt |

Reproduce the earliest failure in isolation. Start with a tiny hand-authored fixture and a known-good example, then compare behavior against the original artifact. For changes to extraction, check form-only, empty, sparse and multi-card cases. For changes to delivery, check unavailable broker, one accepted publish and independent receipt. Record which checks needed an external website or running Docker and whether they were performed.

## Validate hotel exports and synthetic records

1. Use `booking_hotel_scraper.py`, `test_booking.py` or the production wrapper for listing exports. Verify destination, stay dates, result limit and output filename. Inspect one listing's name, nightly rate, rating, review count and URL against its card.
2. Check that CSV and Excel contain the same logical rows and distinguish missing values from actual zeros. Excel export uses openpyxl.
3. Use the Scrapy project for synthetic hotel and review records. Run `scrapy list` from the scraper directory to check discovery. Review effective pipelines before invoking the spider. Confirm that each generated review references a generated hotel and label both as synthetic in any downstream export.

## Validate repository changes

Run `git diff --check` and inspect the staged paths. Confirm Markdown links resolve, shell examples point to tracked commands and TOML files contain a unique `name`, a focused `description` and detailed `developer_instructions`. Keep examples and documentation aligned with the operational defaults. Include observed test results and unverified external behavior in the handoff.
