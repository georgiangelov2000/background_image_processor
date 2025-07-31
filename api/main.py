# main.py
from fastapi import FastAPI, Form, UploadFile, File
import psutil
from utils import get_queue_length, MAX_CPU_PERCENT, MAX_MEMORY_PERCENT, MAX_QUEUE_LENGTH
from classes.job import Job

app = FastAPI()


@app.post("/send-job/")
def send_job(
    image: UploadFile = File(...),
    job_type: str = Form(...)
):
    queue_size = get_queue_length()
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent

    # Circuit breaker for overloading 
    if queue_size > MAX_QUEUE_LENGTH or cpu > MAX_CPU_PERCENT or mem > MAX_MEMORY_PERCENT:
        return {
            "status": "rejected",
            "reason": "System overloaded",
            "job_id": None,
            "system": {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "queue_length": queue_size
            }
        }

    try:
        job = Job(image=image, job_type=job_type)
        job.save_image()
        message = job.publish()

        return {
            "status": "Job sent",
            "job": message,
            "job_id": job.image_name,
            "system": {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "queue_length": queue_size
            }
        }

    except Exception as e:
        return {"error": str(e)}
