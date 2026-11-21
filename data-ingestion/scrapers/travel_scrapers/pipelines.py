import json
import os
from datetime import datetime
from itemadapter import ItemAdapter
from kafka import KafkaProducer
import logging

class FlightPipeline:
    """Production flight data pipeline"""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Basic validation and processing
        if not adapter.get('scraped_at'):
            adapter['scraped_at'] = datetime.now().isoformat()
        
        # Ensure required fields
        required_fields = ['airline', 'flight_number', 'origin', 'destination', 'price']
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Format price as integer
        if adapter.get('price'):
            try:
                adapter['price'] = int(float(str(adapter['price']).replace(',', '').replace('₹', '')))
            except:
                pass
                
        return item

class DataValidationPipeline:
    """Validate scraped data"""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Basic validation
        if not adapter.get('scraped_at'):
            adapter['scraped_at'] = datetime.now().isoformat()
            
        return item
class FlightItemFilter:
    def __call__(self, item):
        return item.get('data_type') == 'flights'

class NewsItemFilter:
    def __call__(self, item):
        return item.get('data_type') == 'news'

class HotelItemFilter:
    def __call__(self, item):
        return item.get('data_type') == 'hotels'

class WeatherItemFilter:
    def __call__(self, item):
        return item.get('data_type') == 'weather'


class KafkaPipeline:
    """
    Pipeline to send scraped data to Kafka
    """
    
    def __init__(self):
        self.producer = None
        self.items_sent = 0
        
    def open_spider(self, spider):
        """Initialize Kafka producer when spider starts"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=['192.168.150.130:9092'],  # Your VM IP
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks=1,  # Wait for acknowledgment
                retries=1,   # Minimal retries
                max_block_ms=5000,  # Only wait 5 seconds for metadata
                request_timeout_ms=5000,  # 5 second timeout
                linger_ms=1000,  # Batch messages for better performance
                batch_size=16384  # Reasonable batch size
            )
            spider.logger.info("✅ Connected to Kafka on VM (192.168.150.130:9092)")
        except Exception as e:
            spider.logger.error(f"❌ Failed to connect to Kafka: {e}")
            raise
    
    def close_spider(self, spider):
        """Close Kafka producer when spider finishes"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            spider.logger.info(f"✅ Kafka connection closed. Total items sent: {self.items_sent}")
    
    def process_item(self, item, spider):
        """Send each scraped item to Kafka topic"""
        try:
            # Convert Scrapy item to dictionary
            item_dict = dict(item)
            
            # Determine topic based on entity type
            entity_type = item_dict.get('entity_type', 'hotel')
            if entity_type == 'hotel':
                topic = 'hotel-data'
            elif entity_type == 'review':
                topic = 'hotel-reviews'
            else:
                topic = 'hotel-data'
            
            # Send to appropriate Kafka topic
            future = self.producer.send(topic, item_dict)
            result = future.get(timeout=10)  # Wait for confirmation
            
            self.items_sent += 1
            spider.logger.info(f"✅ Sent to Kafka ({topic}): {item_dict.get('hotel_name', item_dict.get('review_id', 'Item'))} - Offset: {result.offset}")
            
        except Exception as e:
            spider.logger.error(f"❌ Failed to send to Kafka: {e}")
            # Don't raise exception - continue scraping even if Kafka fails
        
        return item