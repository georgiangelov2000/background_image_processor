# docker compose run finish_worker python consumer.py
import pika
import json
import os
import shutil
from datetime import datetime

WATERMARKED_DIR = "/media/watermarked"
FINISHED_DIR = "/media/finished"
LOG_FILE = "/media/finished_jobs.jsonl"

os.makedirs(FINISHED_DIR, exist_ok=True)

def log_job(data: dict):
    data["logged_at"] = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")
    print(f"[✓] Logged finished job: {data['image_name']}")

def move_final_image(image_name: str):
    source = os.path.join(WATERMARKED_DIR, image_name)
    dest = os.path.join(FINISHED_DIR, image_name)

    if not os.path.exists(source):
        raise FileNotFoundError(f"Watermarked image not found: {source}")

    shutil.copy2(source, dest)
    print(f"Copied image to {dest}")
    return dest

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"[>] Received finished job: {message}")

        image_name = message["image_name"]
        move_final_image(image_name)
        log_job(message)

        # Publish to notify_queue
        notify_msg = {
            "image_name": image_name
        }
        
        ch.queue_declare(queue="notify_queue")
        ch.basic_publish(
            exchange='',
            routing_key='notify_queue',
            body=json.dumps(notify_msg),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"[→] Sent notification to notify_queue for {image_name}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[!] Failed to finish job: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="finish_queue")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="finish_queue", on_message_callback=callback)

    print("[*] Waiting for finish jobs...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
