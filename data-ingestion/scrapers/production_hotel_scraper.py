"""
VOYATRA BOOKING.COM PRODUCTION HOTEL SCRAPER
Multi-city, multi-scenario hotel scraping for comprehensive data collection
Author: VOYATRA Team
Version: 2.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from booking_hotel_scraper import BookingHotelScraper
from datetime import datetime, timedelta

def run_comprehensive_hotel_scraping():
    """Run comprehensive hotel scraping across multiple cities and scenarios"""
    
    # Initialize scraper (set headless=True for background scraping)
    scraper = BookingHotelScraper(headless=False)
    
    print("🏨 VOYATRA COMPREHENSIVE HOTEL SCRAPING")
    print("="*60)
    
    # Define future dates
    tomorrow = datetime.now() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)
    week_later = datetime.now() + timedelta(days=7)
    week_after = week_later + timedelta(days=1)
    
    checkin_short = tomorrow.strftime('%Y-%m-%d')
    checkout_short = day_after.strftime('%Y-%m-%d')
    checkin_long = week_later.strftime('%Y-%m-%d')
    checkout_long = week_after.strftime('%Y-%m-%d')
    
    # Define scraping scenarios
    scenarios = [
        {
            'name': '🏙️ MUMBAI - Business Hotels',
            'destination': 'Mumbai',
            'checkin': checkin_short,
            'checkout': checkout_short,
            'adults': 1,
            'rooms': 1,
            'max_pages': 3,
            'filename_prefix': 'mumbai_business'
        },
        {
            'name': '🏖️ GOA - Beach Resorts',
            'destination': 'Goa',
            'checkin': checkin_long,
            'checkout': checkout_long,
            'adults': 2,
            'rooms': 1,
            'max_pages': 2,
            'filename_prefix': 'goa_beach'
        },
        {
            'name': '🏢 BANGALORE - Tech Hub Hotels',
            'destination': 'Bangalore',
            'checkin': checkin_short,
            'checkout': checkout_short,
            'adults': 1,
            'rooms': 1,
            'max_pages': 2,
            'filename_prefix': 'bangalore_tech'
        },
        {
            'name': '🏛️ DELHI - Heritage & Luxury',
            'destination': 'New Delhi',
            'checkin': checkin_long,
            'checkout': checkout_long,
            'adults': 2,
            'rooms': 1,
            'max_pages': 2,
            'filename_prefix': 'delhi_luxury'
        },
        {
            'name': '🏔️ SHIMLA - Hill Station Hotels',
            'destination': 'Shimla',
            'checkin': checkin_long,
            'checkout': checkout_long,
            'adults': 2,
            'rooms': 1,
            'max_pages': 2,
            'filename_prefix': 'shimla_hills'
        }
    ]
    
    all_results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{scenario['name']}")
        print("="*50)
        print(f"📅 Dates: {scenario['checkin']} to {scenario['checkout']}")
        print(f"👥 {scenario['adults']} adult(s), {scenario['rooms']} room(s)")
        
        try:
            # Scrape hotels
            hotels = scraper.scrape_hotels(
                destination=scenario['destination'],
                checkin_date=scenario['checkin'],
                checkout_date=scenario['checkout'],
                adults=scenario['adults'],
                rooms=scenario['rooms'],
                max_pages=scenario['max_pages']
            )
            
            if hotels:
                # Add to combined results
                all_results.extend(hotels)
                
                print(f"✅ Found {len(hotels)} hotels in {scenario['destination']}")
                
                # Show top 3 hotels
                print("🏆 Top 3 Hotels:")
                for j, hotel in enumerate(hotels[:3], 1):
                    print(f"  {j}. {hotel.name}")
                    print(f"     💰 {hotel.price_per_night}")
                    print(f"     ⭐ {hotel.rating_score} - {hotel.review_description}")
                    print(f"     📍 {hotel.location}")
                
                # Quick stats
                stats = scraper.get_summary_stats(hotels)
                print(f"\n📊 Quick Stats:")
                print(f"   Average Rating: {stats['avg_rating']:.1f}/10")
                print(f"   Price Range: ${stats['min_price']:.0f} - ${stats['max_price']:.0f}")
                print(f"   Free Cancellation: {stats['hotels_with_free_cancellation']} hotels")
                
            else:
                print(f"❌ No hotels found in {scenario['destination']}")
                
        except Exception as e:
            print(f"❌ Error scraping {scenario['destination']}: {str(e)}")
        
        # Add delay between cities to be respectful
        if i < len(scenarios):
            print("\n⏳ Waiting before next city...")
            import time
            time.sleep(5)
    
    # Save combined results
    if all_results:
        print(f"\n🎉 FINAL SUMMARY")
        print("="*60)
        
        # Final statistics
        final_stats = scraper.get_summary_stats(all_results)
        
        print(f"📊 OVERALL STATISTICS:")
        print(f"   Total Hotels Scraped: {final_stats['total_hotels']}")
        print(f"   Cities Covered: {len(final_stats['destinations'])}")
        print(f"   Average Price: ${final_stats['avg_price']:.2f}")
        print(f"   Price Range: ${final_stats['min_price']:.0f} - ${final_stats['max_price']:.0f}")
        print(f"   Average Rating: {final_stats['avg_rating']:.1f}/10")
        print(f"   Free Cancellation: {final_stats['hotels_with_free_cancellation']} hotels")
        print(f"   Breakfast Included: {final_stats['hotels_with_breakfast']} hotels")
        
        print(f"\n🏙️ CITIES BREAKDOWN:")
        for city, count in final_stats['destinations'].items():
            print(f"   {city}: {count} hotels")
        
        print(f"\n🏨 PROPERTY TYPES:")
        for prop_type, count in final_stats['property_types'].items():
            print(f"   {prop_type}: {count} properties")
        
        print(f"\n� Data ready for Kafka integration!")
        print(f"� Total: {final_stats['total_hotels']} hotels across {len(final_stats['destinations'])} cities")
        
        return final_stats
    
    else:
        print("\n❌ No data collected from any city")
        return None

def run_custom_city_search():
    """Run a custom search for user-specified city"""
    
    scraper = BookingHotelScraper(headless=False)
    
    print("🔧 CUSTOM CITY HOTEL SEARCH")
    print("="*40)
    
    # Get user input
    city = input("Enter city name (e.g., Jaipur, Kochi, Pune): ").strip()
    if not city:
        city = "Pune"  # Default
    
    pages = input("Number of pages to scrape (1-5, default=2): ").strip()
    try:
        pages = int(pages) if pages else 2
        pages = max(1, min(pages, 5))  # Limit between 1-5
    except:
        pages = 2
    
    print(f"\n🏨 Searching hotels in {city} ({pages} pages)...")
    
    # Use future dates
    tomorrow = datetime.now() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=2)  # 2-day stay
    
    checkin = tomorrow.strftime('%Y-%m-%d')
    checkout = day_after.strftime('%Y-%m-%d')
    
    hotels = scraper.scrape_hotels(
        destination=city,
        checkin_date=checkin,
        checkout_date=checkout,
        adults=2,
        rooms=1,
        max_pages=pages
    )
    
    if hotels:
        # Save results
        print(f"\n✅ Found {len(hotels)} hotels in {city}")
        print(f"📅 Stay: {checkin} to {checkout}")
        print(f"� Data ready for Kafka integration!")
        
        # Show top hotels
        print(f"\n🏆 TOP HOTELS IN {city.upper()}:")
        print("-" * 60)
        
        for i, hotel in enumerate(hotels[:10], 1):
            print(f"{i:2d}. {hotel.name}")
            print(f"     💰 {hotel.price_per_night}")
            print(f"     ⭐ {hotel.rating_score} ({hotel.review_count})")
            print(f"     📍 {hotel.location}")
            if hotel.amenities:
                amenities_short = hotel.amenities[:50] + "..." if len(hotel.amenities) > 50 else hotel.amenities
                print(f"     🛎️ {amenities_short}")
            print()
        
        # Statistics
        stats = scraper.get_summary_stats(hotels)
        print(f"📊 {city.upper()} HOTEL STATISTICS:")
        print(f"   Total Hotels: {stats['total_hotels']}")
        print(f"   Average Price: ${stats['avg_price']:.2f}/night")
        print(f"   Price Range: ${stats['min_price']:.0f} - ${stats['max_price']:.0f}")
        print(f"   Average Rating: {stats['avg_rating']:.1f}/10")
        print(f"   Free Cancellation: {stats['hotels_with_free_cancellation']} hotels")
        
    else:
        print(f"❌ No hotels found in {city}")

if __name__ == "__main__":
    print("🏨 VOYATRA BOOKING.COM PRODUCTION SCRAPER")
    print("="*60)
    print("Choose scraping mode:")
    print("1. Comprehensive Multi-City Scraping (5 cities)")
    print("2. Custom Single City Search")
    print("3. Quick Mumbai Test")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        print("\n🚀 Starting comprehensive multi-city scraping...")
        results = run_comprehensive_hotel_scraping()
        if results:
            print(f"\n🎉 SCRAPING COMPLETED SUCCESSFULLY!")
            print(f"Total hotels collected: {results['total_hotels']}")
            
    elif choice == "2":
        run_custom_city_search()
        
    elif choice == "3" or choice == "":
        print("\n🚀 Quick Mumbai Test")
        scraper = BookingHotelScraper(headless=False)
        
        tomorrow = datetime.now() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        hotels = scraper.scrape_hotels(
            destination="Mumbai",
            checkin_date=tomorrow.strftime('%Y-%m-%d'),
            checkout_date=day_after.strftime('%Y-%m-%d'),
            max_pages=1
        )
        
        if hotels:
            print(f"✅ Found {len(hotels)} hotels in Mumbai")
            print("💡 Data ready for Kafka integration!")
            for i, hotel in enumerate(hotels[:5], 1):
                print(f"{i}. {hotel.name} - {hotel.price_per_night}")
    
    else:
        print("Invalid choice. Running quick test...")
        scraper = BookingHotelScraper(headless=True)
        hotels = scraper.scrape_hotels("Mumbai", max_pages=1)
        if hotels:
            print(f"✅ Found {len(hotels)} hotels")