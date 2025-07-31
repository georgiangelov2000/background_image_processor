# utils.py
from dotenv import load_dotenv
import pika
import os

# Load .env file
load_dotenv()

# Now read environment variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "resize_queue")

MEDIA_DIR = os.getenv("MEDIA_DIR", "./media")
MAX_QUEUE_LENGTH = int(os.getenv("MAX_QUEUE_LENGTH", 100))
MAX_CPU_PERCENT = int(os.getenv("MAX_CPU_PERCENT", 85))
MAX_MEMORY_PERCENT = int(os.getenv("MAX_MEMORY_PERCENT", 85))


def get_channel():
    """Establish and return a RabbitMQ channel."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT
    ))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    return channel


def get_queue_length():
    """Return the number of messages in the queue."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT
    ))
    channel = connection.channel()
    queue = channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True, passive=True)
    message_count = queue.method.message_count
    connection.close()
    return message_count
