#docker compose run watermark_worker python consumer.py

import pika
import json
import os
from PIL import Image, ImageDraw, ImageFont

RESIZED_DIR = "/media/resized"
WATERMARKED_DIR = "/media/watermarked"
os.makedirs(WATERMARKED_DIR, exist_ok=True)

def watermark_image(image_name, channel):
    input_path = os.path.join(RESIZED_DIR, image_name)
    output_path = os.path.join(WATERMARKED_DIR, image_name)

    try:
        with Image.open(input_path).convert("RGBA") as base:
            watermark = Image.new("RGBA", base.size, (0, 0, 0, 0))  # type: ignore

            draw = ImageDraw.Draw(watermark)

            font_size = int(base.size[0] * 0.05)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            text = "Smart Ads"
            position = (base.size[0] - font_size * len(text) // 2 - 20, base.size[1] - font_size - 20)
            draw.text(position, text, font=font, fill=(255, 255, 255, 128))

            combined = Image.alpha_composite(base, watermark)
            combined.convert("RGB").save(output_path)
            print(f"[✓] Watermarked image saved to {output_path}")

            # Prepare message for finish_queue
            finish_message = {
                "image_name": image_name,
                "job_type": "finish",
                "status": "done",
                "stage": "watermarked"
            }

            # Ensure the queue exists before publishing
            channel.queue_declare(queue="finish_queue")

            channel.basic_publish(
                exchange='',
                routing_key='finish_queue',
                body=json.dumps(finish_message),
            )
            print(f"[→] Sent job to finish_queue: {finish_message}")

    except Exception as e:
        print(f"[!] Failed to watermark {image_name}: {e}")

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"[>] Received job: {message}")

        if message.get("job_type") == "watermark":
            watermark_image(message["image_name"], ch)
        else:
            print(f"[!] Unsupported job type: {message.get('job_type')}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[!] Error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="watermark_queue")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="watermark_queue", on_message_callback=callback)

    print("[*] Waiting for watermark jobs...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
