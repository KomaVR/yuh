# locustfile_proxies.py
from gevent import monkey
monkey.patch_all()

import uuid, random, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from locust import HttpUser, task, between, events

# --- CONFIG ---
PROXY_SOURCE_URL = (
    "https://api.proxyscrape.com/v2/?request=getproxies"
    "&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
)
MAX_TO_VALIDATE   = 100
VALID_TIMEOUT     = 5  # seconds
VALIDATION_URL    = "/favicon.ico"  # tiny static endpoint
# ---------------

@events.test_start.add_listener
def fetch_proxies(environment, **kwargs):
    """Fetch & validate proxies once before the test."""
    print("[ProxySetup] Downloading proxy list…")
    try:
        r = requests.get(PROXY_SOURCE_URL, timeout=10)
        r.raise_for_status()
        raw = [p.strip() for p in r.text.splitlines() if p.strip()]
    except Exception as e:
        print(f"[ProxySetup] Failed to download: {e}")
        environment.proxies = []
        return

    print(f"[ProxySetup] Got {len(raw)} proxies, validating first {MAX_TO_VALIDATE}…")
    valid = []

    def _check(proxy):
        url = environment.host + VALIDATION_URL
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        try:
            rr = requests.head(url, proxies=proxies, timeout=VALID_TIMEOUT)
            if rr.status_code < 400:
                return proxy
        except:
            return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(_check, p): p for p in raw[:MAX_TO_VALIDATE]}
        for fut in as_completed(futures):
            p = fut.result()
            if p:
                valid.append(p)
                print(f"[ProxySetup]  ✔ {p}")

    environment.proxies = valid
    print(f"[ProxySetup] {len(valid)} proxies are alive.")

class ProxyUser(HttpUser):
    host = "https://54.167.227.87"
    wait_time = between(0, 0)  # zero think time

    @task(7)
    def search(self):
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

        q = random.choice([
            "123456789012345678",
            "987654321098765432",
            "user_example",
            "ip:192.168.0.1",
        ])
        # cache bust:
        url = f"/?q={q}&nocache={uuid.uuid4().hex}"
        self.client.get(
            url,
            name="GET /?q",
            headers={"Cache-Control":"no-cache","Pragma":"no-cache"},
            proxies=proxy_dict,
        )

    @task(3)
    def heavy_api(self):
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

        payload = {"data": "x" * random.randint(1000, 10000)}
        self.client.post(
            "/api/process",
            name="POST /api/process",
            json=payload,
            proxies=proxy_dict,
        )
