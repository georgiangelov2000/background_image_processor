from fastapi import FastAPI, Form, UploadFile, File
import os
import shutil
import pika
import json
import hashlib
import psutil

app = FastAPI()
MEDIA_DIR = "/media"
MAX_QUEUE_LENGTH = 100
MAX_CPU_PERCENT = 90
MAX_MEMORY_PERCENT = 90

def get_channel():
    connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="resize_queue")
    return channel

def get_queue_length(queue_name="resize_queue", host="rabbitmq"):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        channel = connection.channel()
        queue = channel.queue_declare(queue=queue_name, passive=True)
        message_count = queue.method.message_count
        connection.close()
        return message_count
    except Exception as e:
        print(f"[!] Failed to get queue length: {e}")
        return -1

def is_rabbitmq_overloaded():
    return get_queue_length() > MAX_QUEUE_LENGTH

def is_system_overloaded():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    return cpu > MAX_CPU_PERCENT or mem > MAX_MEMORY_PERCENT

@app.post("/send-job/")
def send_job(
    image: UploadFile = File(...),
    job_type: str = Form(...)
):
    ext = os.path.splitext(image.filename)[1]
    image_name = hashlib.sha256((image.filename + str(os.urandom(4))).encode()).hexdigest() + ext
    os.makedirs(MEDIA_DIR, exist_ok=True)

    # Circuit breaker check
    queue_size = get_queue_length()
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent

    if queue_size > MAX_QUEUE_LENGTH or cpu > MAX_CPU_PERCENT or mem > MAX_MEMORY_PERCENT:
        return {
            "status": "rejected",
            "reason": "System overloaded",
            "job_id": image_name,
            "system": {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "queue_length": queue_size
            }
        }

    try:
        with open(os.path.join(MEDIA_DIR, image_name), "wb") as f:
            shutil.copyfileobj(image.file, f)

        message = {
            "image_name": image_name,
            "job_type": job_type
        }

        channel = get_channel()
        channel.basic_publish(
            exchange='',
            routing_key='resize_queue',
            body=json.dumps(message)
        )

        return {
            "status": "Job sent",
            "job": message,
            "job_id": image_name,
            "system": {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "queue_length": queue_size
            }
        }

    except Exception as e:
        return {"error": str(e)}
