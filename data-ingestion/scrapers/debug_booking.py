"""
DEBUG BOOKING.COM HTML STRUCTURE
Check what selectors we need for hotel extraction
"""

import requests
from bs4 import BeautifulSoup
import time
import random

def debug_booking_structure():
    """Debug the HTML structure of Booking.com"""
    
    print("🔍 DEBUGGING BOOKING.COM HTML STRUCTURE")
    print("="*50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive'
    })
    
    # Simple search URL
    url = "https://www.booking.com/searchresults.html?ss=Mumbai&checkin=2025-10-21&checkout=2025-10-22&group_adults=2&no_rooms=1"
    
    print(f"🌐 Fetching: {url}")
    
    try:
        time.sleep(2)  # Be polite
        response = session.get(url)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for common hotel container patterns
            print("\n🔍 SEARCHING FOR HOTEL CONTAINERS...")
            
            # Pattern 1: data-testid
            containers1 = soup.find_all('div', {'data-testid': 'property-card'})
            print(f"✅ Found {len(containers1)} with data-testid='property-card'")
            
            # Pattern 2: Class patterns
            containers2 = soup.find_all('div', class_=lambda x: x and 'property' in x.lower() if x else False)
            print(f"✅ Found {len(containers2)} with 'property' in class")
            
            # Pattern 3: sr_property_block (old pattern)
            containers3 = soup.find_all('div', class_=lambda x: x and 'sr_property_block' in x if x else False)
            print(f"✅ Found {len(containers3)} with 'sr_property_block' in class")
            
            # Pattern 4: Generic containers
            containers4 = soup.find_all('div', class_=lambda x: x and ('hotel' in x.lower() or 'card' in x.lower()) if x else False)
            print(f"✅ Found {len(containers4)} with 'hotel' or 'card' in class")
            
            # Let's examine the first few containers
            all_containers = containers1 + containers2 + containers3 + containers4
            
            if all_containers:
                print(f"\n📋 EXAMINING FIRST CONTAINER:")
                first_container = all_containers[0]
                
                # Print container classes
                classes = first_container.get('class', [])
                print(f"Classes: {classes}")
                
                # Print data attributes
                data_attrs = {k: v for k, v in first_container.attrs.items() if k.startswith('data-')}
                print(f"Data attributes: {data_attrs}")
                
                # Look for hotel name
                print(f"\n🏨 SEARCHING FOR HOTEL NAME...")
                name_selectors = [
                    {'data-testid': 'title'},
                    'h3',
                    'h2', 
                    {'class': lambda x: x and 'name' in x.lower() if x else False},
                    {'class': lambda x: x and 'title' in x.lower() if x else False}
                ]
                
                for selector in name_selectors:
                    if isinstance(selector, str):
                        name_elem = first_container.find(selector)
                    else:
                        name_elem = first_container.find('div', selector) or first_container.find('span', selector) or first_container.find('a', selector)
                    
                    if name_elem:
                        print(f"✅ Found name with selector {selector}: {name_elem.get_text(strip=True)[:50]}...")
                        break
                
                # Look for price
                print(f"\n💰 SEARCHING FOR PRICE...")
                price_selectors = [
                    {'data-testid': 'price-and-discounted-price'},
                    {'class': lambda x: x and 'price' in x.lower() if x else False},
                    {'class': lambda x: x and 'bui-price-display' in x if x else False}
                ]
                
                for selector in price_selectors:
                    price_elem = first_container.find('div', selector) or first_container.find('span', selector)
                    if price_elem:
                        print(f"✅ Found price with selector {selector}: {price_elem.get_text(strip=True)[:50]}...")
                        break
                
                # Look for rating
                print(f"\n⭐ SEARCHING FOR RATING...")
                rating_selectors = [
                    {'data-testid': 'review-score'},
                    {'class': lambda x: x and 'score' in x.lower() if x else False},
                    {'class': lambda x: x and 'rating' in x.lower() if x else False}
                ]
                
                for selector in rating_selectors:
                    rating_elem = first_container.find('div', selector) or first_container.find('span', selector)
                    if rating_elem:
                        print(f"✅ Found rating with selector {selector}: {rating_elem.get_text(strip=True)[:50]}...")
                        break
                
                # Save a sample of the HTML for inspection
                with open('debug_booking_sample.html', 'w', encoding='utf-8') as f:
                    f.write(str(first_container.prettify()))
                print(f"\n💾 Saved first container HTML to: debug_booking_sample.html")
                
            else:
                print(f"\n❌ NO HOTEL CONTAINERS FOUND")
                print(f"Response length: {len(response.text)} characters")
                
                # Check if we're being blocked
                if 'captcha' in response.text.lower() or 'blocked' in response.text.lower():
                    print("🚫 Likely blocked by Booking.com")
                elif 'robot' in response.text.lower():
                    print("🤖 Detected as robot")
                else:
                    print("📄 Saving full HTML for manual inspection...")
                    with open('debug_booking_full.html', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print("💾 Saved to: debug_booking_full.html")
        
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_booking_structure()