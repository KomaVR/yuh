import os
import time
import subprocess
from locust import User, task, constant, events

# pulled from env by /storm
TARGET_IP     = os.getenv("LOCUST_TARGET_IP", "127.0.0.1")
TCP_PORT      = int(os.getenv("LOCUST_TCP_PORT", "12345"))
UDP_PORT      = int(os.getenv("LOCUST_UDP_PORT", "12345"))
UDP_BANDWIDTH = os.getenv("LOCUST_UDP_BW", "1G")

class HpingUser(User):
    wait_time = constant(0)

    @task(1)
    def syn_flood(self):
        """
        1s TCP SYN flood using hping3 --flood --rand-source
        """
        cmd = [
            "hping3",
            "--flood",          # send as fast as possible
            "--rand-source",    # randomize src IP
            "-S",               # SYN flag
            "-p", str(TCP_PORT),
            TARGET_IP,
        ]
        start = time.time()
        exception = None
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.wait(timeout=1)
        except Exception as e:
            exception = e
            try: p.terminate()
            except: pass
        else:
            p.terminate()
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="hping3",
            name="1s-hping3-syn",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )

class IperfUser(User):
    wait_time = constant(0)

    @task(1)
    def udp_flood(self):
        """
        1s UDP flood at configured bandwidth via iperf3
        """
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
            try: p.terminate()
            except: pass
        else:
            p.terminate()
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="iperf3",
            name="1s-iperf3-udp",
            response_time=elapsed,
            response_length=0,
            exception=exception,
        )
