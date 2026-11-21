"""
VOYATRA BOOKING.COM COMPREHENSIVE HOTEL SCRAPER
Enhanced version of the working Playwright scraper with advanced filtering and data extraction
Author: VOYATRA Team
Version: 2.0 (Production-Ready)
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import json
import logging
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import re

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/booking_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Hotel:
    """Hotel data structure"""
    name: str = ""
    location: str = ""
    price_per_night: str = ""
    price_numeric: float = 0.0
    original_price: str = ""
    discount_percentage: str = ""
    rating_score: str = ""
    rating_numeric: float = 0.0
    review_description: str = ""
    review_count: str = ""
    review_count_numeric: int = 0
    distance_from_center: str = ""
    amenities: str = ""
    property_type: str = ""
    booking_url: str = ""
    image_url: str = ""
    free_cancellation: bool = False

class BookingHotelScraper:
    """Enhanced Booking.com hotel scraper using Playwright"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.base_url = "https://www.booking.com"
        
        # Rate limiting
        self.min_delay = 2
        self.max_delay = 5
        
    def build_search_url(self, 
                        destination: str,
                        checkin_date: str = None,
                        checkout_date: str = None,
                        adults: int = 1,
                        children: int = 0,
                        rooms: int = 1,
                        currency: str = 'USD',
                        language: str = 'en-us') -> str:
        """Build search URL with parameters"""
        
        # Default dates (tomorrow for 1 night)
        if not checkin_date:
            checkin = datetime.now() + timedelta(days=1)
            checkin_date = checkin.strftime('%Y-%m-%d')
        
        if not checkout_date:
            checkout = datetime.strptime(checkin_date, '%Y-%m-%d') + timedelta(days=1)
            checkout_date = checkout.strftime('%Y-%m-%d')
        
        # Build URL
        url = f"{self.base_url}/searchresults.{language}.html"
        url += f"?checkin={checkin_date}"
        url += f"&checkout={checkout_date}"
        url += f"&selected_currency={currency}"
        url += f"&ss={destination}"
        url += f"&ssne={destination}"
        url += f"&ssne_untouched={destination}"
        url += f"&lang={language}"
        url += "&sb=1&src_elem=sb&src=searchresults&dest_type=city"
        url += f"&group_adults={adults}"
        url += f"&no_rooms={rooms}"
        url += f"&group_children={children}"
        url += "&sb_travel_purpose=leisure"
        
        logger.info(f"Built search URL: {url}")
        return url
    
    # (reviews removed - reverted to simple hotel-only scraper)
    
    def extract_hotel_data(self, hotel_element, page, destination: str) -> Optional[Hotel]:
        """Extract comprehensive hotel data from hotel element"""
        try:
            hotel = Hotel()
            hotel.destination = destination
            hotel.scraped_at = datetime.now().isoformat()
            
            # Hotel name
            try:
                name_element = hotel_element.locator('//div[@data-testid="title"]')
                hotel.name = name_element.inner_text() if name_element.count() > 0 else "Unknown Hotel"
            except:
                hotel.name = "Unknown Hotel"
            
            # Location/Address
            try:
                location_element = hotel_element.locator('//span[@data-testid="address"]')
                hotel.location = location_element.inner_text() if location_element.count() > 0 else ""
            except:
                hotel.location = ""
            
            # Price
            try:
                price_element = hotel_element.locator('//span[@data-testid="price-and-discounted-price"]')
                if price_element.count() > 0:
                    hotel.price_per_night = price_element.inner_text()
                    # Extract numeric price
                    price_match = re.search(r'[\d,]+', hotel.price_per_night.replace('$', '').replace('₹', ''))
                    if price_match:
                        hotel.price_numeric = float(price_match.group().replace(',', ''))
            except:
                hotel.price_per_night = "N/A"
            
            # Original price (if discounted)
            try:
                original_price_element = hotel_element.locator('//span[contains(@class, "sr_discount_price")]')
                if original_price_element.count() > 0:
                    hotel.original_price = original_price_element.inner_text()
            except:
                pass
            
            # Rating score
            try:
                score_element = hotel_element.locator('//div[@data-testid="review-score"]/div[1]')
                if score_element.count() > 0:
                    hotel.rating_score = score_element.inner_text()
                    # Extract numeric rating
                    rating_match = re.search(r'([0-9.]+)', hotel.rating_score)
                    if rating_match:
                        hotel.rating_numeric = float(rating_match.group(1))
            except:
                hotel.rating_score = "N/A"
            
            # Review description
            try:
                review_desc_element = hotel_element.locator('//div[@data-testid="review-score"]/div[2]/div[1]')
                if review_desc_element.count() > 0:
                    hotel.review_description = review_desc_element.inner_text()
            except:
                hotel.review_description = ""
            
            # Review count
            try:
                review_count_element = hotel_element.locator('//div[@data-testid="review-score"]/div[2]/div[2]')
                if review_count_element.count() > 0:
                    hotel.review_count = review_count_element.inner_text()
                    # Extract numeric count
                    count_match = re.search(r'([0-9,]+)', hotel.review_count)
                    if count_match:
                        hotel.review_count_numeric = int(count_match.group(1).replace(',', ''))
            except:
                hotel.review_count = "0 reviews"
            
            # Distance from center
            try:
                distance_element = hotel_element.locator('//span[contains(text(), "km from")]')
                if distance_element.count() > 0:
                    hotel.distance_from_center = distance_element.inner_text()
            except:
                pass
            
            # Amenities (look for common amenities in the text)
            try:
                hotel_text = hotel_element.inner_text().lower()
                amenities_found = []
                
                amenity_keywords = {
                    'WiFi': ['wifi', 'wi-fi', 'internet'],
                    'Parking': ['parking', 'park'],
                    'Pool': ['pool', 'swimming'],
                    'Gym': ['gym', 'fitness'],
                    'Spa': ['spa', 'wellness'],
                    'Restaurant': ['restaurant', 'dining'],
                    'Bar': ['bar', 'lounge'],
                    'Breakfast': ['breakfast', 'morning'],
                    'Air Conditioning': ['air conditioning', 'ac', 'climate'],
                    'Pet Friendly': ['pet', 'dog', 'cat']
                }
                
                for amenity, keywords in amenity_keywords.items():
                    if any(keyword in hotel_text for keyword in keywords):
                        amenities_found.append(amenity)
                
                hotel.amenities = ', '.join(amenities_found)
            except:
                hotel.amenities = ""
            
            # Free cancellation
            try:
                hotel_text = hotel_element.inner_text().lower()
                hotel.free_cancellation = 'free cancellation' in hotel_text
            except:
                hotel.free_cancellation = False
            
            # Breakfast included
            try:
                hotel_text = hotel_element.inner_text().lower()
                hotel.breakfast_included = any(phrase in hotel_text for phrase in ['breakfast included', 'breakfast free', 'free breakfast'])
            except:
                hotel.breakfast_included = False
            
            # Booking URL
            try:
                link_element = hotel_element.locator('//h3/a | //div[@data-testid="title"]/a')
                if link_element.count() > 0:
                    href = link_element.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            hotel.booking_url = self.base_url + href
                        else:
                            hotel.booking_url = href
            except:
                pass
            
            # Property type (infer from name and description)
            try:
                name_lower = hotel.name.lower()
                if any(word in name_lower for word in ['resort', 'spa']):
                    hotel.property_type = "Resort"
                elif any(word in name_lower for word in ['apartment', 'studio', 'suites']):
                    hotel.property_type = "Apartment"
                elif any(word in name_lower for word in ['villa', 'house']):
                    hotel.property_type = "Villa"
                elif any(word in name_lower for word in ['hostel', 'backpacker']):
                    hotel.property_type = "Hostel"
                else:
                    hotel.property_type = "Hotel"
            except:
                hotel.property_type = "Hotel"
            
            # Image URL
            try:
                img_element = hotel_element.locator('//img')
                if img_element.count() > 0:
                    src = img_element.get_attribute('src') or img_element.get_attribute('data-src')
                    if src and 'http' in src:
                        hotel.image_url = src
            except:
                pass
            
            # Reviews scraping removed to restore original behavior
                hotel.overall_review_summary = "Reviews not available"
            
            return hotel
            
        except Exception as e:
            logger.error(f"Error extracting hotel data: {str(e)}")
            return None
    
    def scrape_hotels(self, 
                     destination: str,
                     checkin_date: str = None,
                     checkout_date: str = None,
                     max_pages: int = 3,
                     **filters) -> List[Hotel]:
        """Scrape hotels using Playwright"""
        
        logger.info(f"Starting hotel scrape for: {destination}")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            # Set user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            hotels_list = []
            
            try:
                # Build and navigate to search URL
                search_url = self.build_search_url(destination, checkin_date, checkout_date, **filters)
                logger.info(f"Navigating to: {search_url}")
                
                page.goto(search_url, timeout=60000)
                
                # Wait for hotels to load
                page.wait_for_selector('div[data-testid="property-card"]', timeout=30000)
                
                current_page = 1
                
                while current_page <= max_pages:
                    logger.info(f"Scraping page {current_page}...")
                    
                    # Rate limiting
                    if current_page > 1:
                        delay = random.uniform(self.min_delay, self.max_delay)
                        time.sleep(delay)
                    
                    # Get all hotel elements on current page
                    hotels = page.locator('//div[@data-testid="property-card"]').all()
                    logger.info(f'Found {len(hotels)} hotels on page {current_page}')
                    
                    if not hotels:
                        logger.warning(f"No hotels found on page {current_page}")
                        break
                    
                    # Extract data from each hotel
                    page_hotels = []
                    for i, hotel_element in enumerate(hotels):
                        try:
                            hotel_data = self.extract_hotel_data(hotel_element, page, destination)
                            if hotel_data and hotel_data.name != "Unknown Hotel":
                                page_hotels.append(hotel_data)
                        except Exception as e:
                            logger.error(f"Error processing hotel {i+1}: {str(e)}")
                            continue
                    
                    hotels_list.extend(page_hotels)
                    logger.info(f"Extracted {len(page_hotels)} hotels from page {current_page}")
                    
                    # Try to go to next page
                    if current_page < max_pages:
                        try:
                            # Look for next page button
                            next_button = page.locator('//a[@aria-label="Next page"]')
                            if next_button.count() > 0 and next_button.is_enabled():
                                next_button.click()
                                page.wait_for_load_state('networkidle', timeout=30000)
                                current_page += 1
                            else:
                                logger.info("No more pages available")
                                break
                        except Exception as e:
                            logger.error(f"Error navigating to next page: {str(e)}")
                            break
                    else:
                        break
            
            except Exception as e:
                logger.error(f"Error during scraping: {str(e)}")
            
            finally:
                browser.close()
            
            logger.info(f"Total hotels scraped: {len(hotels_list)}")
            return hotels_list
    
    def save_to_csv(self, hotels: List[Hotel], filename: str = None):
        """Save hotels data to CSV"""
        if not hotels:
            logger.warning("No hotels to save")
            return
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data/raw/hotels/booking_hotels_{timestamp}.csv'
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame([asdict(hotel) for hotel in hotels])
        
        # Save to CSV
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Saved {len(hotels)} hotels to {filename}")
        
        return filename
    
    def save_to_excel(self, hotels: List[Hotel], filename: str = None):
        """Save hotels data to Excel"""
        if not hotels:
            logger.warning("No hotels to save")
            return
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data/raw/hotels/booking_hotels_{timestamp}.xlsx'
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame([asdict(hotel) for hotel in hotels])
        
        # Save to Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Saved {len(hotels)} hotels to {filename}")
        
        return filename
    
    def get_summary_stats(self, hotels: List[Hotel]) -> Dict:
        """Get summary statistics of scraped hotels"""
        if not hotels:
            return {}
        
        df = pd.DataFrame([asdict(hotel) for hotel in hotels])
        
        stats = {
            'total_hotels': len(hotels),
            'avg_price': df['price_numeric'].mean() if df['price_numeric'].sum() > 0 else 0,
            'min_price': df['price_numeric'].min() if df['price_numeric'].sum() > 0 else 0,
            'max_price': df['price_numeric'].max() if df['price_numeric'].sum() > 0 else 0,
            'avg_rating': df['rating_numeric'].mean() if df['rating_numeric'].sum() > 0 else 0,
            'hotels_with_free_cancellation': df['free_cancellation'].sum(),
            'hotels_with_breakfast': int(df['breakfast_included'].sum()) if 'breakfast_included' in df else 0,
            'property_types': df['property_type'].value_counts().to_dict(),
            'destinations': df['location'].value_counts().to_dict()
        }
        
        return stats

