"""
Kafka Producer for Flight Data
Sends scraped flight data to Kafka topic on VM
"""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
from datetime import datetime
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# VM Kafka Configuration
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
# Broker is configurable: set KAFKA_BROKER (env var or .env) e.g. "10.7.1.120:9092" for the Cloudera VM
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "flight-data")
VM_IP = KAFKA_BROKER.split(":")[0]

# Airline code mapping for flight number generation
AIRLINE_CODES = {
    "Air India": "AI",
    "IndiGo": "6E",
    "SpiceJet": "SG",
    "Vistara": "UK",
    "GoAir": "G8",
    "AirAsia": "I5",
    "Akasa Air": "QP",
    "Alliance Air": "9I"
}

class FlightKafkaProducer:
    """Kafka producer for sending flight data to VM"""
    
    def __init__(self):
        """Initialize Kafka producer"""
        self.producer = None
        self.connected = False
        self.message_count = 0
        
        try:
            logger.info(f"Connecting to Kafka broker at {KAFKA_BROKER}...")
            
            self.producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_block_ms=5000,
                compression_type='gzip'
            )
            
            self.connected = True
            logger.info("✅ Kafka producer initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka producer: {e}")
            self.connected = False
    
    def generate_flight_number(self, airline):
        """Generate flight number from airline name"""
        airline_clean = airline.strip()
        
        # Get airline code or use first 2 letters
        code = AIRLINE_CODES.get(airline_clean, airline_clean[:2].upper())
        
        # Generate 3-digit number
        number = random.randint(100, 999)
        
        return f"{code}{number}"
    
    def transform_flight_data(self, flight, source_city, dest_city):
        """Transform Flight dataclass to Kafka message format"""
        
        # Generate flight number if airline exists
        flight_number = self.generate_flight_number(flight.airline) if flight.airline else "UNKNOWN000"
        
        # Extract price numeric value
        price_str = "0"
        if flight.price:
            # Extract numbers from price string (e.g., "INR7,241.92" -> "7241")
            import re
            price_match = re.search(r'[\d,]+', flight.price)
            if price_match:
                price_str = price_match.group().replace(',', '').split('.')[0]
        
        # Create message matching VM's expected schema
        message = {
            "flight_number": flight_number,
            "source": source_city,
            "destination": dest_city,
            "price": price_str,
            "airline": flight.airline or "Unknown",
            "departure_time": flight.departure_time or "N/A",
            "arrival_time": flight.arrival_time or "N/A",
            "duration": flight.duration or "N/A",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stops": flight.stops or "N/A",
            "scraped_at": flight.scraped_at or datetime.now().isoformat(),
            "flight_number_generated": True  # Flag indicating this was generated
        }
        
        return message
    
    def send_flight(self, flight, source_city, dest_city):
        """Send a single flight to Kafka"""
        
        if not self.connected:
            logger.warning("⚠ Kafka producer not connected, skipping message")
            return False
        
        try:
            # Transform to Kafka format
            message = self.transform_flight_data(flight, source_city, dest_city)
            
            # Send to Kafka
            future = self.producer.send(KAFKA_TOPIC, message)
            
            # Wait for confirmation (with timeout)
            result = future.get(timeout=5)
            
            self.message_count += 1
            
            logger.info(
                f"✅ Sent flight {message['flight_number']}: "
                f"{source_city}→{dest_city} ₹{message['price']} "
                f"(offset: {result.offset})"
            )
            
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Kafka error sending flight: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending flight: {e}")
            return False
    
    def send_batch(self, flights, source_city, dest_city):
        """Send multiple flights to Kafka"""
        
        if not self.connected:
            logger.warning("⚠ Kafka producer not connected, cannot send batch")
            return 0
        
        success_count = 0
        
        for i, flight in enumerate(flights, 1):
            if self.send_flight(flight, source_city, dest_city):
                success_count += 1
            
            # Small delay between messages to avoid overwhelming Kafka
            if i % 5 == 0:
                self.producer.flush()
        
        # Final flush
        self.producer.flush()
        
        logger.info(f"📊 Batch complete: {success_count}/{len(flights)} flights sent successfully")
        
        return success_count
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            logger.info("Closing Kafka producer...")
            self.producer.flush()
            self.producer.close()
            logger.info(f"✅ Kafka producer closed. Total messages sent: {self.message_count}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Standalone function for easy import
def send_flights_to_kafka(flights, source_city, dest_city):
    """
    Convenience function to send flights to Kafka
    
    Args:
        flights: List of Flight dataclass objects
        source_city: Source city name
        dest_city: Destination city name
    
    Returns:
        Number of flights successfully sent
    """
    with FlightKafkaProducer() as producer:
        return producer.send_batch(flights, source_city, dest_city)

if __name__ == "__main__":
    # Test with sample data
    from dataclasses import dataclass
    
    @dataclass
    class TestFlight:
        airline: str = "Air India"
        departure_time: str = "10:30 AM"
        arrival_time: str = "12:45 PM"
        duration: str = "2h 15m"
        price: str = "INR5,000"
        stops: str = "Non-stop"
        departure_city: str = ""
        arrival_city: str = ""
        scraped_at: str = ""
    
    test_flight = TestFlight()
    
    with FlightKafkaProducer() as producer:
        producer.send_flight(test_flight, "Delhi", "Mumbai")
    
    print("\n✅ Test complete!")
