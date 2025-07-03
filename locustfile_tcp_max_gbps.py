# locustfile_tcp_max_gbps.py
from gevent import monkey
monkey.patch_all()

import socket, time, random, string
from locust import User, task, constant, events

TARGET_IP   = "54.167.227.87"
TARGET_PORT = 12345

# Generate a 1 MB random payload once
ONE_MB = 1024 * 1024
BIG_PAYLOAD = b"A" * ONE_MB

class GbpsUser(User):
    wait_time = constant(0)

    @task(5)
    def tcp_big_burst(self):
        """Open TCP, send 5 × 1 MB, close."""
        start = time.time()
        error = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((TARGET_IP, TARGET_PORT))
            for _ in range(5):
                sock.sendall(BIG_PAYLOAD)
            sock.close()
        except Exception as e:
            error = e
        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-BURST",
            name="5×1MB",
            response_time=elapsed,
            response_length=ONE_MB*5,
            exception=error,
        )

    @task(3)
    def udp_big_flood(self):
        """Send 2 × 1 MB UDP packets."""
        start = time.time()
        error = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            for _ in range(2):
                sock.sendto(BIG_PAYLOAD, (TARGET_IP, TARGET_PORT))
            sock.close()
        except Exception as e:
            error = e
        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="UDP-FLOOD",
            name="2×1MB",
            response_time=elapsed,
            response_length=ONE_MB*2,
            exception=error,
        )

    @task(2)
    def tcp_connect_only(self):
        """Lean SYN+close churn."""
        start = time.time()
        error = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((TARGET_IP, TARGET_PORT))
            sock.close()
        except Exception as e:
            error = e
        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-CONNECT",
            name="SYN-FLOOD",
            response_time=elapsed,
            response_length=0,
            exception=error,
        )
