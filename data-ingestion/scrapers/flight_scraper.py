"""
VOYATRA FLIGHT SCRAPER
Interactive flight scraper - user inputs options in terminal, script fills website and scrapes
Sends data to Kafka topic 'flight-data' (broker from KAFKA_BROKER env var, default localhost:9092)
Author: VOYATRA Team
"""

from playwright.sync_api import Error as PlaywrightError, sync_playwright
import argparse
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import re
import time
from datetime import datetime, timedelta
import os
from dataclasses import dataclass, asdict
from kafka_flight_producer import FlightKafkaProducer, KAFKA_BROKER, KAFKA_TOPIC

BOOKING_FLIGHTS_URL = "https://www.booking.com/flights/index.html"

@dataclass
class Flight:
    airline: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""
    price: str = ""
    stops: str = ""
    departure_city: str = ""
    arrival_city: str = ""
    scraped_at: str = ""

def get_user_inputs():
    """Get flight search parameters from user"""
    
    print("✈️ VOYATRA FLIGHT SEARCH")
    print("="*40)
    print()
    
    # Get cities
    from_city = input("📍 From city (e.g., Mumbai, Delhi, Bangalore): ").strip()
    to_city = input("📍 To city (e.g., Delhi, Goa, Chennai): ").strip()
    
    # Get date
    print("\n📅 Departure date:")
    print("1. Tomorrow")
    print("2. Day after tomorrow") 
    print("3. Custom date (YYYY-MM-DD)")
    
    date_choice = input("Select (1-3): ").strip()
    
    if date_choice == "1":
        departure_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif date_choice == "2":
        departure_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    else:
        departure_date = input("Enter date (YYYY-MM-DD): ").strip()
    
    # Trip type
    print("\n✈️ Trip type:")
    print("1. One way")
    print("2. Round trip")
    print("3. Multi-city")
    
    trip_choice = input("Select (1-3): ").strip()
    trip_types = {"1": "one-way", "2": "round-trip", "3": "multi-city"}
    trip_type = trip_types.get(trip_choice, "one-way")
    
    # Return date for round trip
    return_date = None
    if trip_type == "round-trip":
        return_date = input("📅 Return date (YYYY-MM-DD): ").strip()
    
    # Number of passengers
    adults = input("\n👥 Number of adults (default 1): ").strip() or "1"
    children = input("👶 Number of children (default 0): ").strip() or "0"
    
    # Class
    print("\n💺 Cabin class:")
    print("1. Economy")
    print("2. Premium Economy")
    print("3. Business") 
    print("4. First Class")
    
    class_choice = input("Select (1-4): ").strip()
    classes = {"1": "Economy", "2": "Premium Economy", "3": "Business", "4": "First Class"}
    cabin_class = classes.get(class_choice, "Economy")
    
    # Direct flights only
    direct_only = input("\n🛫 Direct flights only? (y/n): ").strip().lower() == 'y'
    
    return {
        'from_city': from_city,
        'to_city': to_city,
        'departure_date': departure_date,
        'return_date': return_date,
        'trip_type': trip_type,
        'adults': adults,
        'children': children,
        'cabin_class': cabin_class,
        'direct_only': direct_only
    }

def manual_search_instructions(params):
    """Show manual search instructions with user's selected options"""
    
    print("\n" + "="*60)
    print("🌐 BROWSER OPENED - PLEASE FILL SEARCH FORM MANUALLY")
    print("="*60)
    print("📋 YOUR SELECTED OPTIONS:")
    print(f"   📍 From: {params['from_city']}")
    print(f"   📍 To: {params['to_city']}")
    print(f"   📅 Date: {params['departure_date']}")
    print(f"   👥 Passengers: {params['adults']} adults, {params['children']} children")
    print(f"   💺 Class: {params['cabin_class']}")
    print(f"   ✈️ Trip: {params['trip_type']}")
    if params['return_date']:
        print(f"   🔄 Return: {params['return_date']}")
    print(f"   🛫 Direct only: {'Yes' if params['direct_only'] else 'No'}")
    print()
    print("📝 STEPS:")
    print("1. Fill in the flight search form with YOUR OPTIONS above")
    print("2. Click SEARCH button")
    print("3. Wait for results to load completely")
    print("4. Come back here and press ENTER to scrape")
    print("="*60)
    
    return True