def main():
    """Example usage"""
    
    # Create directories
    os.makedirs('data/raw/hotels', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Initialize scraper
    scraper = BookingHotelScraper(headless=False)  # Set to True for headless mode
    
    print("🏨 VOYATRA BOOKING.COM HOTEL SCRAPER")
    print("="*50)
    
    # Example 1: Mumbai Hotels
    print("📍 Scraping hotels in Mumbai...")
    mumbai_hotels = scraper.scrape_hotels(
        destination="Mumbai",
        checkin_date=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        checkout_date=(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
        max_pages=2
    )
    
    if mumbai_hotels:
        # Save data
        csv_file = scraper.save_to_csv(mumbai_hotels, 'data/raw/hotels/mumbai_hotels.csv')
        excel_file = scraper.save_to_excel(mumbai_hotels, 'data/raw/hotels/mumbai_hotels.xlsx')
        
        # Show results
        print(f"\n✅ Found {len(mumbai_hotels)} hotels in Mumbai")
        print(f"💾 Saved to: {csv_file}")
        print(f"💾 Saved to: {excel_file}")
        
        # Show top 5 hotels
        print("\n🏆 Top 5 Hotels:")
        for i, hotel in enumerate(mumbai_hotels[:5], 1):
            print(f"{i:2d}. {hotel.name}")
            print(f"     💰 {hotel.price_per_night}")
            print(f"     ⭐ {hotel.rating_score} - {hotel.review_description}")
            print(f"     📍 {hotel.location}")
            if hotel.amenities:
                print(f"     🛎️ {hotel.amenities[:50]}{'...' if len(hotel.amenities) > 50 else ''}")
            print()
        
        # Show statistics
        stats = scraper.get_summary_stats(mumbai_hotels)
        print("📊 SUMMARY STATISTICS:")
        print(f"   Total Hotels: {stats['total_hotels']}")
        print(f"   Average Price: ${stats['avg_price']:.2f}")
        print(f"   Price Range: ${stats['min_price']:.0f} - ${stats['max_price']:.0f}")
        print(f"   Average Rating: {stats['avg_rating']:.1f}/10")
        print(f"   Free Cancellation: {stats['hotels_with_free_cancellation']} hotels")
        print(f"   Breakfast Included: {stats['hotels_with_breakfast']} hotels")
    
    else:
        print("❌ No hotels found in Mumbai")

if __name__ == "__main__":
    main()