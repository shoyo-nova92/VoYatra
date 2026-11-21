"""
QUICK TEST FOR BOOKING.COM SCRAPER
Test the Playwright-based scraper functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from booking_hotel_scraper import BookingHotelScraper
from datetime import datetime, timedelta

def test_scraper():
    """Quick test of the booking scraper"""
    
    print("🧪 TESTING BOOKING.COM SCRAPER")
    print("="*40)
    
    try:
        # Create directories
        os.makedirs('data/raw/hotels', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Initialize scraper (with visible browser for testing)
        scraper = BookingHotelScraper(headless=False)
        print("✅ Scraper initialized")
        
        # Test with future dates
        tomorrow = datetime.now() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        checkin = tomorrow.strftime('%Y-%m-%d')
        checkout = day_after.strftime('%Y-%m-%d')
        
        print(f"🗓️ Using dates: {checkin} to {checkout}")
        
        # Test basic scraping (just 1 page for testing)
        print("\n🔍 Testing basic hotel scraping for Mumbai...")
        hotels = scraper.scrape_hotels(
            destination="Mumbai",
            checkin_date=checkin,
            checkout_date=checkout,
            max_pages=1  # Just one page for testing
        )
        
        if hotels:
            print(f"✅ SUCCESS! Found {len(hotels)} hotels")
            
            # Show first few hotels
            for i, hotel in enumerate(hotels[:3], 1):
                print(f"\n🏨 Hotel {i}:")
                print(f"   Name: {hotel.name}")
                print(f"   Price: {hotel.price_per_night}")
                print(f"   Rating: {hotel.rating_score} - {hotel.review_description}")
                print(f"   Location: {hotel.location}")
                if hotel.amenities:
                    print(f"   Amenities: {hotel.amenities}")
            
            # Test CSV saving
            csv_file = scraper.save_to_csv(hotels, 'data/raw/hotels/test_mumbai_hotels.csv')
            print(f"\n✅ CSV export works - saved to {csv_file}")
            
            # Test Excel saving
            excel_file = scraper.save_to_excel(hotels, 'data/raw/hotels/test_mumbai_hotels.xlsx')
            print(f"✅ Excel export works - saved to {excel_file}")
            
            # Show summary stats
            stats = scraper.get_summary_stats(hotels)
            print(f"\n📊 SUMMARY:")
            print(f"   Total Hotels: {stats['total_hotels']}")
            print(f"   Average Rating: {stats['avg_rating']:.1f}/10")
            print(f"   Free Cancellation: {stats['hotels_with_free_cancellation']} hotels")
            
            return True
        else:
            print("❌ No hotels found - check if dates are in future")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Install missing dependencies:")
        print("   pip install playwright pandas openpyxl")
        print("   playwright install chromium")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    print("🚀 VOYATRA BOOKING SCRAPER - QUICK TEST")
    print("="*50)
    
    success = test_scraper()
    
    if success:
        print("\n🎉 TEST PASSED!")
        print("✅ The scraper is working correctly")
        print("✅ Ready for production use")
        print("\nNext steps:")
        print("1. Run: python booking_hotel_scraper.py (for full scraping)")
        print("2. Modify destination and dates as needed")
        print("3. Set headless=True for background scraping")
        
    else:
        print("\n❌ TEST FAILED")
        print("Check the error messages above and:")
        print("1. Install dependencies: pip install playwright pandas openpyxl")
        print("2. Install browser: playwright install chromium")
        print("3. Check internet connection")
        print("4. Ensure dates are in the future")