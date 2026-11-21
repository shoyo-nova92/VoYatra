"""
Test Kafka Connection to VM
Sends a test message to verify connectivity to 10.7.1.120:9092
"""

from kafka import KafkaProducer
import json
from datetime import datetime
import sys

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

def test_kafka_connection():
    """Test connection to Kafka broker and send test message"""
    
    print("="*60)
    print("KAFKA CONNECTION TEST")
    print("="*60)
    print(f"📡 Broker: {KAFKA_BROKER}")
    print(f"📋 Topic: {KAFKA_TOPIC}")
    print()
    
    try:
        print("🔌 Connecting to Kafka broker...")
        
        # Create Kafka producer
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            max_block_ms=10000  # Timeout after 10 seconds
        )
        
        print("✅ Connected successfully!")
        print()
        
        # Test message
        test_message = {
            "flight_number": "TEST001",
            "source": "TestCity",
            "destination": "TestDestination",
            "price": "0",
            "airline": "TestAirline",
            "departure_time": "00:00 AM",
            "arrival_time": "00:00 AM",
            "duration": "0h 0m",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        print("📤 Sending test message...")
        print(f"Message: {json.dumps(test_message, indent=2)}")
        print()
        
        # Send message
        future = producer.send(KAFKA_TOPIC, test_message)
        
        # Wait for confirmation
        result = future.get(timeout=10)
        
        print("✅ TEST MESSAGE SENT SUCCESSFULLY!")
        print(f"   Topic: {result.topic}")
        print(f"   Partition: {result.partition}")
        print(f"   Offset: {result.offset}")
        print()
        print("="*60)
        print("🎉 Kafka connection is working!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. Check VM consumer to verify message was received")
        print(f"2. SSH to VM: ssh cloudera@{VM_IP}")
        print("3. Check data: ls -lh /home/cloudera/voyatra_data/")
        print()
        
        # Close producer
        producer.flush()
        producer.close()
        
        return True
        
    except Exception as e:
        print()
        print("❌ CONNECTION FAILED!")
        print("="*60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting steps:")
        print("1. Check if VM is running")
        print(f"2. Verify network connectivity: ping {VM_IP}")
        print("3. Check if Kafka is running on VM:")
        print(f"   ssh cloudera@{VM_IP}")
        print("   jps | grep Kafka")
        print("4. Check Kafka logs on VM:")
        print("   tail -f /var/log/kafka/server.log")
        print()
        
        return False

if __name__ == "__main__":
    success = test_kafka_connection()
    sys.exit(0 if success else 1)
