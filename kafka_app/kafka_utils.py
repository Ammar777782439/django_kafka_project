import json
import base64
import os
import threading
import time
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def delivery_report(err, msg):
    """
    Callback function for Kafka producer to report delivery status
    """
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

def get_kafka_producer():
    """
    Create and return a Kafka producer instance
    """
    try:
        return Producer(settings.KAFKA_CONFIG)
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        return None

def send_text_message(message):
    """
    Send a text message to Kafka
    """
    producer = get_kafka_producer()
    if not producer:
        return False, "Failed to create Kafka producer"

    try:
        # Create message payload
        payload = {
            'type': 'text',
            'content': message
        }

        # Convert payload to JSON string
        message_json = json.dumps(payload)

        # Send message to Kafka
        producer.produce(
            settings.KAFKA_PRODUCER_TOPIC,
            message_json.encode('utf-8'),
            callback=delivery_report
        )

        # Wait for any outstanding messages to be delivered
        producer.flush()

        return True, "Message sent successfully"
    except Exception as e:
        logger.error(f"Failed to send message to Kafka: {e}")
        return False, f"Failed to send message: {str(e)}"

def send_file(file_obj):
    """
    Send a file to Kafka
    """
    producer = get_kafka_producer()
    if not producer:
        return False, "Failed to create Kafka producer"

    try:
        # Read file content
        file_content = file_obj.read()

        # Encode file content as base64
        encoded_content = base64.b64encode(file_content).decode('utf-8')

        # Create message payload
        payload = {
            'type': 'file',
            'filename': file_obj.name,
            'content': encoded_content
        }

        # Convert payload to JSON string
        message_json = json.dumps(payload)

        # Send message to Kafka
        producer.produce(
            settings.KAFKA_PRODUCER_TOPIC,
            message_json.encode('utf-8'),
            callback=delivery_report
        )

        # Wait for any outstanding messages to be delivered
        producer.flush()

        return True, "File sent successfully"
    except Exception as e:
        logger.error(f"Failed to send file to Kafka: {e}")
        return False, f"Failed to send file: {str(e)}"


# Global variables for consumer management
consumer_thread = None
consumer_running = False
messages_buffer = []


def get_kafka_consumer():
    """
    Create and return a Kafka consumer instance
    """
    try:
        consumer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'django-kafka-consumer-group',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
        }
        return Consumer(consumer_config)
    except Exception as e:
        logger.error(f"Failed to create Kafka consumer: {e}")
        return None


def consume_messages():
    """
    Consume messages from Kafka topic and store them in the messages buffer
    This function runs in a separate thread
    """
    global consumer_running, messages_buffer

    consumer = get_kafka_consumer()
    if not consumer:
        logger.error("Failed to create Kafka consumer")
        consumer_running = False
        return

    try:
        consumer.subscribe([settings.KAFKA_CONSUMER_TOPIC])
        logger.info(f"Subscribed to topic: {settings.KAFKA_CONSUMER_TOPIC}")

        while consumer_running:
            msg = consumer.poll(1.0)  # Poll for 1 second

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event - not an error
                    logger.info(f"Reached end of partition {msg.partition()}")
                else:
                    logger.error(f"Consumer error: {msg.error()}")
            else:
                try:
                    # Get message value and convert it to string
                    message_value = msg.value().decode('utf-8')

                    # Parse JSON message
                    message_data = json.loads(message_value)

                    # Add metadata to the message (without underscore prefix for template compatibility)
                    message_data['kafka_metadata'] = {
                        'partition': msg.partition(),
                        'offset': msg.offset(),
                        'key': msg.key().decode('utf-8') if msg.key() else 'empty',
                        'timestamp': datetime.fromtimestamp(msg.timestamp()[1]/1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                        'headers': msg.headers() if msg.headers() else 'empty'
                    }

                    # Add message to buffer (limit buffer size to 100 messages)
                    messages_buffer.append(message_data)
                    if len(messages_buffer) > 100:
                        messages_buffer = messages_buffer[-100:]

                    logger.info(f"Received message: {message_data}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    except KafkaException as e:
        logger.error(f"Kafka exception: {e}")
    finally:
        consumer.close()
        logger.info("Kafka consumer closed")


def start_consumer():
    """
    Start the Kafka consumer in a separate thread
    """
    global consumer_thread, consumer_running

    if consumer_thread is not None and consumer_thread.is_alive():
        return False, "Consumer is already running"

    consumer_running = True
    consumer_thread = threading.Thread(target=consume_messages)
    consumer_thread.daemon = True  # Thread will exit when the main program exits
    consumer_thread.start()

    return True, "Consumer started successfully"


def stop_consumer():
    """
    Stop the Kafka consumer thread
    """
    global consumer_running, consumer_thread

    if consumer_thread is None or not consumer_thread.is_alive():
        return False, "Consumer is not running"

    consumer_running = False
    consumer_thread.join(timeout=5.0)  # Wait for the thread to terminate

    if consumer_thread.is_alive():
        return False, "Failed to stop consumer"
    else:
        consumer_thread = None
        return True, "Consumer stopped successfully"


def get_received_messages(event_type=None):
    """
    Get the messages received from Kafka

    Args:
        event_type (str, optional): Filter messages by event_type. Defaults to None.

    Returns:
        list: List of messages, filtered by event_type if specified
    """
    global messages_buffer

    if event_type is None:
        return messages_buffer

    # Filter messages by event_type
    filtered_messages = [msg for msg in messages_buffer if msg.get('event_type') == event_type]
    return filtered_messages
