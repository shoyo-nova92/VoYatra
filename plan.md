# VoYatra showcase recap

## Where I started

I wanted to show how VoYatra turns flight search results into structured records. I first verified the local Kafka connection by sending a test message, `TEST001`, to `flight-data`. The live Booking.com search was unreliable in the Chromium window launched by the scraper.

## How I got it working

I ran the Mumbai to Delhi search in Brave, where the flight results loaded. I added a way to pass the saved results page to `flight_scraper.py --html`. The first saved file turned out to be the search form, so I saved the tab with the actual flight cards and added a check that explains this mistake when it happens.

## Where I ended

I extracted flight records from the saved Brave results and published them to Kafka. Kafka UI showed a Mumbai to Delhi record at partition 0, offset 17. Some fields, including the airline on that record, were missing. For the showcase, I prepared `flight-data-showcase` and verified it started empty so I can show records arriving after the scraper runs.
