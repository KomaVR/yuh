# locustfile_tcp_max_gbps_fixed.py
from gevent import monkey
monkey.patch_all()

import socket, time, random
from locust import User, task, constant, events

TARGET_IP   = "54.167.227.87"
TARGET_PORT = 12345

# We’ll build a moderate 16 KB payload and blast it repeatedly,
# rather than 1 MB all at once (UDP MTU-safe).
CHUNK_SIZE   = 16 * 1024  # 16 KB
BIG_PAYLOAD  = b"A" * CHUNK_SIZE

class GbpsUser(User):
    wait_time = constant(0)

    def on_start(self):
        # Create & reuse sockets instead of opening a new one each time
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Reuse local ports to avoid ephemeral exhaustion
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def on_stop(self):
        self.tcp_sock.close()
        self.udp_sock.close()

    @task(5)
    def tcp_big_burst(self):
        """Open once, send 64 × 16 KB = 1 MB, close."""
        start = time.time()
        error = None
        try:
            self.tcp_sock.settimeout(1)
            self.tcp_sock.connect((TARGET_IP, TARGET_PORT))
            for _ in range(64):         # 64×16 KB = 1 MB
                self.tcp_sock.sendall(BIG_PAYLOAD)
        except Exception as e:
            error = e
        finally:
            self.tcp_sock.close()
            # recreate for next time
            self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-BURST",
            name="1MB TCP",
            response_time=elapsed,
            response_length=CHUNK_SIZE * 64,
            exception=error,
        )

    @task(3)
    def udp_big_flood(self):
        """Send 64 × 16 KB = 1 MB via UDP without exceeding MTU."""
        start = time.time()
        error = None
        try:
            for _ in range(64):
                self.udp_sock.sendto(BIG_PAYLOAD, (TARGET_IP, TARGET_PORT))
        except Exception as e:
            error = e

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="UDP-FLOOD",
            name="1MB UDP",
            response_time=elapsed,
            response_length=CHUNK_SIZE * 64,
            exception=error,
        )

    @task(2)
    def tcp_connect_only(self):
        """Lean SYN+close churn."""
        start = time.time()
        error = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect((TARGET_IP, TARGET_PORT))
        except Exception as e:
            error = e
        finally:
            sock.close()

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-CONNECT",
            name="SYN-FLOOD",
            response_time=elapsed,
            response_length=0,
            exception=error,
        )
