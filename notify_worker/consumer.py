#docker compose run watermark_worker python consumer.py

import pika
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "gangelov2000@gmail.com"            # TODO: replace
SMTP_PASSWORD = "pwivatdmpjnbtlen"           # TODO: use App Password if 2FA

TO_EMAIL = "gangelov2000@gmail.com"

# --- Media directories to clean up ---
MEDIA_DIRS = [
    "/media",
    "/media/resized",
    "/media/watermarked",
    "/media/finished"
]

def send_email(image_name):
    subject = "✅ Image Processed Successfully"
    body = f"Hello,\n\nYour image `{image_name}` has been successfully resized and watermarked.\n\nRegards,\nSmart Ads System"

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, TO_EMAIL, msg.as_string())
        server.quit()
        print(f"[📧] Sent notification email for {image_name}")
    except Exception as e:
        print(f"[!] Failed to send email: {e}")

def delete_all_versions(image_name: str):
    print(f"\n[🧹] Starting cleanup for: {image_name}")
    deleted = False

    for dir_path in MEDIA_DIRS:
        file_path = os.path.join(dir_path, image_name)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[🗑️] Deleted file: {file_path}")
                deleted = True
            except Exception as e:
                print(f"[!] Failed to delete {file_path}: {e}")
        else:
            print(f"[⚠️] Not found: {file_path}")

    if not deleted:
        print(f"[ℹ️] No files were deleted for {image_name} — nothing found in:")
        for p in MEDIA_DIRS:
            print(f"   └── {os.path.join(p, image_name)}")

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"[>] Received notify job: {message}")

        image_name = message.get("image_name", "unknown.jpg")
        send_email(image_name)
        delete_all_versions(image_name)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[!] Notification error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="notify_queue")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="notify_queue", on_message_callback=callback)

    print("[*] Waiting for notify jobs...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
