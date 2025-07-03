# locustfile_tcp_max_gbps_v2.py
from gevent import monkey
monkey.patch_all()

import socket, time
from locust import User, task, constant, events

TARGET_IP   = "54.167.227.87"
TARGET_PORT = 12345

# 64 KB chunk
CHUNK_SIZE  = 64 * 1024
CHUNK       = b"A" * CHUNK_SIZE

class GbpsUser(User):
    wait_time = constant(0)

    def on_start(self):
        # Create a fresh socket per task to avoid reuse issues
        pass

    @task(10)  # heavier weight for smaller bursts
    def tcp_burst_64k(self):
        """
        Open TCP, send 16 × 64 KB = 1 MB total,
        but in smaller bites so buffers don't overflow.
        """
        start = time.time()
        error = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            for _ in range(16):   # 16×64 KB = 1 MB
                s.sendall(CHUNK)
        except Exception as e:
            error = e
        finally:
            try: s.close()
            except: pass

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-BURST",
            name="16×64KB",
            response_time=elapsed,
            response_length=CHUNK_SIZE * 16,
            exception=error,
        )

    @task(5)
    def udp_flood_64k(self):
        """
        Fire 32 × 64 KB = 2 MB UDP packets,
        but below MTU limits so they go through.
        """
        start = time.time()
        error = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(5)
            for _ in range(32):  # 32×64 KB = 2 MB
                s.sendto(CHUNK, (TARGET_IP, TARGET_PORT))
        except Exception as e:
            error = e
        finally:
            try: s.close()
            except: pass

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="UDP-FLOOD",
            name="32×64KB",
            response_time=elapsed,
            response_length=CHUNK_SIZE * 32,
            exception=error,
        )

    @task(2)
    def tcp_connect_only(self):
        """SYN flood + immediate close"""
        start = time.time()
        error = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
        except Exception as e:
            error = e
        finally:
            try: s.close()
            except: pass

        elapsed = int((time.time() - start)*1000)
        events.request.fire(
            request_type="TCP-CONNECT",
            name="SYN-FLOOD",
            response_time=elapsed,
            response_length=0,
            exception=error,
        )
