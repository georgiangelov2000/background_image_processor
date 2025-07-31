# classes/job.py

import os
import hashlib
import shutil
import json
from pydantic import BaseModel
from fastapi import UploadFile
from utils import get_channel, MEDIA_DIR


class JobData(BaseModel):
    image_name: str
    job_type: str


class Job:
    def __init__(self, image: UploadFile, job_type: str):
        self.image = image
        self.job_type = job_type
        self.image_name = self._generate_image_name()

    def _generate_image_name(self) -> str:
        ext = os.path.splitext(self.image.filename)[1]
        return hashlib.sha256((self.image.filename + str(os.urandom(4))).encode()).hexdigest() + ext

    def save_image(self):
        os.makedirs(MEDIA_DIR, exist_ok=True)
        with open(os.path.join(MEDIA_DIR, self.image_name), "wb") as f:
            shutil.copyfileobj(self.image.file, f)

    def publish(self):
        message = JobData(image_name=self.image_name, job_type=self.job_type).dict()
        channel = get_channel()
        channel.basic_publish(
            exchange='',
            routing_key='resize_queue',
            body=json.dumps(message)
        )
        return message