def wait_for_results_page(context, timeout_seconds=20):
    """Find loaded flight results, including searches that open a new tab."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for page in reversed(context.pages):
            try:
                cards = page.locator('[data-testid="flight_card"], [data-testid="flight-card"], .flight-card')
                summary = page.get_by_text(re.compile(r'\b(?:found|showing)\s+[\d,]+\s+flight options?\b', re.I))
                if cards.first.is_visible() or summary.first.is_visible():
                    return page
            except PlaywrightError:
                # A redirect or a closing tab can interrupt a locator query.
                continue
        time.sleep(0.25)
    return None


def scrape_flight_results(page, params):
    """Scrape flight results from the page"""
    
    print("🔍 Scraping flight results...")
    
    # Try to find flight containers using Booking.com specific selectors
    selectors = [
        '[data-testid="flight_card"]',
        '[data-testid="flight-card"]', 
        '.flight-card',
        '[class*="FlightSearchResult"]',
        '[class*="flight-result"]',
        '.sr-item',
        '[data-testid*="result"]'
    ]
    
    flights = []
    
    # First, let's try to get all visible text and analyze it
    try:
        page_content = page.content()
        print(f"📄 Page loaded with {len(page_content)} characters")
        
        # Look for specific flight data patterns in page content
        # Extract times (format like 3:40 AM, 10:35 AM)
        time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM))'
        times_found = re.findall(time_pattern, page_content, re.IGNORECASE)
        print(f"⏰ Found {len(times_found)} time entries: {times_found[:10]}")
        
        # Extract prices (INR format)
        price_pattern = r'INR\s*[\d,]+(?:\.\d{2})?'
        prices_found = re.findall(price_pattern, page_content)
        print(f"💰 Found {len(prices_found)} prices: {prices_found[:5]}")
        
        # Extract airlines
        airlines_pattern = r'(ITA Airways|Air India|IndiGo|SpiceJet|Vistara|GoAir|AirAsia India)'
        airlines_found = re.findall(airlines_pattern, page_content, re.IGNORECASE)
        print(f"✈️ Found airlines: {set(airlines_found)}")
        
    except Exception as e:
        print(f"Error analyzing page content: {e}")
    
    # Now try to scrape using different approaches
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            if len(elements) > 0:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
                
                for i, element in enumerate(elements):
                    try:
                        flight = Flight()
                        flight.departure_city = params['from_city']
                        flight.arrival_city = params['to_city']
                        flight.scraped_at = datetime.now().isoformat()
                        
                        # Get element text for analysis
                        element_text = element.inner_text()
                        print(f"Flight {i+1} text preview: {element_text[:200]}...")
                        
                        # Extract airline
                        airlines = ['ITA Airways', 'Air India', 'IndiGo', '6E', 'SpiceJet', 'SG', 'Vistara', 'UK', 'GoAir', 'G8', 'AirAsia']
                        for airline in airlines:
                            if airline in element_text:
                                flight.airline = airline
                                break
                        
                        # Extract times using regex (both 24hr and 12hr format)
                        times_12hr = re.findall(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', element_text, re.IGNORECASE)
                        times_24hr = re.findall(r'\b([0-2]?[0-9]:[0-5][0-9])\b', element_text)
                        
                        if times_12hr and len(times_12hr) >= 2:
                            flight.departure_time = times_12hr[0]
                            flight.arrival_time = times_12hr[1]
                        elif times_24hr and len(times_24hr) >= 2:
                            flight.departure_time = times_24hr[0]
                            flight.arrival_time = times_24hr[1]
                        
                        # Extract price (INR format)
                        prices = re.findall(r'INR\s*[\d,]+(?:\.\d{2})?', element_text)
                        if prices:
                            flight.price = prices[0]
                        else:
                            # Try other currency formats
                            other_prices = re.findall(r'[₹$]\s*[\d,]+', element_text)
                            if other_prices:
                                flight.price = other_prices[0]
                        
                        # Extract duration
                        durations = re.findall(r'\d+h\s*\d*m?|\d+\s*hr?\s*\d*m?', element_text)
                        if durations:
                            flight.duration = durations[0]
                        
                        # Extract stops info
                        if 'non-stop' in element_text.lower() or 'direct' in element_text.lower():
                            flight.stops = 'Non-stop'
                        elif '1 stop' in element_text.lower():
                            flight.stops = '1 stop'
                        elif 'stop' in element_text.lower():
                            stops_match = re.search(r'(\d+)\s*stops?', element_text, re.IGNORECASE)
                            if stops_match:
                                flight.stops = f"{stops_match.group(1)} stops"
                            else:
                                flight.stops = 'With stops'
                        
                        # Add flight if we have some useful data
                        if flight.airline or flight.price or flight.departure_time:
                            flights.append(flight)
                            print(f"✅ Added flight: {flight.airline} {flight.departure_time} → {flight.arrival_time} {flight.price}")
                        
                    except Exception as e:
                        print(f"Error processing flight {i+1}: {e}")
                        continue
                
                if flights:
                    break  # Stop after finding successful flights
                    
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    # If no flights found with standard selectors, try a broader approach
    if not flights:
        print("🔍 Trying broader search...")
        try:
            # Get all text and try to parse flight data patterns
            all_text = page.inner_text('body')
            
            # Look for price patterns
            price_matches = re.findall(r'INR\s*[\d,]+', all_text)
            time_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', all_text, re.IGNORECASE)
            
            if price_matches and time_matches:
                # Create flights from patterns found
                for i, price in enumerate(price_matches[:5]):  # Limit to first 5
                    flight = Flight()
                    flight.departure_city = params['from_city']
                    flight.arrival_city = params['to_city']
                    flight.scraped_at = datetime.now().isoformat()
                    flight.price = price
                    
                    if i*2 < len(time_matches):
                        flight.departure_time = time_matches[i*2]
                    if i*2+1 < len(time_matches):
                        flight.arrival_time = time_matches[i*2+1]
                    
                    flights.append(flight)
                    
        except Exception as e:
            print(f"Error in broader search: {e}")
    
    return flights

def publish_flights(flights, params):
    if flights:
        # Send to Kafka
        print("\n📡 SENDING TO KAFKA...")
        print("="*50)

        with FlightKafkaProducer() as kafka_producer:
            if kafka_producer.connected:
                success_count = kafka_producer.send_batch(
                    flights,
                    params['from_city'],
                    params['to_city']
                )
                print(f"✅ Sent {success_count}/{len(flights)} flights to Kafka")
                print(f"📋 Topic: {KAFKA_TOPIC} @ {KAFKA_BROKER}")
                print("💡 Watch them arrive live in local_monitor.py")
            else:
                print("⚠ Kafka not available - data saved locally only")

        print("="*50)

        # Save results locally (CSV backup)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"data/raw/flights/{params['from_city']}_{params['to_city']}_{timestamp}.csv"

        df = pd.DataFrame([asdict(flight) for flight in flights])
        df.to_csv(filename, index=False)

        print(f"\n✅ SUCCESS! Found {len(flights)} flights")
        print(f"💾 Local backup: {filename}")

        # Show results
        print("\n🏆 FLIGHT RESULTS:")
        print("-" * 50)
        for i, flight in enumerate(flights, 1):
            print(f"{i:2d}. {flight.airline}")
            print(f"    Time: {flight.departure_time} → {flight.arrival_time}")
            print(f"    Price: {flight.price}")
            print(f"    Duration: {flight.duration}")
            print(f"    Stops: {flight.stops}")
            print()
    else:
        print("❌ No flights found in results")
        print("💡 Make sure the search results have loaded completely")


def main():
    """Main function"""
    
    # Create directory
    os.makedirs('data/raw/flights', exist_ok=True)
    
    parser = argparse.ArgumentParser(description="Extract flights and publish them to Kafka.")
    parser.add_argument("--html", type=Path, help="Read a flight results page saved as HTML")
    args = parser.parse_args()
    if args.html:
        try:
            html = args.html.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            parser.error(f"Cannot read the saved HTML file: {error}")

        print(f"Booking.com Flights: {BOOKING_FLIGHTS_URL}")
        saved_url = re.search(r"<!-- saved from url=\(\d+\)(\S+)\s*-->", html[:1024])
        if saved_url:
            url = urlsplit(saved_url.group(1))
            if url.hostname in {"booking.com", "www.booking.com"} and url.path == "/flights/index.html":
                parser.error("This file was saved from the Booking.com search form. "
                             "Save the tab showing the flight cards and pass that file to --html.")
            if url.scheme == "https" and url.netloc.lower() == "flights.booking.com":
                print(f"Original results: {url.geturl()}")

        params = {
            "from_city": input("From city: ").strip(),
            "to_city": input("To city: ").strip(),
        }
        if not all(params.values()):
            parser.error("Enter both cities as shown on the saved results page.")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(java_script_enabled=False, offline=True)
            page = context.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            flights = scrape_flight_results(page, params)
            browser.close()
        publish_flights(flights, params)
        return

    # Get user inputs
    params = get_user_inputs()
    
    print("\n🚀 STARTING FLIGHT SEARCH")
    print("="*40)
    print(f"Route: {params['from_city']} → {params['to_city']}")
    print(f"Date: {params['departure_date']}")
    print(f"Passengers: {params['adults']} adults, {params['children']} children")
    print(f"Class: {params['cabin_class']}")
    print(f"Direct only: {params['direct_only']}")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Go to Booking.com flights
            print(f"🌐 Opening Booking.com Flights: {BOOKING_FLIGHTS_URL}")
            page.goto(BOOKING_FLIGHTS_URL, timeout=60000)
            
            # Show manual instructions
            manual_search_instructions(params)
            
            # Wait for user to complete search
            input("✅ Press ENTER after you've completed the search and results are loaded...")
            
            # Booking.com can navigate the original tab or open a results tab.
            print("🔍 Looking for loaded flight results in the scraper browser...")
            results_page = wait_for_results_page(context)
            if results_page is None:
                print("❌ No results page detected. Keep the flight cards open in the browser launched by this script.")
                return
            print(f"🌐 Reading results from {results_page.title()}")
            flights = scrape_flight_results(results_page, params)
            
            publish_flights(flights, params)

        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            input("Press ENTER to close browser...")
            browser.close()

if __name__ == "__main__":
    main()
