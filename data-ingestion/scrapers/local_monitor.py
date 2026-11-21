"""
Local Kafka Monitor for Flight Data
Real-time monitoring of flight-data topic from VM Kafka broker
Displays incoming flights in terminal - does NOT save to files
"""

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
from datetime import datetime
import sys
import signal

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

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\n⏹ Stopping monitor...")
    running = False

def format_flight_display(message):
    """Format flight data for terminal display"""
    
    # Extract data
    flight_num = message.get('flight_number', 'N/A')
    airline = message.get('airline', 'N/A')
    source = message.get('source', 'N/A')
    dest = message.get('destination', 'N/A')
    price = message.get('price', 'N/A')
    dep_time = message.get('departure_time', 'N/A')
    arr_time = message.get('arrival_time', 'N/A')
    duration = message.get('duration', 'N/A')
    stops = message.get('stops', 'N/A')
    date = message.get('date', 'N/A')
    
    # Check if flight number was generated
    generated = message.get('flight_number_generated', False)
    flight_display = f"{flight_num}*" if generated else flight_num
    
    # Format output
    output = f"""
┌{'─'*58}┐
│ {flight_display:<20} {airline:<35} │
├{'─'*58}┤
│ Route:    {source} → {dest}                           
│ Time:     {dep_time} → {arr_time}                     
│ Duration: {duration:<20} Stops: {stops:<20}           
│ Price:    ₹{price}                                     
│ Date:     {date}                                       
└{'─'*58}┘
"""
    
    return output

def monitor_kafka_topic():
    """Monitor Kafka topic and display incoming flights"""
    
    print("="*60)
    print("🔍 KAFKA FLIGHT DATA MONITOR")
    print("="*60)
    print(f"📡 Broker:  {KAFKA_BROKER}")
    print(f"📋 Topic:   {KAFKA_TOPIC}")
    print(f"👁  Mode:    Real-time monitoring (read-only)")
    print("="*60)
    print()
    print("⏳ Connecting to Kafka...")
    
    try:
        # Create Kafka consumer
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='latest',  # Only new messages
            enable_auto_commit=True,
            group_id='flight-monitor-local',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000  # Check for new messages every second
        )
        
        print("✅ Connected successfully!")
        print()
        print("🎧 Listening for new flights...")
        print("💡 Tip: Run the scraper in another terminal to see real-time data")
        print("⏹  Press Ctrl+C to stop monitoring")
        print()
        print("="*60)
        
        message_count = 0
        
        # Monitor loop
        while running:
            try:
                # Poll for messages
                messages = consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        message_count += 1
                        
                        # Display message
                        timestamp = datetime.fromtimestamp(record.timestamp / 1000.0)
                        
                        print(f"\n📨 Message #{message_count} at {timestamp.strftime('%H:%M:%S')}")
                        print(format_flight_display(record.value))
                        
                        # Check if it's a test message
                        if record.value.get('test', False):
                            print("   ℹ️  This is a test message")
                        
                        # Show offset info
                        print(f"   📍 Offset: {record.offset} | Partition: {record.partition}")
                        print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                if running:
                    print(f"⚠  Error reading message: {e}")
        
        # Close consumer
        consumer.close()
        
        print()
        print("="*60)
        print(f"📊 MONITORING SESSION COMPLETE")
        print(f"   Total messages received: {message_count}")
        print("="*60)
        
    except KafkaError as e:
        print()
        print("❌ KAFKA CONNECTION FAILED!")
        print("="*60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print(f"1. Check if VM is accessible: ping {VM_IP}")
        print("2. Verify Kafka is running on VM")
        print(f"3. Check topic exists: kafka-topics --list --bootstrap-server {KAFKA_BROKER}")
        print()
        sys.exit(1)
    
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def main():
    """Main function"""
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring
    monitor_kafka_topic()

if __name__ == "__main__":
    print()
    print("🚀 Starting Kafka Flight Monitor...")
    print()
    main()
    print()
    print("👋 Monitor stopped. Goodbye!")
    print()
