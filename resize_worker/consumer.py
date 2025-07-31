#docker compose run resize_worker python consumer.py

import pika
import json
import os
from PIL import Image

MEDIA_DIR = "/media"
RESIZED_DIR = os.path.join(MEDIA_DIR, "resized")
os.makedirs(RESIZED_DIR, exist_ok=True)

def resize_image(image_name, width=800, height=600):
    input_path = os.path.join(MEDIA_DIR, image_name)
    output_path = os.path.join(RESIZED_DIR, image_name)

    try:
        with Image.open(input_path) as img:
            resized = img.resize((width, height))
            resized.save(output_path)
            print(f"[✓] Resized image saved to {output_path}")
    except Exception as e:
        print(f"[!] Failed to resize image {image_name}: {e}")

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"[>] Received job: {message}")

        if message.get("job_type") == "resize":
            resize_image(message["image_name"])

            # Prepare next job for watermarking
            next_job = {
                "image_name": message["image_name"],
                "job_type": "watermark"
            }

            # Ensure the target queue exists before publishing
            ch.queue_declare(queue="watermark_queue")

            # Publish to watermark_queue
            ch.basic_publish(
                exchange='',
                routing_key='watermark_queue',
                body=json.dumps(next_job),
            )
            print(f"[→] Sent job to watermark_queue: {next_job}")
        else:
            print(f"[!] Unsupported job type: {message.get('job_type')}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[!] Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="resize_queue")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="resize_queue", on_message_callback=callback)

    print("[*] Waiting for resize jobs. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == "__main__":
    main()
